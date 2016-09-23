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

# 2013/5/20 apple 创建

import os, sys
import time
import subprocess
import threading
import re
from adbclient import ADBClient
from util import Deprecated, logger, ThreadEx, TimeoutError, InstallPackageFailedError, is_mutibyte_string

cur_path = os.path.dirname(os.path.abspath(__file__))

def get_adb_path():
    for root in os.environ.get('path').split(';'):
        adb_path = os.path.join(root, 'adb.exe')
        if os.path.exists(adb_path):  # 优先使用环境变量中指定的 adb
            return adb_path
    return os.path.join(cur_path, 'tools', 'adb.exe')
adb_path = get_adb_path()
os.environ['QTA_ADB_PATH'] = adb_path

def is_adb_server_opend():
    '''判断ADB Server是否开启
    '''
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', 5037))
        sock.close()
        return False
    except:
        return True

use_protocol = True

try:
    from testbase.testcase import Environ
    env = Environ()
    if env.has_key('USE_PROTOCOL') and env['USE_PROTOCOL'] == '1':
        use_protocol = True
except ImportError:
    use_protocol = True
    
class ADBHost(object):
    '''ADB主机
    '''
    def __init__(self, hostname='127.0.0.1', port=5037):
        self._hostname = hostname
        self._port = port
        
    @property
    def hostname(self):
        return self._hostname
    
    @property
    def port(self):
        return self._port
    
    def is_local_host(self):
        '''是否是本地主机
        '''
        return self.hostname == '127.0.0.1' or self.hostname == 'localhost'
    
    def list_device(self):
        '''
        '''
        if self.is_local_host():
            ADB.start()
        result = ''
        if use_protocol:
            result = ADBClient.get_client(self.hostname, self.port).call('devices', retry_count=3)[0]
        else:
            args = [adb_path, 'devices']
            if not self.is_local_host():
                args.insert(1, '-H')
                args.insert(2, self.hostname)
                if self.port != 5037:
                    args.insert(3, '-P')
                    args.insert(4, '%d' % self.port)
            proc = subprocess.Popen(args, stdout=subprocess.PIPE)  # , stderr=subprocess.PIPE
            result = proc.stdout.read().replace('\r\n', '\n')

        result = result.split('\n')
        device_list = []
        for device in result:
            if len(device) <= 1 or not '\t' in device: continue
            device_list.append((device.split('\t')[0], device.split('\t')[1]))
        return device_list
    
class ADB(object):
    '''封装ADB功能
    '''
    armeabi = 'armeabi'
    x86 = 'x86'
    
    server_port = 5037  # adb server端口
    connect_timeout = 300  # 连接设备的超时时间
    instance_dict = {}

    def __init__(self, device_name='', check_device=True, wait_time=0):
        if isinstance(device_name, unicode):
            device_name = device_name.encode('utf8')
        self._device_name = device_name
        self._rooted = None
        if check_device:
            found_device = False
            time0 = time.time()
            while wait_time == 0 or time.time() - time0 <= wait_time:
                devices = [device for device, state in ADBHost().list_device() if state == 'device']
                if len(devices) == 0 or (device_name != '' and not device_name in devices):
                    if wait_time == 0: break
                    time.sleep(0.5)
                    continue
                elif device_name == '' and len(devices) == 1:
                    self._device_name = devices[0]
                    found_device = True
                    break
                else:
                    found_device = True
                    break
            if not found_device: raise RuntimeError('%sADB未找到设备 %s' % ('%d秒内' % wait_time if wait_time > 0 else '', device_name))
        self._need_quote = None  # 执行shell命令时有些手机需要引号，有些不需要
        # self._check_grep()
        self._log_filter_thread_list = []  # 不打印log的线程id列表
        self._shell_prefix = None  # 有些设备上会有固定输出
    
    def _gen_adb_args(self, cmd):
        '''生成adb命令行参数
        '''
        args = [adb_path, cmd]
        if self._device_name:
            args = [adb_path, '-s', self._device_name, cmd]
        return args
    
    def run_adb_cmd(self, cmd, *argv, **kwds):
        '''执行adb命令
        '''
        retry_count = 3  # 默认最多重试3次
        if not kwds.has_key('retry_count'): kwds['retry_count'] = retry_count
        timeout = 20
        if not kwds.has_key('timeout'): kwds['timeout'] = timeout
        if use_protocol or (kwds.has_key('sync') and kwds['sync'] == False):
            return self.run_adb_cmd_by_protocol(cmd, *argv, **kwds)
        else:
            return self.run_adb_cmd_by_exe(cmd, *argv, **kwds)
    
    def run_adb_cmd_by_exe(self, cmd, *argv, **kwds):
        '''使用adb.exe执行adb命令
        '''
        import time
        import util
        args = self._gen_adb_args(cmd)
        
        for i in range(len(argv)):
            arg = argv[i]
            if is_mutibyte_string(arg): 
                # adb.exe不支持中文
                return self.run_adb_cmd_by_protocol(cmd, *argv, **kwds)
            
            if not isinstance(argv[i], unicode):
                arg = arg.decode('utf8')
            encoding = util.get_default_encoding()
            arg = arg.encode(encoding)
            args.append(arg)
        # args.extend(argv)
        # cmdline = ' '.join(args)
        if not threading.current_thread().ident in self._log_filter_thread_list: logger.info('%s' % (args))
        
        retry_count = kwds['retry_count']
        timeout = kwds['timeout']
        
        close_fds = False
        stdin = subprocess.PIPE
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
        if kwds.has_key('close_fds'):
            close_fds = kwds['close_fds']
            if close_fds:
                stdin = stdout = stderr = None
                args.append('1>/dev/null')  # 禁止输出
                args.append('2>/dev/null')  # 禁止错误输出
        for i in range(retry_count):
            time0 = time.time()
            proc = subprocess.Popen(args, stdin=stdin, stdout=stdout, stderr=stderr, close_fds=close_fds)  # shell=True, 
            if kwds.has_key('sync') and kwds['sync'] == False:
                # 不等待返回结果
                return proc

            result = [None, None]
            def _run_cmd_thread():
                result[0], result[1] = proc.communicate()

            t = ThreadEx(target=_run_cmd_thread)
            t.setDaemon(True)
            t.start()
            t.join(timeout)

            if t.is_alive():
                # 卡住了
                if not threading.current_thread().ident in self._log_filter_thread_list: logger.warn(u'执行ADB命令：%s 超时' % args)
                try:
                    proc.terminate()
                except WindowsError, e:
                    logger.warn('执行proc.terminate()失败：%s' % e)
                    pass
                if i >= retry_count - 1:
                    raise TimeoutError('执行ADB命令：%s 超时失败' % args)
                time.sleep(1)
            else:
                break

        if not threading.current_thread().ident in self._log_filter_thread_list: logger.info('执行ADB命令耗时：%s，命令行返回值：%s' % (time.time() - time0, proc.returncode))
        out, err = result
        if err:
            encoding = util.get_default_encoding()
            err = err.decode(encoding).strip()
            # print >> sys.stderr, err
            logger.error('%r' % err)
            if err == 'error: closed':
                raise RuntimeError(err)
#                self.close()
#                self.start()
#                return self.run_adb_cmd(cmd, *argv, **kwds)
            # raise RuntimeError('执行命令：%s 失败：\n%s' % (args, err.decode(encoding)))
            elif err.startswith('error: device not found') or err.startswith('error: device offline'):
                self.run_adb_cmd('wait-for-device', retry_count=1, timeout=self.connect_timeout)  # 等待设备连接正常
                return self.run_adb_cmd(cmd, *argv, **kwds)
            elif 'cannot connect to daemon' in err:
                import clientsocket
                if not hasattr(self, '_host_name'): raise RuntimeError(err)
                time0 = time.time()
                while time.time() - time0 < self.connect_timeout:
                    if clientsocket.is_tcp_server_opened(self._host_name, self.server_port):
                        return self.run_adb_cmd(cmd, *argv, **kwds)
                    time.sleep(10)
                else:
                    logger.error('连接ADB SERVER %s:%s超时失败' % (self._host_name, self.server_port))
                    raise TimeoutError('执行ADB命令：%s 超时失败' % args)
                
            elif 'protocol fault' in err or 'protocol failure' in err:
                # 执行shell命令时可能会返回
                time.sleep(1)  # 等待1秒后重试，防止过多错误
                return self.run_adb_cmd(cmd, *argv, **kwds)
        # print out
        if out == '': out = err
        return out.strip()
    
    def run_adb_cmd_by_protocol(self, cmd, *args, **kwds):
        '''使用协议执行adb命令
        '''
        hostname = '127.0.0.1'
        if hasattr(self, '_host_name'):
            hostname = self._host_name
        client = ADBClient.get_client(hostname, 5037)
        sync = kwds['sync'] if kwds.has_key('sync') else True
        retry_count = kwds['retry_count']
        timeout = kwds['timeout']
        
        if not threading.current_thread().ident in self._log_filter_thread_list: logger.info('adb %s%s %s %s' % (self._host_name + ':' if hasattr(self, '_host_name') else '', self._device_name, cmd, ' '.join(args)))
        time0 = time.time()
        result = client.call(cmd, self._device_name, *args, sync=sync, retry_count=retry_count, timeout=timeout)
        if not isinstance(result, tuple): return result
        if not threading.current_thread().ident in self._log_filter_thread_list: logger.info('执行ADB命令耗时：%s' % (time.time() - time0))
        out, err = result
        if err:
            if 'error: device not found' in err:
                self.run_adb_cmd('wait-for-device', retry_count=1, timeout=self.connect_timeout)  # 等待设备连接正常
                return self.run_adb_cmd(cmd, *args, **kwds)
            return err
        if isinstance(out, basestring): out = out.strip()
        return out
    
    def run_shell_cmd(self, cmd_line, root=False, **kwds):
        sync = kwds['sync'] if kwds.has_key('sync') else True
        # if not cmd_line.startswith('echo'): self._check_shell_prefix()

        def _handle_result(result):
            if not isinstance(result, (str, unicode)): return result
            if self._shell_prefix != None and self._shell_prefix > 0:
                result = '\n'.join(result.split('\n')[self._shell_prefix:])
            if result.startswith('WARNING: linker:'):
                # 虚拟机上可能会有这种错误：WARNING: linker: libdvm.so has text relocations. This is wasting memory and is a security risk. Please fix.
                lines = result.split('\n')
                idx = 1
                while idx < len(lines):
                    if not lines[idx].startswith('WARNING: linker:'): break
                    idx += 1
                return '\n'.join(lines[idx:]).strip()
            elif root and result.startswith('Test prop'):
                lines = result.split('\n')
                return '\n'.join(lines[2:]).strip()
            else:
                if root and 'connect ui: Timer expired' in result:
                    # su程序出现问题 TODO: 是否重试能够解决问题？
                    return self.run_shell_cmd(cmd_line, root, **kwds)
                return result

        if root:
            if self._rooted == None:
                self._rooted = self.is_rooted()
            if self._rooted:
                return self.run_shell_cmd(cmd_line, **kwds)
            if self._need_quote == None:
                self._check_need_quote()
            if self._need_quote:
                cmd_line = 'su -c \'%s\'' % cmd_line
            else:
                cmd_line = 'su -c %s' % cmd_line
        return _handle_result(self.run_adb_cmd('shell', '%s' % cmd_line, **kwds))

    def reboot(self, _timeout=180):
        '''重启手机'''
        try:
            self.run_adb_cmd('reboot', retry_count=1, timeout=30)
        except TimeoutError:
            # 使用强杀init进程方式重启手机
            self.kill_process(1)
            time.sleep(10)  # 等待手机重启
        if _timeout > 0: self.wait_for_boot_complete(_timeout)

    def wait_for_boot_complete(self, _timeout=180):
        '''等待手机启动完成'''
        # 手机重启完后 adbd Insecure 启动时会导致adb断开重连，qt4a框架己经实现了adb root权限功能，测试手机请不要安装 adbd Insecure
        import time
        print '等待手机启动完成...'
        self.run_adb_cmd('wait-for-device', timeout=_timeout)
        boot_complete = False
        attempts = 0
        wait_period = 5
        while not boot_complete and (attempts * wait_period) < _timeout:
            output = self.run_shell_cmd("getprop sys.boot_completed", retry_count=1)
            output = output.strip()
            if output == "1":
                boot_complete = True
            else:
                time.sleep(wait_period)
                attempts += 1
        if not boot_complete:
            raise RuntimeError("dev.bootcomplete 标志在  %s 秒后仍未设置，手机重启失败" % _timeout)

    def start_logcat(self, process_list=[], params=''):
        '''运行logcat进程
        :param process_list: 要捕获日志的进程名或进程ID列表，为空则捕获所有进程
        :type process_list:  list
        '''
        self.run_shell_cmd('logcat -c ' + params)  # 清除缓冲区
        if not hasattr(self, '_log_list'):
            self._log_list = []
        self._logcat_running = True
        self._log_pipe = self.run_shell_cmd('logcat -v threadtime ' + params, sync=False)

        # self._logcat_thread_func(process_list)

        self._logcat_thread = ThreadEx(target=self._logcat_thread_func, args=[process_list, params])
        self._logcat_thread.setDaemon(True)
        self._logcat_thread.start()
        self._log_filter_thread_list.append(self._logcat_thread.ident)

    def stop_logcat(self):
        '''停止logcat
        '''
        self._logcat_running = False
        if hasattr(self, '_log_pipe'):
            if self._log_pipe.poll() == None:  # 判断logcat进程是否存在
                try:
                    self._log_pipe.terminate()
                except WindowsError, e:
                    logger.warn('terminate logcat process failed: %s' % e)
                    
        if hasattr(self, '_logcat_thread'):
            if self._logcat_thread.ident in self._log_filter_thread_list:
                self._log_filter_thread_list.remove(self._logcat_thread.ident)
            else:
                logger.warn('%s not in %s' % (self._logcat_thread.ident, self._log_filter_thread_list))

    def get_log(self, clear=True):
        '''获取已经保存的log
        '''
        result = self._log_list
        if clear: self._log_list = []
        return result

    def save_log(self, save_path):
        '''保存log
        '''
        if not hasattr(self, '_log_list'): return
        log_list = self.get_log()
        for i in range(len(log_list)):
            log = log_list[i]
            if not isinstance(log, unicode):
                # 先编码为unicode
                for code in ['utf8', 'gbk']:
                    try:
                        log = log.decode(code)
                        break
                    except UnicodeDecodeError, e:
                        logger.warn('decode with %s error: %s' % (code, e))
                else:
                    log = repr(log)
            log_list[i] = log.encode('utf8') if isinstance(log, unicode) else log
        f = open(save_path, 'w')
        f.write('\n'.join(log_list))
        f.close()

    def insert_logcat(self, process_name, year, month_day, timestamp, level, tag, tid, content):
        self._log_list.append('[%s] [%s-%s %s] %s/%s(%s): %s' % (process_name,
                                                                 year, month_day, timestamp,
                                                                 level,
                                                                 tag,
                                                                 tid,
                                                                 content))

    def _logcat_thread_func(self, process_list, params=''):
        '''获取logcat线程
        '''
        import re
        # pattern = re.compile(r'([A-Z])/([\w|.]+)\s*\(\s*(\d+)\):.+') #标准格式
        pattern = re.compile(r'([\d|-]+)\s+([\d|:|\.]+)\s+(\d+)\s+(\d+)\s+(\w)\s+(\S+)\s*:\s+(.+)')  # [^:]
        # Date Time PID TID Level Tag Content 
        pid_dict = {}
        filter_pid_list = []  # 没有找到匹配进程的列表
        zygote_pid = 0  # zygote进程ID

        while self._logcat_running:
            log = self._log_pipe.stdout.readline().strip()
            if not log:
                if self._log_pipe.poll() != None:
                    logger.debug('logcat进程：%s 已退出' % self._log_pipe.pid)
                    # 进程已退出
                    # TODO: 解决logcat重复问题
                    if not self._logcat_running:
                        logger.info('logcat线程停止运行')
                        return
                    self._log_pipe = self.run_shell_cmd('logcat -v threadtime ' + params, sync=False)
                else:
                    continue

            ret = pattern.match(log)
            if not ret: continue
            tag = ret.group(6).strip()
            if tag in ['inject', 'dexloader', 'ActivityInspect']:  # , 'MethodHook'
                logger.info(log)  # 测试桩日志加入到qt4a日志中
                continue  # TODO: 测试桩去掉log

            if tag in ['Web Console']:
                if ret.group(7).startswith('[ClickListener]'):
                    logger.info(log)  # WebView的控件点击信息
                    continue
                
            pid = int(ret.group(3))
            if pid in filter_pid_list: continue

            init_process_list = ['<pre-initialized>', 'zygote']

            if not pid in pid_dict.keys():
                for item in self.list_process():
                    if zygote_pid == 0 and item['proc_name'] == 'zygote' and item['ppid'] == 1:
                        # zygote父进程ID为1
                        zygote_pid = item['pid']

                    for init_process in init_process_list:
                        if pid_dict.has_key(item['pid']) and pid_dict[item['pid']].startswith(init_process) and not item['proc_name'].startswith(init_process):

                            for i in range(len(self._log_list) - 1, -1, -1):
                                # 修复之前记录的“<pre-initialized>”进程
                                pre_process_name = '[%s(%d)]' % (init_process, item['pid'])
                                if not pre_process_name in self._log_list[i]: continue
                                if process_list:
                                    del_flag = True
                                    for process in process_list:
                                        if pid == process or item['proc_name'].startswith(process):
                                            # 替换为真实进程名
                                            self._log_list[i] = self._log_list[i].replace(pre_process_name, '[%s]' % item['proc_name'])
                                            del_flag = False
                                            break
                                    if del_flag:
                                        # 不在需要记录的进程列表中
                                        del self._log_list[i]
                                else:
                                    # 直接替换
                                    self._log_list[i] = self._log_list[i].replace(pre_process_name, '[%s]' % item['proc_name'])
                    pid_dict[item['pid']] = item['proc_name']
                    if item['proc_name'] in init_process_list and item['pid'] != zygote_pid:
                        pid_dict[item['pid']] += '(%d)' % item['pid']
                if not pid in pid_dict.keys():
                    filter_pid_list.append(pid)
                    continue

            found = False
            if not process_list:
                found = True  # 不指定进程列表则捕获所有进程
            else:
                for process in process_list:
                    if pid == process or (pid_dict.has_key(pid) and (pid_dict[pid].startswith(process) or pid_dict[pid].startswith('<pre-initialized>') \
                                                                     or (pid_dict[pid].startswith('zygote') and pid != zygote_pid))):  # 进程初始化中
                        found = True
                        break

            if found:
                import datetime
                if not hasattr(self, '_year'):
                    self._year = datetime.date.today().year
                self.insert_logcat(pid_dict.get(pid), self._year, ret.group(1), ret.group(2), ret.group(5), ret.group(6), ret.group(4), ret.group(7))

    def is_rooted(self):
        result = self.run_shell_cmd('id')
        logger.debug('is_rooted: %s' % result)
        return result.find('uid=0(root)') >= 0

    def _check_need_quote(self, timeout=20):
        cmd = "su -c 'ls -l /data/data'"  # 默认方式为加引号，避免有些手机上对于存在空格的命令容易出错
        # 联想S899T上发现不加引号返回结果为空
        result = self.run_shell_cmd(cmd, timeout=timeout)
        if result.find('com.android.phone') >= 0:
            self._need_quote = True
        else:
            self._need_quote = False

    def _check_shell_prefix(self):
        '''检查设备运行命令时是够有固定输出
        '''
        pass
#        if self._shell_prefix == None:
#            self._shell_prefix = len(self.run_shell_cmd('echo padding').split('\n')) - 1  #一般前缀的行数是固定的

    def _set_system_writable(self):
        '''修改system分区可写
        '''
        result = self.run_shell_cmd('mount', True)
        for line in result.split('\r\n'):
            if line.find('/system') >= 0:
                block = line.split(' ')[0]
                print block
                self.run_shell_cmd('mount -o remount %s /system' % block, True)
                return True
        return False

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
            ret = self.run_adb_cmd('forward', 'tcp:%d' % (port1), '%s:%s' % (type, port2))
            if not 'cannot bind socket' in ret and not 'cannot bind to socket' in ret: return port1
            port1 += 1

    def _push_file(self, src_path, dst_path, uid=None):
        '''以指定身份拷贝文件到手机中
        '''
        result = self.run_adb_cmd('push', src_path, dst_path, timeout=None)
        if 'No space left on device' in result or 'No such file or directory' in result:
            # 如果源文件不存在不会执行到这里
            raise RuntimeError('设备存储空间不足')
        if uid and uid != 'shell' and uid != 'root':
            self.run_shell_cmd('mv %s %s0' % (dst_path, dst_path), True)
            dst_dir = dst_path[:dst_path.rfind('/')]
            self.run_shell_cmd('rm %s' % dst_path, True)
            self.run_shell_cmd('rmdir %s' % dst_dir, True)
            self.run_shell_cmd('su %s mkdir %s' % (uid, dst_dir))
            self.run_shell_cmd('chmod 777 %s' % dst_dir, True)
            self.run_shell_cmd('su %s cp %s0 %s' % (uid, dst_path, dst_path))
            self.run_shell_cmd('rm %s0' % dst_path)  # 只能复制再删除
        return result

    def push_file(self, src_path, dst_path, uid=None):
        '''以指定身份拷贝文件到手机中
        '''
        for _ in range(3):
            file_size = os.path.getsize(src_path)  # 防止取到的文件大小不正确
            result = self._push_file(src_path, dst_path, uid)
            if file_size == 0:
                logger.warn('文件大小为0')
                return result
            if ('%d' % file_size) in result:
                try:
                    _, file_list = self.list_dir(dst_path)
                    if len(file_list) == 0:
                        logger.warn('push file failed: file not exist')
                    elif file_list[0]['size'] != file_size:
                        logger.warn('push file failed: file size error, expect %d, actual is %d' % (file_size, file_list[0]['size']))
                    else:
                        return result
                except RuntimeError, e:
                    err_msg = e.args[0]
                    if not isinstance(err_msg, unicode):
                        err_msg = err_msg.decode('utf8')
                    logger.warn(err_msg)
            else:
                logger.warn('push file failed: %s' % result)
        raise RuntimeError('拷贝文件到手机：%r 失败：%s' % (self._device_name, result))

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
        import zipfile, StringIO
        from _axmlparser import AXMLPrinter
        package_name = ''
        for _ in range(3):
            try:
                f = open(apk_path, 'rb')
                apk_data = f.read()
                f.close()
                break
            except IOError:
                logger.exception('read package error')
                time.sleep(10)
        else:
            raise InstallPackageFailedError('读取安装包失败')
        zip = zipfile.ZipFile(StringIO.StringIO(apk_data), mode='r')
        for i in zip.namelist():
            if i == "AndroidManifest.xml":
                printer = AXMLPrinter(zip.read(i))
                package_name = printer.get_xml_obj().getElementsByTagName('manifest')[0].getAttribute('package')
                break
        if not package_name: raise RuntimeError('获取安装包中的包名信息失败')
        return package_name
        
    def _install_apk(self, apk_path, package_name, reinstall=False):
        '''
        '''
#        if not reinstall:
#            return self.run_adb_cmd('install', apk_path, timeout=None)
#        else:
#            return self.run_adb_cmd('install', '-r', apk_path, timeout=None)

        timeout = 3 * 60  # TODO: 确认3分钟是否足够
        cmdline = 'pm install %s %s' % ('-r' if reinstall else '', apk_path)
        ret = ''
        for i in range(3):
            # 处理一些必然会失败的情况，如方法数超标之类的问题
            try:
                ret = self.run_shell_cmd(cmdline, True, retry_count=1, timeout=timeout)  # 使用root权限安装，可以在小米2S上不弹出确认对话框
                logger.debug(ret)
                if 'Success' in ret:
                    return True, ret
                elif i > 1 and 'INSTALL_FAILED_ALREADY_EXISTS' in ret:
                    # 出现至少一次超时，认为安装完成
                    return True, 'Success'
                elif 'INSTALL_PARSE_FAILED_NO_CERTIFICATES' in ret:
                    return False, ret
                elif 'INSTALL_PARSE_FAILED_INCONSISTENT_CERTIFICATES' in ret:
                    # 必须卸载安装
                    return self._install_apk(apk_path, package_name, False)
                elif 'INSTALL_FAILED_INSUFFICIENT_STORAGE' in ret:
                    # 有可能是存在/data/app-lib/packagename-1目录导致的
                    dir_path = '/data/app-lib/%s-1' % package_name
                    if 'No such file or directory' in self.run_shell_cmd('ls -l %s' % dir_path, True):
                        return False, ret
                    else:
                        self.delete_folder(dir_path)
                        continue    
                elif 'INSTALL_FAILED_UID_CHANGED' in ret:
                    # /data/data目录下存在文件夹没有删除
                    dir_path = '/data/data/%s' % package_name
                    for _ in range(3):
                        # 防止删除没有成功
                        self.delete_folder(dir_path)
                        if 'No such file or directory' in self.run_shell_cmd('ls -l %s' % dir_path, True): break
                    continue
                else:
                    return False, ret
            except TimeoutError, e:
                logger.warn('install app timeout: %r' % e)
        else:
            logger.warn('install app failed')
            ret = self.run_shell_cmd(cmdline, timeout=timeout)  # 改用非root权限安装
            logger.debug(ret)
            if 'INSTALL_FAILED_ALREADY_EXISTS' in ret: return True, 'Success'
        
        return False, ret

    def install_apk(self, apk_path, reinstall=False):
        '''安装应用
        '''
        if not isinstance(self, RemoteADB) and not os.path.exists(apk_path):
            if isinstance(apk_path, unicode):
                apk_path = apk_path.encode('utf8')
            raise RuntimeError('APK: %s 不存在' % apk_path)
        package_name = self._get_package_name(apk_path)

        tmp_path = '/data/local/tmp/' + os.path.split(apk_path)[-1]
        self.push_file(apk_path, tmp_path)
        
        if not reinstall:
            self.uninstall_app(package_name)  # 先卸载，再安装
            result = self._install_apk(tmp_path, package_name, reinstall)
        else:
            result = self._install_apk(tmp_path, package_name, reinstall)
        # logger.debug(result)

        if result[0] == False: 
            if not 'Failure' in result[1]: 
                # 一般这种情况都是由于adb server意外退出导致，此时安装过程还会继续
                logger.warn('install app: %r' % result[1])
                timeout = 30
                time0 = time.time()
                while time.time() - time0 < timeout:
                    # 等待应用安装完成
                    if self.get_package_path(package_name): break
                    time.sleep(1)
                else:
                    result = self._install_apk(tmp_path, package_name, reinstall)
            else:
                err_msg = result[1]
                if isinstance(err_msg, unicode): err_msg = err_msg.encode('utf8')
                if isinstance(package_name, unicode): package_name = package_name.encode('utf8')
                raise InstallPackageFailedError('安装应用%s失败：%s' % (package_name, err_msg))
        try:
            self.delete_file('/data/local/tmp/*.apk')
        except TimeoutError:
            pass
        
    def uninstall_app(self, pkg_name):
        '''卸载应用
        '''
        result = ''
        if not self.get_package_path(pkg_name): return True
        for i in range(5):
            try:
                result = self.run_adb_cmd('uninstall', pkg_name, retry_count=1, timeout=30)
                break
            except RuntimeError, e:
                logger.exception('uninstall %s failed' % pkg_name)
                if i >= 4: raise e
                time.sleep(10)
        logger.debug('uninstall result: %r' % result)
        return result.find('Success') >= 0
    
    @Deprecated('uninstall_app')
    def uninstall_apk(self, pkg_name):
        '''卸载应用
        '''
        return self.uninstall_app(pkg_name)
    
    def get_package_path(self, pkg_name):
        '''获取应用安装包路径
        '''
        for _ in range(3):
            # 为避免某些情况下获取不到应用安装包路径，重试多次
            result = self.run_shell_cmd('pm path %s' % pkg_name)
            logger.debug('get_package_path: %r' % result)
            pos = result.find('package:')
            if pos >= 0: return result[pos + 8:]
            time.sleep(1)
        return ''

    def start_activity(self, activity_name, action='', type='', data_uri='', extra={}, wait=True):
        '''打开一个Activity
        '''
        if action != '':  # 指定Action
            action = '-a %s ' % action
        if type != '':
            type = '-t %s ' % type
        if data_uri != '':
            data_uri = '-d %s ' % data_uri
        extra_str = ''
        for key in extra.keys():  # 指定额外参数
            p_type = ''
            if extra[key] in ['true', 'false']:
                p_type = 'z'  # EXTRA_BOOLEAN_VALUE
            elif isinstance(extra[key], int):
                p_type = 'i'  # EXTRA_INT_VALUE
            elif isinstance(extra[key], long):
                p_type = 'l'  # EXTRA_LONG_VALUE
            elif isinstance(extra[key], float):
                p_type = 'f'  # EXTRA_FLOAT_VALUE
            elif extra[key].startswith('file://'):  # EXTRA_URI_VALUE
                p_type = 'u'
            if not p_type and '&' in extra[key]:
                extra[key] = extra[key].replace('&', r'\&')
            param = '-e%s %s %s ' % (p_type, key, extra[key])
            if p_type: param = '-' + param
            extra_str += param
        if len(extra_str) > 0: extra_str = extra_str[:-1]
        W = ''
        if wait: W = '-W'  # 等待启动完成才返回
        # 如果/sbin/sh指向busybox，就会返回“/sbin/sh: am: not found”错误
        # 返回am找不到是因为am缺少“#!/system/bin/sh”
        command = 'am start %s -n %s %s%s%s%s' % (W, activity_name, action, type, data_uri, extra_str)
        if command[-1] == ' ': command = command[:-1]
        result = self.run_shell_cmd(command, timeout=15, retry_count=3)
        if 'Permission Denial' in result or not 'Activity' in result or not 'Complete' in result:
            # 使用root权限运行
            result = self.run_shell_cmd(command, True, timeout=15, retry_count=3)
            # raise RuntimeError('打开Activity失败：\n%s' % result)
        ret_dict = {}

        for line in result.split('\r\n'):
            if ': ' in line:
                key, value = line.split(': ')
                ret_dict[key] = value
        if ret_dict.has_key('Error'):
            raise RuntimeError(ret_dict['Error'])
        return ret_dict

    def get_cpu_abi(self):
        '''获取系统的CPU架构信息
        '''
        ret = self.run_shell_cmd('getprop ro.product.cpu.abi')
        if not ret: ret = 'armeabi'  # 有些手机可能没有这个系统属性
        return ret

    def get_device_module(self):
        '''获取设备型号
        '''
        module = self.run_shell_cmd('getprop ro.product.model')
        brand = self.run_shell_cmd('getprop ro.product.brand')
        if module.find(brand) >= 0:
            return module
        return '%s %s' % (brand, module)

    def get_system_version(self):
        '''获取系统版本
        '''
        return self.run_shell_cmd('getprop ro.build.version.release')

    def get_sdk_version(self):
        '''获取SDK版本
        '''
        return int(self.run_shell_cmd('getprop ro.build.version.sdk'))
            
    def get_uid(self, app_name):
        '''获取APP的uid
        '''
        result = self.run_shell_cmd('ls -l /data/data', True)
        result = result.replace('\r\r\n', '\n')
        for line in result.split('\n'):
            items = line.split(' ')
            for item in items:
                if not item: continue
                if item == app_name: return items[1]
        return None

    def is_selinux_opened(self):
        '''selinux是否是enforcing状态
        '''
        if self.get_sdk_version() < 18: return False
        return 'Enforcing' in self.run_shell_cmd('getenforce', True)
    
    def close_selinux(self):
        '''关闭selinux
        '''
        result = self.run_shell_cmd('setenforce 0', True)
        if 'Permission denied' in result: return False
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

        ret = self.run_shell_cmd('chmod %s %s' % (attr, file_path), True)
        dir_list, file_list = self.list_dir(file_path)

        if len(dir_list) == 0 and len(file_list) == 1 and file_path.endswith('/' + file_list[0]['name']):
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

    def mkdir(self, dir_path, mod=None):
        '''创建目录
        '''
        cmd = 'mkdir %s' % (dir_path)
        ret = self.run_shell_cmd(cmd, True)
#        if not 'File exists' in ret:
#            #加了-p参数貌似不会返回这个提示信息
        try:
            self.list_dir(dir_path)
        except RuntimeError, e:
            logger.warn('mkdir %s failed: %s(%s)' % (dir_path, ret, e))
            return self.mkdir(dir_path, mod)
        # 修改权限
        if mod != None:
            self.chmod(dir_path, mod)

    def list_dir(self, dir_path):
        '''列取目录
        '''
        if ' ' in dir_path: dir_path = '"%s"' % dir_path
        result = self.run_shell_cmd('ls -l %s' % dir_path, True)
        result = result.replace('\r\r\n', '\n')

        if 'No such file or directory' in result:
            raise RuntimeError(u'文件(夹) %s 不存在' % dir_path)
        if 'Not a directory' in result:
            raise RuntimeError(u'%s %s' % (dir_path, result))
        
        dir_list = []
        file_list = []

        def _handle_name(name):
            return name.split('/')[-1]
        
        is_busybox = None
        # busybox格式 -rwxrwxrwx    1 shell    shell        13652 Jun  3 10:56 /data/local/tmp/qt4a/inject
        
        for line in result.split('\n'):
            items = line.split()
            if len(items) < 6: continue  # (6, 7, 9)
            if line[0] != '-' and line[0] != 'd': continue
            
            is_dir = items[0][0] == 'd'  # 是否是目录
            if is_busybox == None:
                item = items[4]  # 日期字段
                if is_dir: item = items[3]  # 目录没有size字段
                pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
                if pattern.match(item):
                    is_busybox = False
                else:
                    is_busybox = True
            
            if not is_busybox:
                # 防止文件名称中有空格
                if not is_dir and len(items) > 7:
                    items[6] = line[line.find(items[6]):].strip()
                elif is_dir and len(items) > 6:
                    items[5] = line[line.find(items[5]):].strip()
            
            attrs = items[0]
            if attrs[0] == 'd':
                if is_busybox: name = _handle_name(items[8])
                else: name = items[5]
                dir_list.append({'name': name, 'attr': attrs[1:]})
            elif attrs[0] == '-':  # 不支持其它类型
                if is_busybox:
                    name = _handle_name(items[8])
                    size = int(items[4])
                    last_modify_time = items[7]
                else:
                    name = items[6]
                    size = int(items[3])
                    last_modify_time = time.strptime('%s %s:00' % (items[4], items[5]), "%Y-%m-%d %X")
                file_list.append({'name': name, 'attr': attrs[1:], 'size': size, 'last_modify_time': last_modify_time})
        return dir_list, file_list

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
            self.run_shell_cmd('cp %s %s' % (src_path, dst_path), True)
        else:
            self.run_shell_cmd('cat %s > %s' % (src_path, dst_path), True, timeout=30)  # 部分手机上发现此方法耗时较多

    def delete_file(self, file_path):
        '''删除手机上文件
        '''
        if '*' in file_path:
            # 使用通配符时不能使用引号
            self.run_shell_cmd('rm %s' % file_path, True)
        else:
            file_path = file_path.replace('"', r'\"')
            self.run_shell_cmd('rm "%s"' % file_path, True)
    
    def delete_folder(self, folder_path):
        '''删除手机上的目录
        '''
        folder_path = folder_path.replace('"', r'\"')
        self.run_shell_cmd('rm -R "%s"' % folder_path, True)
        
    def get_process_uid(self, pid):
        '''获取进程uid'''
        if not pid:
            return None
        if len(self._device_name) > 0:
            res = os.popen("adb -s %s shell cat /proc/%s/status" % (self._device_name, pid)).readlines()
        else:
            res = os.popen("adb shell cat /proc/%s/status" % pid).readlines()
        if  (not res) or len(res[0]) == 0:
            return None
        for res_item in res:
            if len(res_item.split()) == 0:
                continue
            if res_item.split()[0] == "Uid:":
                return res_item.split()[1]
        return None

    def _list_process(self):
        '''获取进程列表
        '''
        import re
        result = self.run_shell_cmd('ps')  # 不能使用grep
        result = result.replace('\r', '')
        lines = result.split('\n')
        busybox = False
        if lines[0].startswith('PID'): busybox = True

        result_list = []
        for i in range(1, len(lines)):
            items = lines[i].split()
            if not busybox:
                if len(items) < 9:
                    raise RuntimeError("ps命令返回格式错误：\n%s" % result)
                result_list.append({'pid': int(items[1]), 'ppid': int(items[2]), 'proc_name': items[8]})
            else:
                idx = 4
                cmd = items[idx]
                if len(cmd) == 1:
                    # 有时候发现此处会有“N”
                    idx += 1
                    cmd = items[idx]
                idx += 1
                if cmd[0] == '{' and cmd[-1] == '}': cmd = items[idx]
                ppid = 0
                if items[1].isdigit(): ppid = int(items[1])  # 有些版本中没有ppid
                result_list.append({'pid': int(items[0]), 'ppid': ppid, 'proc_name': cmd})
        return result_list
    
    def list_process(self):
        '''获取进程列表
        '''
        for _ in range(3):
            try:
                return self._list_process()
            except RuntimeError, e:
                logger.warn('list_process error: %s' % e)
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
            if not line: continue
            if not ':' in line:
                logger.warn('get_process_status line error: %r' % line)
                continue
            key, value = line.split(':')
            result[key] = value.strip()
        return result
    
    def kill_process(self, proc_name_or_pid):
        '''杀死进程
        '''
        kill_list = []
        cmd = ''
        
        if isinstance(proc_name_or_pid, (str, unicode)):
            process_list = self.list_process()
            for process in process_list:
                if process['proc_name'].find(proc_name_or_pid) >= 0:
                    if process['proc_name'] == proc_name_or_pid:
                        # 保证主进程首先被杀
                        kill_list.insert(0, process['pid'])
                    else:
                        kill_list.append(process['pid'])
        else:
            kill_list.append(proc_name_or_pid)
            
        for pid in kill_list:
            cmd += 'kill -9 %d && ' % pid
        if cmd:
            cmd = cmd[:-4]
            self.run_shell_cmd(cmd, True)
            return True
        else:
            return False

#     def get_process_meminfo(self, process_name):
#         '''获取进程内存信息
#         '''
#         pid = self.get_pid(process_name)
#         if pid == 0:
#             raise RuntimeError('进程：%s 不存在' % process_name)
#         self.run_shell_cmd('kill -10 %d' % pid, True)  # 产生GC
#         result = self.run_shell_cmd('dumpsys meminfo %s' % process_name)
#         for line in result.split('\r\n'):
#             # print line
#             if line.find('Dalvik') >= 0:
#                 return int(line[53:59])
#         # print result

    def get_device_imei(self):
        '''获取手机串号
        '''
        result = self.run_shell_cmd('dumpsys iphonesubinfo', True)
        for line in result.split('\n'):
            if line.find('Device ID') >= 0:
                return line.split('=')[1].strip()
        raise RuntimeError('获取imei号失败：%r' % result)

    def get_cpu_total_time(self):
        cpu_time = 0
        result = self.run_shell_cmd('cat /proc/stat')
        result = result.split('\r\n')[0]
        for item in result.split(' '):
            item = item.strip()
            if not item: continue
            if item == 'cpu': continue
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
        import time
        pid = self.get_pid(proc_name)
        # print pid'
        if not pid: return None
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
        return process_cpu * 100 / total_cpu, thread_cpu * 100 / total_cpu

    @staticmethod
    def list_device():
        '''获取设备列表
        '''
        ret = ADB.start()
        proc = subprocess.Popen([adb_path, 'devices'], stdout=subprocess.PIPE)  # , stderr=subprocess.PIPE
        # for line in iter(proc.stdout.readline, ""): print line
        result = proc.stdout.read()
        # print 'result', result
        result = result.split('\r\n')
        device_list = []
        for device in result[1:]:
            if len(device) <= 1 or not '\t' in device: continue
            device_list.append((device.split('\t')[0], device.split('\t')[1]))
#        if ret == False and len(device_list) == 0:
#            # 为避免ADB出现问题，此时重启ADB
#            ADB.close()
#            ADB.start()
#            return ADB.list_device()
        return device_list

    @staticmethod
    def is_local_device(device_id):
        '''是否是本地设备
        '''
        pattern = re.compile(r'([\w|\-|\.]+):(.+)')
        mat = pattern.match(device_id)
        if not mat or (mat.group(2).isdigit() and int(mat.group(2)) > 1024 and int(mat.group(2)) < 65536):
            return True
        else:
            return False

    @staticmethod
    def open_device(name=''):
        from clientsocket import is_tcp_server_opened
        if ADB.instance_dict.has_key(name):
            return ADB.instance_dict[name]
        if ADB.is_local_device(name):
            ADB.start()
            adb = ADB(name)
        else:
            adb = RemoteADB(name)
            timeout = 60
            time0 = time.time()
            while time.time() - time0 < timeout:
                if is_tcp_server_opened(adb.host_name, 5037): break
                time.sleep(10)
            else:
                raise RuntimeError('设备主机：%s:5037 无法访问' % adb.host_name)

        if adb.is_selinux_opened():
            if not adb.close_selinux():
                raise RuntimeError('关闭selinux失败，确认手机是否完美Root')
        ADB.instance_dict[name] = adb
        return adb

    @staticmethod
    def connect_device(name):
        '''使用TCP连接设备
        '''
        proc = subprocess.Popen([adb_path, 'connect', name], stdout=subprocess.PIPE)
        result = proc.stdout.read()
        if result.find('unable to connect to') >= 0:
            print >> sys.stderr, result
            return False
        return True

    @staticmethod
    def start():
        if is_adb_server_opend(): return False
        subprocess.call([adb_path, 'start-server'])
        return True

    @staticmethod
    def close():
        subprocess.call([adb_path, 'kill-server'])

    def read_event(self):
        '''读取事件
        '''
        import re, time
        pattern = re.compile(r'/dev/input/event\d: (\w+) (\w+) (\w+)')
        proc = self.run_shell_cmd('getevent', sync=False)
        while True:
            line = proc.stdout.readline().strip()
            # print line
            ret = pattern.search(line)
            if ret:
                # print ret.group(1)
                event_type = int(ret.group(1), 16)
                # print ret.group(2), ret.group(3)
                parm1 = int(ret.group(2), 16)
                parm2 = int(ret.group(3), 16)
                print time.time(),
                if event_type == 0:
                    print 'EV_SYN', parm1, parm2
                elif event_type == 1:
                    print 'EV_KEY',
                    if parm1 == 0x14a: print 'BTN_TOUCH',
                    else: print parm1,
                    print parm2
                elif event_type == 3:
                    print 'EV_ABS',
                    if parm1 == 0: print 'x',
                    elif parm1 == 1: print 'y',
                    elif parm1 == 0x30: print 'ABS_MT_TOUCH_MAJOR',
                    elif parm1 == 0x31: print 'ABS_MT_TOUCH_MINOR',
                    elif parm1 == 0x32: print 'ABS_MT_WIDTH_MAJOR',
                    elif parm1 == 0x33: print 'ABS_MT_WIDTH_MINOR',
                    elif parm1 == 0x34: print 'ABS_MT_ORIENTATION',
                    elif parm1 == 0x35: print 'ABS_MT_POSITION_X',
                    elif parm1 == 0x36: print 'ABS_MT_POSITION_Y',
                    elif parm1 == 0x39: print 'ABS_MT_TRACKING_ID',
                    elif parm1 == 0x3a: print 'ABS_MT_PRESSURE',
                    else: print '%x' % parm1,
                    print parm2
                else:
                    print line

    def get_cpu_time(self):
        '''获取手机全局总时间片和空闲时间片
        '''
        import re
        cpu_time = 0
        result = self.run_shell_cmd('cat /proc/stat')
        result = result.split('\r\n')[0]
        result, num = re.subn(r'\s+', ' ', result)  # 将字符串中多个相连的空白字符合并成一个空白字符
        results = result.split(' ')
        if len(results) < 5 :
            logger.warn('无法取得CPU时间片统计，请确保手机正常链接，并已启动！')
            return 0, 0
        idle_time = int(results[4])
        for item in results:
            item = item.strip()
            if not item: continue
            if item == 'cpu': continue
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
        if total_time == 0 :
            return -1
        return (total_time - idle_time) * 100 / total_time

    def dump_stack(self, pid_or_procname):
        '''获取进程调用堆栈
        '''
        if isinstance(pid_or_procname, (str, unicode)):
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
        
# ADB.close()
# ADB.start()

class RemoteADB(ADB):
    '''使用新版adb.exe实现
    '''
    def __init__(self, device_name=''):
        super(RemoteADB, self).__init__(device_name, False)
        # host:device_id
        pos = self._device_name.find(':')
        if pos < 0:
            raise RuntimeError('设备名称格式错误')
        self._host_name = self._device_name[:pos]
        self._device_name = self._device_name[pos + 1:]

    def _gen_adb_args(self, cmd):
        '''生成adb命令行参数
        '''
        args = [adb_path, '-H', self._host_name, cmd]
        if self._device_name:
            args = [adb_path, '-H', self._host_name, '-s', self._device_name, cmd]
        return args
    
    @property
    def host_name(self):
        '''
        '''
        return self._host_name
    
if __name__ == '__main__':
    adb = ADB.open_device('')
    
