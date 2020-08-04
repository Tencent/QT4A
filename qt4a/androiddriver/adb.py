# -*- coding:UTF-8 -*-
#
# Tencent is pleased to support the open source community by making QTA available.
# Copyright (C) 2016THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the BSD 3-Clause License (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
#
# https://opensource.org/licenses/BSD-3-Clause
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" basis, WITHOUT WARRANTIES OR CONDITIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.
#
'''封装ADB功能
'''

from __future__ import unicode_literals
from __future__ import print_function

import os
import re
import six
import subprocess
import sys
import threading
import time

from pkg_resources import iter_entry_points
from qt4a.androiddriver.adbclient import ADBClient
from qt4a.androiddriver.util import Singleton, Deprecated, logger, ThreadEx, TimeoutError, InstallPackageFailedError, PermissionError, is_int, utf8_encode, encode_wrap, enforce_utf8_decode, general_encode, time_clock

try:
    import _strptime  # time.strptime() is not thread-safed, so import _strptime first, otherwise it raises an AttributeError: _strptime_time
except:
    pass
cur_path = os.path.dirname(os.path.abspath(__file__))


def get_adb_path():
    if sys.platform == 'win32':
        sep = ';'
        file_name = 'adb.exe'
    else:
        sep = ':'
        file_name = 'adb'

    for root in os.environ.get('PATH').split(sep):
        adb_path = os.path.join(root, file_name)
        if os.path.exists(adb_path):  # 优先使用环境变量中指定的 adb
            return adb_path

    return os.path.join(cur_path, 'tools', 'adb', sys.platform, file_name)


adb_path = get_adb_path()


def is_adb_server_opend(host='localhost'):
    '''判断ADB Server是否开启
    '''
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, 5037))
        sock.close()
        return False
    except:
        return True


class EnumRootState(object):
    '''设备Root状态
    '''
    Unknown = 0  # 未知
    NonRoot = 1  # 非Root
    AdbdRoot = 2  # adbd以Root权限执行（执行adb root后）
    SuRoot = 3  # 使用su进入Root


class IADBBackend(object):
    '''ADBBackend接口定义
    '''

    @staticmethod
    def list_device():
        '''枚举设备列表
        '''
        pass

    @staticmethod
    def open_device(name):
        '''打开指定设备

        :param name: 设备名称
        :type  name: str
        :return: IADBBackend实例
        '''
        pass

    @property
    def device_host(self):
        '''设备主机
        '''
        pass

    @property
    def device_name(self):
        '''设备名
        '''
        pass

    def run_adb_cmd(self, cmd, *args, **kwargs):
        '''执行adb命令
        '''
        pass


class LocalADBBackend(IADBBackend):
    '''本地ADBBackend
    '''

    @staticmethod
    def start():
        if is_adb_server_opend():
            return False
        subprocess.call([adb_path, 'start-server'])
        return True

    @staticmethod
    def close():
        subprocess.call([adb_path, 'kill-server'])

    @staticmethod
    def list_device(device_host='127.0.0.1'):
        '''枚举设备列表
        '''
        if not is_adb_server_opend(device_host):
            return []
        result = ADBClient.get_client(device_host).call('devices',
                                                        retry_count=3)[0]
        result = result.split('\n')
        device_list = []
        for device in result:
            if len(device) <= 1 or not '\t' in device:
                continue
            device_name, status = device.split('\t')
            if status != 'device':
                continue
            device_list.append(device_name)
        return device_list

    @staticmethod
    def open_device(name):
        '''打开指定设备

        :param name: 设备名称
        :type  name: str
        :return: IADBBackend实例
        '''
        device_host = '127.0.0.1'
        if ':' in name:
            pattern = re.compile(r'^\d{3,5}$')
            pos = name.find(':')
            hostname = name[:pos]
            if not pattern.match(name[pos + 1:]):
                # adb connect device
                name = name[pos + 1:]
                device_host = hostname

        if name not in LocalADBBackend.list_device(device_host):
            raise RuntimeError('Device %s not exist in host %s' %
                               (name, device_host))

        return LocalADBBackend(device_host, name)

    def __init__(self, device_host, device_name, port=5037):
        self._device_host = device_host
        self._device_host_port = port
        self._device_name = device_name
        self._adb_client = ADBClient.get_client(self._device_host,
                                                self._device_host_port)

    @property
    def device_host(self):
        '''设备主机
        '''
        return self._device_host

    @property
    def device_name(self):
        '''设备名
        '''
        return self._device_name

    def run_adb_cmd(self, cmd, *args, **kwargs):
        '''执行adb命令
        '''
        timeout = kwargs.pop('timeout')
        sync = kwargs.pop('sync')
        return self._adb_client.call(cmd,
                                     self._device_name,
                                     *args,
                                     sync=sync,
                                     retry_count=1,
                                     timeout=timeout)


def static_result(func):
    '''固定返回结果函数
    '''

    def _wrap_func(self):
        attr = '_%s_result' % func.__name__
        if not hasattr(self, attr):
            result = func(self)
            setattr(self, attr, result)
        return getattr(self, attr)

    return _wrap_func


class ADB(object):
    '''封装ADB功能
    '''
    armeabi = 'armeabi'
    x86 = 'x86'

    connect_timeout = 300  # 连接设备的超时时间

    def __init__(self, backend):
        self._backend = backend
        self._device_name = self._backend.device_name
        self._root_state = EnumRootState.Unknown

        self._need_quote = None  # 执行shell命令时有些手机需要引号，有些不需要
        self._log_filter_thread_list = []  # 不打印log的线程id列表
        self._shell_prefix = None  # 有些设备上会有固定输出
        self._logcat_callbacks = []
        self._newline = None  # 不同手机使用的换行会不同

    @property
    def device_host(self):
        '''设备主机名
        '''
        return self._backend.device_host

    @property
    def device_name(self):
        '''设备名
        '''
        return self._backend.device_name

    def add_no_log_thread(self, thread):
        '''添加线程到不打印日志线程列表
        '''
        if not thread.ident in self._log_filter_thread_list:
            self._log_filter_thread_list.append(thread.ident)

    def remove_no_log_thread(self, thread):
        '''移除不打印日志线程列表中指定线程
        '''
        if thread.ident in self._log_filter_thread_list:
            self._log_filter_thread_list.remove(thread.ident)

    def run_adb_cmd(self, cmd, *args, **kwargs):
        '''执行adb命令
        '''
        retry_count = 3  # 默认最多重试3次
        if 'retry_count' in kwargs:
            retry_count = kwargs.pop('retry_count')
        timeout = 20
        if 'timeout' in kwargs:
            timeout = kwargs.pop('timeout')
        sync = True
        if 'sync' in kwargs:
            sync = kwargs.pop('sync')

        for _ in range(retry_count):
            if not threading.current_thread(
            ).ident in self._log_filter_thread_list:
                logger.info('adb %s:%s %s %s' %
                            (self._backend.device_host,
                             self._backend.device_name, cmd, ' '.join(args)))
            time0 = time_clock()
            try:
                result = self._backend.run_adb_cmd(cmd,
                                                   *args,
                                                   sync=sync,
                                                   timeout=timeout,
                                                   **kwargs)
            except Exception as e:
                logger.exception('Exec adb %s failed: %s' % (cmd, e))
                continue

            if not isinstance(result, tuple):
                return result
            if not threading.current_thread(
            ).ident in self._log_filter_thread_list:
                logger.info('执行ADB命令耗时：%s' % (time_clock() - time0))
            out, err = result

            if err:
                if b'error: device not found' in err:
                    self.run_adb_cmd('wait-for-device',
                                     retry_count=1,
                                     timeout=self.connect_timeout)  # 等待设备连接正常
                    return self.run_adb_cmd(cmd, *args, **kwargs)
                return err
            if isinstance(out, (bytes, str)):
                out = out.strip()
            return out

    def run_shell_cmd(self, cmd_line, root=False, **kwds):
        '''运行shell命令

        :param cmd_line: 要运行的命令行
        :param root: 是否使用root权限
        '''
        if isinstance(cmd_line, bytes):
            cmd_line = cmd_line.decode('utf8')

        if not self._newline:
            result = self.run_adb_cmd('shell', 'echo "1\n2"')
            if b'\r\n' in result:
                self._newline = b'\r\n'
            else:
                self._newline = b'\n'

        binary_output = False
        if 'binary_output' in kwds:
            binary_output = kwds.pop('binary_output')

        def _handle_result(result):
            if not isinstance(result, (bytes, str)):
                return result
            if self._newline != b'\n':
                result = result.replace(self._newline, b'\n')

            if binary_output:
                return result
            else:
                result = result.decode('utf8')

            if self._shell_prefix != None and self._shell_prefix > 0:
                result = '\n'.join(result.split('\n')[self._shell_prefix:])
            if result.startswith('WARNING: linker:'):
                # 虚拟机上可能会有这种错误：WARNING: linker: libdvm.so has text relocations. This is wasting memory and is a security risk. Please fix.
                lines = result.split('\n')
                idx = 1
                while idx < len(lines):
                    if not lines[idx].startswith('WARNING: linker:'):
                        break
                    idx += 1
                return '\n'.join(lines[idx:]).strip()
            else:
                return result

        if root:
            need_su = True
            if self._root_state == EnumRootState.Unknown:
                self._root_state = self.get_root_state()
            if self._root_state == EnumRootState.AdbdRoot:
                need_su = False
            elif self._root_state == EnumRootState.NonRoot:
                raise RuntimeError('device is not rooted')

            if not need_su:
                return self.run_shell_cmd(cmd_line, **kwds)
            if self._need_quote == None:
                self._check_need_quote()
            if self._need_quote:
                cmd_line = 'su -c \'%s\'' % cmd_line
            else:
                orig_cmd_line = cmd_line
                if not '&&' in orig_cmd_line:
                    cmd_line = 'su -c %s' % cmd_line
                else:
                    result = []
                    for cmd_line in orig_cmd_line.split('&&'):
                        cmd_line = 'su -c %s' % cmd_line
                        result.append(
                            _handle_result(
                                self.run_adb_cmd('shell', '%s' % cmd_line,
                                                 **kwds)))
                    return '\n'.join(result)

        return _handle_result(self.run_adb_cmd('shell', cmd_line, **kwds))

    def reboot(self, _timeout=180):
        '''重启手机'''
        try:
            self.run_adb_cmd('reboot', retry_count=1, timeout=30)
        except TimeoutError:
            # 使用强杀init进程方式重启手机
            self.kill_process(1)
            time.sleep(10)  # 等待手机重启
        if _timeout > 0:
            self.wait_for_boot_complete(_timeout)

    def wait_for_boot_complete(self, _timeout=180):
        '''等待手机启动完成'''
        # 手机重启完后 adbd Insecure 启动时会导致adb断开重连，qt4a框架己经实现了adb root权限功能，测试手机请不要安装 adbd Insecure
        import time
        print('等待手机启动完成...')
        self.run_adb_cmd('wait-for-device', timeout=_timeout)
        boot_complete = False
        attempts = 0
        wait_period = 5
        while not boot_complete and (attempts * wait_period) < _timeout:
            output = self.run_shell_cmd("getprop sys.boot_completed",
                                        retry_count=1)
            output = output.strip()
            if output == "1":
                boot_complete = True
            else:
                time.sleep(wait_period)
                attempts += 1
        if not boot_complete:
            raise RuntimeError("dev.bootcomplete 标志在  %s 秒后仍未设置，手机重启失败" %
                               _timeout)

    def start_logcat(self, process_list=[], params=''):
        '''运行logcat进程
        :param process_list: 要捕获日志的进程名或进程ID列表，为空则捕获所有进程
        :type process_list:  list
        '''
        if not hasattr(self, '_start_count'):
            self._start_count = 0
        self._start_count += 1
        if self._start_count > 1:
            return
        logger.debug('[ADB] start logcat')
        self.run_shell_cmd('logcat -c ' + params)  # 清除缓冲区
        if not hasattr(self, '_log_list'):
            self._log_list = []
        self._logcat_running = True
        self._log_pipe = self.run_shell_cmd('logcat -v threadtime ' + params,
                                            sync=False)

        # self._logcat_thread_func(process_list)

        self._logcat_thread = ThreadEx(target=self._logcat_thread_func,
                                       args=[process_list, params])
        self._logcat_thread.setDaemon(True)
        self._logcat_thread.start()
        self._log_filter_thread_list.append(self._logcat_thread.ident)

    def stop_logcat(self):
        '''停止logcat
        '''
        if not hasattr(self, '_start_count') or self._start_count <= 0:
            logger.warn('[ADB] logcat not start')
            return
        self._start_count -= 1
        if self._start_count > 0:
            return
        logger.debug('[ADB] stop logcat')
        self._logcat_running = False
        if hasattr(self, '_log_pipe'):
            if self._log_pipe.poll() == None:  # 判断logcat进程是否存在
                try:
                    self._log_pipe.terminate()
                except WindowsError as e:
                    logger.warn('terminate logcat process failed: %s' % e)

        if hasattr(self, '_logcat_thread'):
            if self._logcat_thread.ident in self._log_filter_thread_list:
                self._log_filter_thread_list.remove(self._logcat_thread.ident)
            else:
                logger.warn(
                    '%s not in %s' %
                    (self._logcat_thread.ident, self._log_filter_thread_list))

    def get_log(self, clear=True):
        '''获取已经保存的log
        '''
        if not hasattr(self, '_log_list'):
            return []
        result = self._log_list
        if clear:
            self._log_list = []
        return result

    def save_log(self, save_path):
        '''保存log
        '''
        if not hasattr(self, '_log_list'):
            return
        log_list = self.get_log()
        for i, log in enumerate(log_list):
            if isinstance(log, bytes):
                # 先编码为unicode
                for code in ['utf8', 'gbk']:
                    try:
                        log = log.decode(code)
                        break
                    except UnicodeDecodeError as e:
                        # logger.warn('decode with %s error: %s' % (code, e))
                        pass
                else:
                    log = repr(log)
            log_list[i] = log.encode('utf8') if not isinstance(log,
                                                               bytes) else log
        f = open(save_path, 'wb')
        f.write(b'\n'.join(log_list))
        f.close()

    def add_logcat_callback(self, callback):
        '''添加logcat回调
        '''
        if not callback in self._logcat_callbacks:
            self._logcat_callbacks.append(callback)

    def remove_logcat_callback(self, callback):
        '''移除logcat回调
        '''
        if callback in self._logcat_callbacks:
            self._logcat_callbacks.remove(callback)

    def insert_logcat(self, process_name, year, month_day, timestamp, level,
                      tag, tid, content):
        self._log_list.append(
            b'[%s] [%d-%s %s] %s/%s(%d): %s' %
            (utf8_encode(process_name), int(year), utf8_encode(month_day),
             utf8_encode(timestamp), utf8_encode(level), utf8_encode(tag),
             int(tid), utf8_encode(content)))
        pid = 0
        pattern = re.compile(r'^(.+)\((\d+)\)$')
        ret = pattern.match(process_name)
        if ret:
            process_name = ret.group(1)
            pid = int(ret.group(2))
        for callback in self._logcat_callbacks:
            callback(pid, process_name, '%s-%s' % (year, month_day), timestamp,
                     level, tag, int(tid), content)

    def _logcat_thread_func(self, process_list, params=''):
        '''获取logcat线程
        '''
        import re
        # pattern = re.compile(r'([A-Z])/([\w|.]+)\s*\(\s*(\d+)\):.+') #标准格式
        # pattern = re.compile(r'([\d|-]+)\s+([\d|:|\.]+)\s+(\d+)\s+(\d+)\s+(\w)\s+(\S+)\s*:\s+(.+)')  # [^:]
        # 会过滤掉只有内容和内容为空的情况：--------- beginning of /dev/log/main not match pattern；04-16 10:09:25.170  2183  2183 D AndroidRuntime:
        pattern = re.compile(
            r'([\d|-]+)\s+([\d|:|\.]+)\s+(\d+)\s+(\d+)\s+(\w)\s+(.*?)\s*:\s*(.*)'
        )
        # Date Time PID TID Level Tag Content
        pid_dict = {}
        filter_pid_list = []  # 没有找到匹配进程的列表
        zygote_pid = 0  # zygote进程ID

        while self._logcat_running:
            log = self._log_pipe.stdout.readline()
            log = enforce_utf8_decode(log).strip()

            if not log:
                if self._log_pipe.poll() != None:
                    logger.debug('logcat进程：%s 已退出' % self._log_pipe.pid)
                    # 进程已退出
                    # TODO: 解决logcat重复问题
                    if not self._logcat_running:
                        logger.info('logcat线程停止运行')
                        return
                    self._log_pipe = self.run_shell_cmd(
                        'logcat -v threadtime ' + params, sync=False)
                else:
                    continue

            if 'beginning of main' in log or 'beginning of system' in log:
                continue

            ret = pattern.match(log)
            if not ret:
                logger.info('log: %s not match pattern' % log)
                continue
            tag = ret.group(6).strip()
            if tag in [
                    'inject', 'dexloader', 'ActivityInspect', 'MethodHook',
                    'androidhook'
            ]:
                logger.info(log)  # 测试桩日志加入到qt4a日志中
                continue

            if tag in ['Web Console']:
                if ret.group(7).startswith('[ClickListener]'):
                    logger.info(log)  # WebView的控件点击信息
                    continue

            pid = int(ret.group(3))
            if pid in filter_pid_list:
                continue

            init_process_list = ['<pre-initialized>', 'zygote']

            if not pid in pid_dict.keys():
                for item in self.list_process():
                    if zygote_pid == 0 and item[
                            'proc_name'] == 'zygote' and item['ppid'] == 1:
                        # zygote父进程ID为1
                        zygote_pid = item['pid']

                    for init_process in init_process_list:
                        if item['pid'] in pid_dict and pid_dict[item[
                                'pid']].startswith(init_process) and not item[
                                    'proc_name'].startswith(init_process):

                            for i in range(len(self._log_list) - 1, -1, -1):
                                # 修复之前记录的“<pre-initialized>”进程
                                pre_process_name = b'[%s(%d)]' % (init_process,
                                                                  item['pid'])
                                if not pre_process_name in self._log_list[i]:
                                    continue
                                if process_list:
                                    del_flag = True
                                    for process in process_list:
                                        if pid == process or item[
                                                'proc_name'].startswith(
                                                    process):
                                            # 替换为真实进程名
                                            self._log_list[i] = self._log_list[
                                                i].replace(
                                                    pre_process_name,
                                                    ('[%s(%d)]' %
                                                     (item['proc_name'],
                                                      item['pid'])))
                                            del_flag = False
                                            break
                                    if del_flag:
                                        # 不在需要记录的进程列表中
                                        del self._log_list[i]
                                else:
                                    # 直接替换
                                    self._log_list[
                                        i] = self._log_list[i].replace(
                                            pre_process_name,
                                            ('[%s(%d)]' %
                                             (item['proc_name'], item['pid'])))
                    pid_dict[item['pid']] = item['proc_name']
#                     if item['proc_name'] in init_process_list and item['pid'] != zygote_pid:
#                         pid_dict[item['pid']] += '(%d)' % item['pid']
                if not pid in pid_dict.keys():
                    filter_pid_list.append(pid)
                    continue

            found = False
            if not process_list:
                found = True  # 不指定进程列表则捕获所有进程
            else:
                for process in process_list:
                    if pid == process or (
                            pid in pid_dict and
                        (pid_dict[pid].startswith(process)
                         or pid_dict[pid].startswith('<pre-initialized>') or
                         (pid_dict[pid].startswith('zygote')
                          and pid != zygote_pid))):  # 进程初始化中
                        found = True
                        break

            if found:
                import datetime
                if not hasattr(self, '_year'):
                    self._year = datetime.date.today().year
                try:
                    self.insert_logcat('%s(%d)' % (pid_dict.get(pid), pid),
                                       self._year, ret.group(1), ret.group(2),
                                       ret.group(5), ret.group(6),
                                       ret.group(4), ret.group(7))
                except:
                    logger.exception('Insert logcat failed: %r' % log)

    @static_result
    def get_root_state(self):
        '''获取Root状态
        '''
        if self.is_adbd_root():
            return EnumRootState.AdbdRoot
        result = self.run_shell_cmd('su -c id')
        if 'su: not found' in result:
            return EnumRootState.NonRoot
        elif 'uid=0(root)' in result:
            return EnumRootState.SuRoot
        return EnumRootState.NonRoot

    @static_result
    def is_adbd_root(self):
        '''adbd是否以root权限运行
        '''
        result = self.run_shell_cmd('id')
        logger.debug('is_adbd_root: %s' % result)
        return 'uid=0(root)' in result

    def is_rooted(self):
        return self.get_root_state() in (EnumRootState.AdbdRoot,
                                         EnumRootState.SuRoot)

    def _check_need_quote(self, timeout=20):
        '''
        '''
        cmd = "su -c 'ls -l /data/data'"  # 默认方式为加引号，避免有些手机上对于存在空格的命令容易出错
        # 联想S899T上发现不加引号返回结果为空
        result = self.run_shell_cmd(cmd, timeout=timeout)
        if result.find('com.android.phone') >= 0:
            self._need_quote = True
        else:
            logger.debug(result)
            self._need_quote = False

    def _set_system_writable(self):
        '''修改system分区可写
        '''
        output = self.run_shell_cmd('mount -o rw,remount /system', True)
        result = self.run_shell_cmd('mount')
        for line in result.split('\n'):
            if '/system' in line and 'rw,' in line:
                return True
        raise RuntimeError('remount /system failed: %s' % output.strip())

    def forward(self, port1, port2, type='tcp'):
        '''端口转发
        :param port1: PC上的TCP端口
        :type port1:  int
        :param port2: 手机上的端口或LocalSocket地址
        :type port2:  int或String
        :param type:  手机上的端口类型
        :type type:   String，LocalSocket地址使用“localabstract”
        '''
        while 1:
            ret = self.run_adb_cmd('forward', 'tcp:%d' % (port1),
                                   '%s:%s' % (type, port2))
            if not 'cannot bind socket' in ret and not 'cannot bind to socket' in ret:
                return port1
            port1 += 1

    def remove_forward(self, port):
        '''移除指定的端口映射
        '''
        return 'cannot remove listener' in self.run_adb_cmd(
            'forward', '--remove', 'tcp:%d' % (port))

    def create_tunnel(self, addr, type='tcp'):
        '''直接创建与手机中socket服务端的连接
        '''
        sock = self.run_adb_cmd('create_tunnel', '%s:%s' % (type, addr))
        if sock == '':
            return None
        return sock

    def _push_file(self, src_path, dst_path):
        '''以指定身份拷贝文件到手机中
        '''
        result = self.run_adb_cmd('push', src_path, dst_path, timeout=None)
        if 'No space left on device' in result or 'No such file or directory' in result:
            # 如果源文件不存在不会执行到这里
            raise RuntimeError('设备存储空间不足')
        return result

    def push_file(self, src_path, dst_path, uid=None):
        '''以指定身份拷贝文件到手机中
        '''
        if six.PY2 and isinstance(dst_path, unicode):
            dst_path = dst_path.encode('utf8')
        file_size = 0
        for _ in range(3):
            file_size = os.path.getsize(src_path)  # 防止取到的文件大小不正确
            result = self._push_file(src_path, dst_path)
            if file_size == 0:
                logger.warn('文件大小为0')
                return result
            if ('%d' % file_size) in result:
                try:
                    _, file_list = self.list_dir(dst_path)
                    if len(file_list) == 0:
                        logger.warn('push file failed: file not exist')
                    elif file_list[0]['size'] != file_size:
                        logger.warn(
                            'push file failed: file size error, expect %d, actual is %d'
                            % (file_size, file_list[0]['size']))
                        self.delete_file(dst_path)
                    else:
                        logger.debug(repr(file_list[0]))
                        if uid:
                            self.chown(dst_path, uid, uid)
                        return result
                except RuntimeError as e:
                    err_msg = e.args[0]
                    if six.PY2 and (not isinstance(err_msg, unicode)):
                        err_msg = err_msg.decode('utf8')
                    logger.warn(err_msg)
            else:
                logger.warn('push file failed: %s' % result)
        raise RuntimeError('Push file [%d]%s to device [%r] failed: %s' %
                           (file_size, src_path, self._device_name, result))

    def pull_file(self, src_path, dst_path):
        '''从手机中拉取文件
        '''
        result = self.run_adb_cmd('pull', src_path, dst_path, timeout=600)
        if 'failed to copy' in result:
            raise RuntimeError(result)
        if not 'bytes in' in result:
            logger.warn(repr(result))
            logger.debug(self.run_shell_cmd('ls -l %s' % src_path, True))
        return result

    @staticmethod
    def _get_package_name(apk_path):
        '''获取安装包名
        '''
        import zipfile
        from ._axmlparser import AXMLPrinter
        package_name = ''
        zf = zipfile.ZipFile(apk_path, mode='r')
        for i in zf.namelist():
            if i == "AndroidManifest.xml":
                printer = AXMLPrinter(zf.read(i))
                package_name = printer.get_xml_obj().getElementsByTagName(
                    'manifest')[0].getAttribute('package')
                break
        if not package_name:
            raise RuntimeError('获取安装包中的包名信息失败')
        return package_name

    def _install_apk(self, apk_path, package_name, reinstall=False):
        '''
        '''
        if self.get_sdk_version() <= 19:
            timeout = 3 * 60
        else:
            timeout = 6 * 60  # TODO: 9100安装5.0系统后安装应用超过3分钟
        cmdline = 'pm install %s %s' % ('-r' if reinstall else '', apk_path)
        ret = ''
        for i in range(3):
            # 处理一些必然会失败的情况，如方法数超标之类的问题
            try:
                if not self.is_rooted():
                    # 通知QT4A助手开始监控应用安装
                    self.run_shell_cmd('am broadcast -a startInstallMonitor')
                    ret = self.run_shell_cmd(cmdline,
                                             retry_count=1,
                                             timeout=timeout)
                else:
                    proc = self.run_shell_cmd(cmdline, True,
                                              sync=False)  # 使用root权限安装
                    time0 = time.time()
                    close_popup_count = 0
                    while time.time() - time0 < timeout:
                        if proc.poll() != None:
                            ret = proc.communicate()[0]
                            break
                        elif time.time() - time0 > 10 and close_popup_count < 2:
                            # 有些系统上弹窗会出现很久，关掉弹窗可以避免超时
                            self.run_shell_cmd('input keyevent 4')
                            close_popup_count += 1
                        time.sleep(1)
                    else:
                        raise TimeoutError('Install package timeout')

                    if not b'Success' in ret:
                        logger.warn('install with root failed: %s' % ret)
                        if not b'INSTALL_' in ret.strip().split(b'\n')[-1]:
                            # 权限弹窗导致的安装失败
                            ret = self.run_as('system',
                                              cmdline,
                                              retry_count=1,
                                              timeout=timeout)

                logger.debug(ret)
                if b'Success' in ret:
                    return True, ret
                elif i > 1 and b'INSTALL_FAILED_ALREADY_EXISTS' in ret:
                    # 出现至少一次超时，认为安装完成
                    return True, 'Success'
                elif b'INSTALL_FAILED_ALREADY_EXISTS' in ret:
                    # 尝试覆盖安装
                    return self._install_apk(apk_path, package_name, True)
                elif b'INSTALL_PARSE_FAILED_NO_CERTIFICATES' in ret or b'INSTALL_PARSE_FAILED_UNEXPECTED_EXCEPTION' in ret:
                    if i >= 2:
                        return False, ret
                    time.sleep(10)
                    continue
                elif b'INSTALL_FAILED_UPDATE_INCOMPATIBLE' in ret:
                    # 强制卸载应用
                    self.uninstall_app(package_name)
                    return self._install_apk(apk_path, package_name, False)
                elif b'INSTALL_PARSE_FAILED_INCONSISTENT_CERTIFICATES' in ret or b'INSTALL_FAILED_DEXOPT' in ret:
                    # 必须卸载安装
                    if not reinstall:
                        return False, ret
                    self.uninstall_app(package_name)
                    return self._install_apk(apk_path, package_name, False)
                elif b'INSTALL_FAILED_INSUFFICIENT_STORAGE' in ret:
                    # 有可能是存在/data/app-lib/packagename-1目录导致的
                    for i in (1, 2):
                        dir_path = '/data/app-lib/%s-%d' % (package_name, i)
                        if 'No such file or directory' in self.run_shell_cmd(
                                'ls -l %s' % dir_path, True):
                            continue
                        else:
                            self.delete_folder(dir_path)
                            break
                    else:
                        return False, ret
                elif b'INSTALL_FAILED_UID_CHANGED' in ret or b'INSTALL_FAILED_INTERNAL_ERROR' in ret:
                    # /data/data目录下存在文件夹没有删除
                    dir_path = '/data/data/%s' % package_name
                    for _ in range(3):
                        # 防止删除没有成功
                        self.delete_folder(dir_path)
                        if b'No such file or directory' in self.run_shell_cmd(
                                'ls -l %s' % dir_path, True):
                            break
                    continue
                elif b'INSTALL_FAILED_CANCELLED_BY_USER' in ret:
                    # 一般是ROM需要手动确认安装，改用system权限安装
                    ret = self.run_shell_cmd('su system %s' % cmdline,
                                             timeout=timeout)
                    if b'Success' in ret:
                        return True, ret
                else:
                    return False, ret
            except TimeoutError as e:
                logger.warn('install app timeout: %r' % e)
        else:
            logger.warn('install app failed')
            ret = self.run_shell_cmd(cmdline, timeout=timeout)  # 改用非root权限安装
            logger.debug(ret)
            if b'Success' in ret or b'INSTALL_FAILED_ALREADY_EXISTS' in ret:
                return True, 'Success'

        return False, ret

    def install_apk(self, apk_path, reinstall=False):
        '''安装应用
        '''
        if not os.path.exists(apk_path):
            raise RuntimeError('APK: %s 不存在' % apk_path)
        package_name = self._get_package_name(apk_path)

        tmp_path = '/data/local/tmp/%s.apk' % package_name
        self.push_file(apk_path, tmp_path)

        if not reinstall:
            self.uninstall_app(package_name)  # 先卸载，再安装
            result = self._install_apk(tmp_path, package_name, reinstall)
        else:
            result = self._install_apk(tmp_path, package_name, reinstall)
        # logger.debug(result)

        if result[0] == False:
            if not b'Failure' in result[1]:
                # 一般这种情况都是由于adb server意外退出导致，此时安装过程还会继续
                logger.warn('install app: %r' % result[1])
                timeout = 30
                time0 = time.time()
                while time.time() - time0 < timeout:
                    # 等待应用安装完成
                    if self.get_package_path(package_name):
                        break
                    time.sleep(1)
                else:
                    result = self._install_apk(tmp_path, package_name,
                                               reinstall)
            else:
                err_msg = result[1]
                if six.PY2:
                    if isinstance(err_msg, unicode):
                        err_msg = err_msg.encode('utf8')
                    if isinstance(package_name, unicode):
                        package_name = package_name.encode('utf8')
                raise InstallPackageFailedError('安装应用%s失败：%s' %
                                                (package_name, err_msg))
        try:
            self.delete_file('/data/local/tmp/*.apk')
        except TimeoutError:
            pass

    def uninstall_app(self, pkg_name):
        '''卸载应用
        '''
        result = ''
        if not self.get_package_path(pkg_name):
            return True
        for _ in range(5):
            try:
                result = self.run_adb_cmd('uninstall',
                                          pkg_name,
                                          retry_count=1,
                                          timeout=30)
            except RuntimeError:
                logger.exception('uninstall %s failed' % pkg_name)
                time.sleep(10)
            else:
                result = general_encode(result)
                break
        else:
            raise
        logger.debug('uninstall %s result: %r' % (pkg_name, result))
        if self.is_rooted():
            # 清理卸载可能遗留的cache文件
            cpu_abi = 'arm'
            if self.get_cpu_abi() == 'x86':
                cpu_abi = 'x86'  # TODO: 支持64位CPU
            self.delete_file('/data/dalvik-cache/%s/data@app@%s-*' %
                             (cpu_abi, pkg_name))
        return 'Success' in result

# ifndef __RELEASE__

    @Deprecated('uninstall_app')
    def uninstall_apk(self, pkg_name):
        '''卸载应用
        '''
        return self.uninstall_app(pkg_name)


# endif

    @encode_wrap
    def get_package_path(self, pkg_name):
        '''获取应用安装包路径
        '''
        for _ in range(3):
            # 为避免某些情况下获取不到应用安装包路径，重试多次
            result = self.run_shell_cmd('pm path %s' % pkg_name)
            logger.debug('get_package_path: %r' % result)
            pos = result.find('package:')
            if pos >= 0:
                return result[pos + 8:]
            time.sleep(1)
        return ''

    @encode_wrap
    def get_package_version(self, pkg_name):
        '''获取应用版本
        '''
        result = self.run_shell_cmd('dumpsys package %s' % pkg_name)
        for line in result.split('\n'):
            line = line.strip()
            if line.startswith('versionName='):
                return line[12:]

    @encode_wrap
    def _build_intent_extra_string(self, extra):
        '''构造intent参数列表
        '''
        extra_str = ''
        for key in extra:  # 指定额外参数
            p_type = ''
            value = extra[key]
            if isinstance(value, bytes):
                value = value.decode('utf8')

            if value in ['true', 'false']:
                p_type = 'z'  # EXTRA_BOOLEAN_VALUE
            elif isinstance(value, int):
                if is_int(value):
                    p_type = 'i'  # EXTRA_INT_VALUE
                else:
                    p_type = 'l'  # EXTRA_LONG_VALUE
            elif isinstance(value, float):
                p_type = 'f'  # EXTRA_FLOAT_VALUE
            elif value.startswith('file://'):  # EXTRA_URI_VALUE
                p_type = 'u'
            param = '-e%s %s %s ' % (p_type, key,
                                     ('"%s"' % value) if not p_type else value)
            if p_type:
                param = u'-' + param
            extra_str += param
        if len(extra_str) > 0:
            extra_str = extra_str[:-1]
        return extra_str

    @encode_wrap
    def start_activity(self,
                       activity_name,
                       action='',
                       type='',
                       data_uri='',
                       extra={},
                       wait=True):
        '''打开一个Activity
        Warning: Activity not started, intent has been delivered to currently running top-most instance.
        Status: ok
        ThisTime: 0
        TotalTime: 0
        WaitTime: 2
        Complete
        '''
        if activity_name:
            activity_name = '-n %s' % activity_name
        if action:  # 指定Action
            action = '-a %s ' % action
        if type:
            type = '-t %s ' % type
        if data_uri:
            data_uri = '-d "%s" ' % data_uri
        extra_str = self._build_intent_extra_string(extra)
        W = u''
        if wait:
            W = '-W'  # 等待启动完成才返回
        # 如果/sbin/sh指向busybox，就会返回“/sbin/sh: am: not found”错误
        # 返回am找不到是因为am缺少“#!/system/bin/sh”
        command = 'am start %s %s %s%s%s%s' % (W, activity_name, action, type,
                                               data_uri, extra_str)
        if command[-1] == ' ':
            command = command[:-1]
        result = self.run_shell_cmd(command, timeout=15, retry_count=3)
        if 'Permission Denial' in result or (wait and
                                             (not 'Activity:' in result
                                              or not 'Complete' in result)):
            # 使用root权限运行
            if self.is_rooted():
                result = self.run_shell_cmd(command,
                                            True,
                                            timeout=15,
                                            retry_count=3)
            else:
                package_name = activity_name.split('/')[0].split()[1]
                result = self.run_as(package_name,
                                     command,
                                     timeout=15,
                                     retry_count=3)
            # raise RuntimeError('打开Activity失败：\n%s' % result)
        if 'startActivityAndWait asks to run as user -2 but is calling from user 0' in result:
            command += ' --user 0'
            result = self.run_as(package_name,
                                 command,
                                 timeout=15,
                                 retry_count=3)
            logger.info('start activity command:%s' % command)
        if 'Permission Denial' in result or (
                'run as user -2 but is calling from user 0' in result) or (
                    wait and not 'Complete' in result):
            raise RuntimeError('start activity failed: %s' % result)

        ret_dict = {}
        for line in result.split('\n'):
            if ': ' in line:
                key, value = line.split(': ')
                ret_dict[key] = value
        if 'Error' in ret_dict:
            raise RuntimeError(ret_dict['Error'])
        return ret_dict

    def start_service(self, service_name, extra={}):
        '''启动服务
        '''
        extra_str = self._build_intent_extra_string(extra)
        command = 'am startservice -n %s %s' % (service_name, extra_str)
        if command[-1] == ' ':
            command = command[:-1]
        result = self.run_shell_cmd(command, timeout=15, retry_count=3)
        if 'no service started' in result or 'java.lang.SecurityException' in result:
            raise RuntimeError('start service %s failed: %s' %
                               (service_name, result))

    def stop_service(self, service_name):
        '''停止服务
        '''
        result = self.run_shell_cmd('am stopservice -n %s' % service_name,
                                    timeout=15,
                                    retry_count=3)
        if not 'Service stopped' in result and not 'was not running' in result:
            raise RuntimeError('stop service failed: %s' % result)

    def send_broadcast(self, action, extra={}):
        '''发送广播

        :param action: 广播使用的ACTION
        :type  action: string
        :param extra:  额外参数
        :type  extra:  dict
        '''
        extra_str = self._build_intent_extra_string(extra)
        command = 'am broadcast -a %s %s' % (action, extra_str)
        result = self.run_shell_cmd(command)
        if not 'Broadcast completed: result=0' in result:
            raise RuntimeError('Send broadcast failed: %s' % result)

    def get_property(self, prop):
        '''读取属性
        '''
        return self.run_shell_cmd('getprop %s' % prop)

    def set_property(self, prop, value):
        '''设置属性
        '''
        self.run_shell_cmd('setprop %s %s' % (prop, value), self.is_rooted())

    @static_result
    def get_cpu_abi(self):
        '''获取系统的CPU架构信息
        '''
        ret = self.run_shell_cmd('getprop ro.product.cpu.abi')
        if not ret:
            ret = 'armeabi'  # 有些手机可能没有这个系统属性
        return ret

    @static_result
    def get_device_model(self):
        '''获取设备型号
        '''
        model = self.run_shell_cmd('getprop ro.product.model')
        brand = self.run_shell_cmd('getprop ro.product.brand')
        if model.find(brand) >= 0:
            return model
        return '%s %s' % (brand, model)

    @static_result
    def get_system_version(self):
        '''获取系统版本
        '''
        return self.run_shell_cmd('getprop ro.build.version.release')

    @static_result
    def get_sdk_version(self):
        '''获取SDK版本
        '''
        return int(self.run_shell_cmd('getprop ro.build.version.sdk'))

    def get_uid(self, app_name):
        '''获取APP的uid
        '''
        result = self.run_shell_cmd('ls -l /data/data', True)
        for line in result.split('\n'):
            items = line.split(' ')
            for item in items:
                if not item:
                    continue
                if item == app_name:
                    return items[1]
        return None

    def is_selinux_opened(self):
        '''selinux是否是enforcing状态
        '''
        if self.get_sdk_version() < 18:
            return False
        return 'Enforcing' in self.run_shell_cmd('getenforce', True)

    def close_selinux(self):
        '''关闭selinux
        '''
        result = self.run_shell_cmd('setenforce 0', True)
        if 'Permission denied' in result:
            return False
        return True

    def chmod(self, file_path, attr):
        '''修改文件/目录属性

        :param file_path: 文件/目录路径
        :type file_path:  string
        :param attr:      设置的属性值，如：777
        :type attr:       int
        '''

        def _parse(num):
            num = str(num)
            attr = ''
            su_flag = ''
            if len(num) == 4:
                su_flag = int(num[0])
                num = num[1:]
            for c in num:
                c = int(c)
                if c & 4:
                    attr += 'r'
                else:
                    attr += '-'
                if c & 2:
                    attr += 'w'
                else:
                    attr += '-'
                if c & 1:
                    attr += 'x'
                else:
                    attr += '-'

            if su_flag and su_flag == 4:
                attr = attr[:2] + 's' + attr[3:]
            return attr

        ret = self.run_shell_cmd('chmod %s %s' % (attr, file_path),
                                 self.is_rooted())
        dir_list, file_list = self.list_dir(file_path)

        if len(dir_list) == 0 and len(file_list) == 1 and file_path.endswith(
                '/' + file_list[0]['name']):
            # 这是一个文件
            new_attr = file_list[0]['attr']
        else:
            # 目录
            dir_name = file_path.split('/')[-1]
            parent_path = '/'.join(file_path.split('/')[:-1])
            dir_list, _ = self.list_dir(parent_path)
            for dir in dir_list:
                if dir['name'] == dir_name:
                    new_attr = dir['attr']
                    break

        if new_attr != _parse(attr):
            logger.warn('chmod failed: %r(%s)' % (ret, new_attr))
            return self.chmod(file_path, attr)
        return new_attr

    def chown(self, file_path, uid, gid):
        '''修改文件的拥有者和群组

        :param file_path: 文件路径
        :type file_path:  string
        :param uid:       拥有者
        :type uid:        string
        :param gid:       群组
        :type gid:        string
        '''
        self.run_shell_cmd('chown %s:%s %s' % (uid, gid, file_path), True)

    def mkdir(self, dir_path, mod=None):
        '''创建目录
        '''
        cmd = 'mkdir %s' % (dir_path)
        ret = self.run_shell_cmd(cmd, self.is_rooted())
        #        if not 'File exists' in ret:
        #            #加了-p参数貌似不会返回这个提示信息
        try:
            self.list_dir(dir_path)
        except RuntimeError as e:
            logger.warn('mkdir %s failed: %s(%s)' % (dir_path, ret, e))
            return self.mkdir(dir_path, mod)
        # 修改权限
        if mod != None:
            self.chmod(dir_path, mod)

    def list_dir(self, dir_path):
        '''列取目录
        '''
        if ' ' in dir_path:
            dir_path = '"%s"' % dir_path
        use_root = self.is_rooted()
        if use_root and dir_path.startswith('/sdcard') or dir_path.startswith(
                '/storage/') or dir_path.startswith('/mnt/'):
            # 部分手机上发现用root权限访问/sdcard路径不一致
            use_root = False
        result = self.run_shell_cmd('ls -l %s' % dir_path, use_root)

        if 'Permission denied' in result:
            raise PermissionError(result)
        if 'No such file or directory' in result:
            raise RuntimeError('file or directory %s not exist' % dir_path)
        if 'Not a directory' in result:
            raise RuntimeError(u'%s %s' % (dir_path, result))

        dir_list = []
        file_list = []

        def _handle_name(name):
            return name.split('/')[-1]

        is_toybox = self.get_sdk_version() >= 24
        is_busybox = None
        # busybox格式 -rwxrwxrwx    1 shell    shell        13652 Jun  3 10:56 /data/local/tmp/qt4a/inject

        for line in result.split('\n'):
            items = line.split()
            if len(items) < 6:
                continue  # (6, 7, 9)
            if not line[0] in ('-', 'd', 'l'):
                continue

            is_dir = items[0][0] == 'd'  # 是否是目录
            is_link = items[0][0] == 'l'  # 软链
            if is_busybox == None:
                if is_toybox:
                    item = items[5]  # 日期字段
                else:
                    item = items[4]  # 日期字段
                    if is_dir or is_link:
                        item = items[3]  # 目录和软链没有size字段
                pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
                if pattern.match(item):
                    is_busybox = False
                else:
                    is_busybox = True

            if not is_busybox:
                # 防止文件名称中有空格
                if not is_toybox:
                    if not is_dir and not is_link and len(items) > 7:
                        items[6] = line[line.find(items[6]):].strip()
                    elif is_dir and len(items) > 6:
                        items[5] = line[line.find(items[5]):].strip()
                else:
                    if not is_dir and not is_link and len(items) > 8:
                        items[7] = line[line.find(items[7]):].strip()
                    elif is_dir and len(items) > 7:
                        items[6] = line[line.find(items[6]):].strip()

            attrs = items[0]
            if attrs[0] == 'd':
                if is_busybox:
                    name = _handle_name(items[8])
                elif is_toybox:
                    name = items[7]
                else:
                    name = items[5]
                dir_list.append({'name': name, 'attr': attrs[1:]})
            elif attrs[0] == '-':
                if is_busybox:
                    name = _handle_name(items[8])
                    size = int(items[4])
                    last_modify_time = items[7]
                elif is_toybox:
                    name = _handle_name(items[7])
                    size = int(items[4])
                    last_modify_time = time.strptime(
                        '%s %s:00' % (items[5], items[6]), "%Y-%m-%d %X")
                else:
                    name = items[6]
                    size = int(items[3])
                    try:
                        last_modify_time = time.strptime(
                            '%s %s:00' % (items[4], items[5]), "%Y-%m-%d %X")
                    except:
                        # TODO: 即将删掉，调试用
                        logger.info('line=%s' % line)
                        raise
                file_list.append({
                    'name': name,
                    'attr': attrs[1:],
                    'size': size,
                    'last_modify_time': last_modify_time
                })
            elif attrs[0] == 'l':  # link
                if is_busybox:
                    name = _handle_name(items[8])
                    last_modify_time = items[7]
                    link = items[10]
                elif is_toybox:
                    name = items[7]
                    last_modify_time = time.strptime(
                        '%s %s:00' % (items[5], items[6]), "%Y-%m-%d %X")
                    link = items[9]
                else:
                    name = items[5]
                    last_modify_time = time.strptime(
                        '%s %s:00' % (items[3], items[4]), "%Y-%m-%d %X")
                    link = items[7]
                file_list.append({
                    'name': name,
                    'attr': attrs[1:],
                    'link': link,
                    'last_modify_time': last_modify_time
                })

        return dir_list, file_list

    def get_sdcard_path(self):
        '''获取sdcard路径
        '''
        path = '/sdcard'
        while True:
            dir_list, file_list = self.list_dir(path)
            if len(dir_list) == 0 and len(
                    file_list) == 1 and 'link' in file_list[0]:
                # another link
                path = file_list[0]['link']
            else:
                break
        return path

    def get_file_info(self, file_path):
        '''获取文件信息
        '''
        return self.list_dir(file_path)[1][0]

    def copy_file(self, src_path, dst_path):
        '''在手机上拷贝文件
        '''
        if not hasattr(self, '_has_cp'):
            self._has_cp = 'not found' not in self.run_shell_cmd('cp')
        if self._has_cp:  # 不是所有的ROM都有cp命令
            self.run_shell_cmd('cp %s %s' % (src_path, dst_path),
                               self.is_rooted())
        else:
            self.run_shell_cmd('cat %s > %s' % (src_path, dst_path),
                               self.is_rooted(),
                               timeout=30)  # 部分手机上发现此方法耗时较多

    def delete_file(self, file_path):
        '''删除手机上文件
        '''
        if '*' in file_path:
            # 使用通配符时不能使用引号
            self.run_shell_cmd('rm -f %s' % file_path, self.is_rooted())
        else:
            file_path = file_path.replace('"', r'\"')
            self.run_shell_cmd('rm -f "%s"' % file_path, self.is_rooted())

    def delete_folder(self, folder_path):
        '''删除手机上的目录
        '''
        folder_path = folder_path.replace('"', r'\"')
        self.run_shell_cmd('rm -R "%s"' % folder_path, self.is_rooted())

    def run_as_by_app(self, package_name, cmdline, **kwargs):
        '''在app中执行命令
        '''
        cmd_res_path = '/sdcard/qt4a_cmd_res.txt'
        self.delete_file(cmd_res_path)
        timeout = 30
        if 'timeout' in kwargs:
            timeout = kwargs['timeout']
        try:
            self.start_activity(
                '%s/com.test.androidspy.inject.CmdExecuteActivity' %
                package_name,
                extra={
                    'cmdline': cmdline,
                    'timeout': timeout
                },
                wait=False)
        except Exception as e:
            if 'com.test.androidspy.inject.CmdExecuteActivity} does not exist' in e.args[
                    0]:
                raise RuntimeError(
                    '该命令需要对apk重打包才能执行，请使用`qt4a-manage repack-apk -p /path/to/apk`命令进行重打包并安装后重试！'
                )
            raise
        cmd_argv_list = cmdline.split()
        if len(cmd_argv_list) > 1 and cmd_argv_list[
                0] == 'pm' and cmd_argv_list[1] == 'clear':
            logger.info('run cmd:%s,return Success' % cmdline)
            time.sleep(2)
            return 'Success'

        time0 = time.time()
        while time.time() - time0 < timeout:
            try:
                self.list_dir(cmd_res_path)
                result = self.run_shell_cmd("cat %s" % cmd_res_path)
                return result
            except RuntimeError as e:
                logger.info('run_as_by_app exception:%s' % e)
                time.sleep(1)
        raise TimeoutError("run_as_by_app timeout:%d" % timeout)

    def run_as(self, package_name, cmdline, **kwargs):
        '''以package_name权限执行命令
        '''
        if self.is_rooted():
            if self._need_quote:
                cmdline = '"%s"' % cmdline
            cmdline = 'su %s %s' % (package_name, cmdline)
            return self.run_shell_cmd(cmdline, False, **kwargs)

        if ':' in package_name:
            package_name = package_name.split(':')[0]  # 允许传入进程名
        if '&&' in cmdline:
            cmndline = 'run-as %s sh -c "%s"' % (package_name, cmdline)
        else:
            cmndline = 'run-as %s %s' % (package_name, cmdline)
        result = self.run_shell_cmd(cmndline, **kwargs)
        run_as_succ = False
        if 'is unknown' in result:
            logger.info('Package %s not installed' % package_name)
        elif 'not debuggable' in result:
            logger.info('Package %s is not debuggable' % package_name)
        elif 'Could not set capabilities: Operation not permitted' in result:
            logger.info('Samsung device has bug with run-as command')
        elif 'run-as: exec failed for' in result:
            raise RuntimeError(result)
        else:
            run_as_succ = True
        if not run_as_succ:
            try:
                result = self.run_as_by_app(package_name, cmdline, **kwargs)
            except RuntimeError:
                logger.exception('run %s as %s by app failed' %
                                 (cmdline, package_name))
                raise PermissionError('run %s as %s failed' %
                                      (cmdline, package_name))
        return result

    def is_app_process64(self, process):
        '''是否是64位应用进程

        :param process: 进程名或进程ID
        :tytpe process: string/int
        '''
        process_name = ''
        if isinstance(process, six.string_types) and not process.isdigit():
            process_name = process
            pid = self.get_pid(process)
        else:
            pid = int(process)
        if pid <= 0:
            raise ValueError('process %s not exist' % process)
        if self.is_rooted():
            return 'app_process64' in self.run_shell_cmd(
                'ls -l /proc/%d/exe' % pid, True)
        elif process_name:
            return 'app_process64' in self.run_as(process_name,
                                                  'ls -l /proc/%d/exe' % pid)
        else:
            raise ValueError('Non root device must pass process name')

    def _list_process(self):
        '''获取进程列表
        '''
        cmdline = 'ps'
        if self.get_sdk_version() >= 26:
            cmdline += ' -A'
        result = self.run_shell_cmd(cmdline).strip()
        lines = result.split('\n')
        busybox = False
        if lines[0].startswith('PID'):
            busybox = True

        result_list = []
        for i in range(1, len(lines)):
            lines[i] = lines[i].strip()
            if not lines[i]:
                continue
            items = lines[i].split()
            if not busybox:
                if len(items) < 9:
                    err_msg = "ps命令返回格式错误：\n%s" % lines[i]
                    if len(items) == 8:
                        result_list.append({
                            'pid': int(items[1]),
                            'ppid': int(items[2]),
                            'proc_name': items[7]
                        })
                    else:
                        raise RuntimeError(err_msg)
                else:
                    proc_name = items[8]
                    if len(proc_name) <= 1 and len(items) > 9:
                        proc_name = items[9]
                    result_list.append({
                        'pid': int(items[1]),
                        'ppid': int(items[2]),
                        'proc_name': proc_name
                    })
            else:
                idx = 4
                cmd = items[idx]
                if len(cmd) == 1:
                    # 有时候发现此处会有“N”
                    idx += 1
                    cmd = items[idx]
                idx += 1
                if cmd[0] == '{' and cmd[-1] == '}':
                    cmd = items[idx]
                ppid = 0
                if items[1].isdigit():
                    ppid = int(items[1])  # 有些版本中没有ppid
                result_list.append({
                    'pid': int(items[0]),
                    'ppid': ppid,
                    'proc_name': cmd
                })
        return result_list

    def list_process(self):
        '''获取进程列表
        '''
        for _ in range(3):
            try:
                return self._list_process()
            except RuntimeError as e:
                logger.warn('%s' % e)
        else:
            raise RuntimeError('获取进程列表失败')

    def get_pid(self, proc_name):
        '''获取进程ID
        '''
        process_list = self.list_process()
        for process in process_list:
            if process['proc_name'] == proc_name:
                return process['pid']
        return 0

    def get_process_status(self, pid):
        '''获取进程状态信息
        '''
        ret = self.run_shell_cmd('cat /proc/%d/status' % pid, True)
        result = {}
        for line in ret.split('\n'):
            if not line:
                continue
            if not ':' in line:
                logger.warn('get_process_status line error: %r' % line)
                continue
            key, value = line.split(':')
            result[key] = value.strip()
        return result

    def get_process_user(self, pid):
        '''get procees user name

        :param pid: process id
        :type  pid: int
        '''
        uid = -1
        cmdline = 'cat /proc/%d/status' % pid
        result = self.run_shell_cmd(cmdline).strip()
        for line in result.split('\n'):
            line = line.strip()
            if line.startswith('Uid:'):
                uid = int(line.split()[1])
                break
        if uid < 0:
            raise RuntimeError('get uid of process %d failed' % pid)
        if uid < 10000:
            return uid
        cmdline = 'cat /proc/%d/cmdline' % pid
        result = self.run_shell_cmd(cmdline).strip().split('\x00')[0]
        if ':' in result:
            result = result.split(':')[0]
        return result

    def kill_process(self, proc_name_or_pid):
        '''杀进程
        '''
        kill_list = []
        package_name = None
        process_list = self.list_process()
        for process in process_list:
            if isinstance(proc_name_or_pid, six.string_types
                          ) and proc_name_or_pid in process['proc_name']:
                if process['proc_name'] == proc_name_or_pid:
                    # 保证主进程首先被杀
                    kill_list.insert(0, process['pid'])
                else:
                    kill_list.append(process['pid'])
            elif process['pid'] == proc_name_or_pid:
                kill_list.append(process['pid'])

        if not kill_list:
            return None  # 没有找到对应的进程
        if package_name == None and not self.is_rooted():
            package_name = self.get_process_user(kill_list[0])
        for i, pid in enumerate(kill_list):
            kill_list[i] = 'kill -9 %d' % pid
        cmd_line = ' && '.join(kill_list)

        if package_name == 2000:
            # shell process
            result = self.run_shell_cmd(cmd_line)
        elif self.is_rooted():
            result = self.run_shell_cmd(cmd_line, True)
        elif isinstance(package_name, six.string_types):
            # package
            result = self.run_as(package_name, cmd_line)
        else:
            raise PermissionError(
                'can\'t kill uid=%s process in non-root device' % package_name)

        if 'Operation not permitted' in result:
            raise PermissionError('run %s failed: %s' % (cmd_line, result))
        return True

    def get_device_imei(self):
        '''获取手机串号
        '''
        result = self.run_shell_cmd('dumpsys iphonesubinfo', self.is_rooted())
        for line in result.split('\n'):
            if line.find('Device ID') >= 0:
                return line.split('=')[1].strip()
        raise RuntimeError('获取imei号失败：%r' % result)

    def get_cpu_total_time(self):
        cpu_time = 0
        result = self.run_shell_cmd('cat /proc/stat')
        result = result.split('\n')[0]
        for item in result.split(' '):
            item = item.strip()
            if not item:
                continue
            if item == 'cpu':
                continue
            cpu_time += int(item)
        return cpu_time

    def get_process_cpu_time(self, pid):
        result = self.run_shell_cmd('cat /proc/%d/stat' % pid)
        result = result.split(' ')
        utime = int(result[13])
        stime = int(result[14])
        cutime = int(result[15])
        cstime = int(result[16])
        return utime + stime + cutime + cstime

    def get_thread_cpu_time(self, pid, tid):
        result = self.run_shell_cmd('cat /proc/%d/task/%d/stat' % (pid, tid))
        result = result.split(' ')
        utime = int(result[13])
        stime = int(result[14])
        cutime = int(result[15])
        cstime = int(result[16])
        return utime + stime + cutime + cstime

    def get_process_cpu(self, proc_name, interval=0.1):
        '''获取进程中每个线程的CPU占用率
        '''
        pid = self.get_pid(proc_name)
        # print (pid)
        if not pid:
            return None
        total_cpu1 = self.get_cpu_total_time()
        process_cpu1 = self.get_process_cpu_time(pid)
        thread_cpu1 = self.get_thread_cpu_time(pid, pid)
        time.sleep(interval)
        total_cpu2 = self.get_cpu_total_time()
        process_cpu2 = self.get_process_cpu_time(pid)
        thread_cpu2 = self.get_thread_cpu_time(pid, pid)
        total_cpu = total_cpu2 - total_cpu1
        process_cpu = process_cpu2 - process_cpu1
        thread_cpu = thread_cpu2 - thread_cpu1
        return process_cpu * 100 // total_cpu, thread_cpu * 100 // total_cpu

    @staticmethod
    def list_device():
        '''获取设备列表
        '''
        return LocalADBBackend.list_device()

    @staticmethod
    def is_local_device(device_id):
        '''是否是本地设备
        '''
        pattern = re.compile(r'([\w|\-|\.]+):(.+)')
        mat = pattern.match(device_id)
        if not mat or (mat.group(2).isdigit() and int(mat.group(2)) > 1024
                       and int(mat.group(2)) < 65536):
            return True
        else:
            return False

    @staticmethod
    def open_device(name_or_backend=None):
        '''打开设备
        '''
        if isinstance(name_or_backend, six.string_types):
            adb_backend = LocalADBBackend.open_device(name_or_backend)
        else:
            adb_backend = name_or_backend

        adb = ADB(adb_backend)

        if adb.is_rooted() and adb.is_selinux_opened():
            if not adb.close_selinux():
                logger.warn('Close selinux failed')
                # raise RuntimeError('关闭selinux失败，确认手机是否完美Root')
        return adb

    @staticmethod
    def connect_device(name):
        '''使用TCP连接设备
        '''
        proc = subprocess.Popen([adb_path, 'connect', name],
                                stdout=subprocess.PIPE)
        result = proc.stdout.read()
        if result.find('unable to connect to') >= 0:
            print(result, file=sys.stderr)
            return False
        return True

    def get_cpu_time(self):
        '''获取手机全局总时间片和空闲时间片
        '''
        import re
        cpu_time = 0
        result = self.run_shell_cmd('cat /proc/stat')
        result = result.split('\n')[0]
        result, num = re.subn(r'\s+', ' ', result)  # 将字符串中多个相连的空白字符合并成一个空白字符
        results = result.split(' ')
        if len(results) < 5:
            logger.warn('无法取得CPU时间片统计，请确保手机正常链接，并已启动！')
            return 0, 0
        idle_time = int(results[4])
        for item in results:
            item = item.strip()
            if not item:
                continue
            if item == 'cpu':
                continue
            cpu_time += int(item)
        return cpu_time, idle_time

    def get_cpu_usage(self, interval=0.5):
        '''获取手机全局CPU使用率
        '''
        total_time1, idle_time1 = self.get_cpu_time()
        time.sleep(interval)
        total_time2, idle_time2 = self.get_cpu_time()
        total_time = total_time2 - total_time1
        idle_time = idle_time2 - idle_time1
        if total_time == 0:
            return -1
        return (total_time - idle_time) * 100 // total_time

    @static_result
    def is_art(self):
        '''是否是art虚拟机
        '''
        ret = self.get_property('persist.sys.dalvik.vm.lib')
        if not ret:
            ret = self.get_property('persist.sys.dalvik.vm.lib.2')
        return 'libart.so' in ret

    def dump_stack(self, pid_or_procname):
        '''获取进程调用堆栈
        '''
        if isinstance(pid_or_procname, six.string_types):
            pid = self.get_pid(pid_or_procname)
        else:
            pid = pid_or_procname
        anr_dir = '/data/anr'
        try:
            self.list_dir(anr_dir)
        except RuntimeError:
            self.mkdir(anr_dir)
        self.chmod(anr_dir, 777)
        cmd = 'kill -3 %d' % pid
        self.run_shell_cmd(cmd, True)
        return self.run_shell_cmd('cat %s/traces.txt' % anr_dir, True)

    def get_state(self):
        '''获取设备状态
        '''
        return self.run_adb_cmd('get-state')

if __name__ == '__main__':
    pass
