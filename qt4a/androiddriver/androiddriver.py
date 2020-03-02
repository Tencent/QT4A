# -*- coding: UTF-8 -*-
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

'''Android测试桩代理
'''
from __future__ import print_function

import base64
import json
import re
import os
import six
import sys
import tempfile
import threading
import time

from qt4a.androiddriver.clientsocket import DirectAndroidSpyClient
from qt4a.androiddriver.devicedriver import DeviceDriver
from qt4a.androiddriver.util import logger, general_encode, SocketError, AndroidSpyError, ControlAmbiguousError, ControlExpiredError, ProcessExitError, QT4ADriverNotInstalled, Mutex, extract_from_zipfile


class EnumCommand(object):
    '''所有支持的命令字
    '''
    CmdHello = "Hello"
    CmdEnableDebug = "EnableDebug"
    CmdGetControl = "GetControl"
    CmdGetParent = "GetParent"
    CmdGetChildren = "GetChildren"
    CmdGetControlText = "GetControlText"
    CmdSetControlText = "SetControlText"
    CmdGetTextRect = "GetTextBoundingRect"
    CmdGetControlRect = "GetControlRect"
    CmdGetControlType = "GetControlType"
    CmdGetControlVisibility = "GetControlVisibility"
    CmdGetControlChecked = "GetControlChecked"
    CmdGetControlProgress = "GetControlProgress"
    CmdGetControlGravity = "GetControlGravity"
    CmdCaptureControl = "CaptureControl"
    CmdSendKey = "SendKey"
    CmdClick = "Click"
    CmdDrag = "Drag"
    CmdEnableSoftInput = "EnableSoftInput"
    CmdCloseActivity = "CloseActivity"
    CmdEvalScript = "EvalScript"
    CmdGetCurrentView = "GetCurrentView"
    CmdGetControlScrollRect = "GetControlScrollRect"
    CmdGetListViewInfo = "GetListViewInfo"
    CmdGetControlBackground = "GetControlBackground"
    CmdGetControlImageResource = "GetControlImageResource"
    CmdGetSelectedTabIndex = "GetSelectedTabIndex"
    CmdGetStaticFieldValue = "GetStaticFieldValue"
    CmdGetObjectFieldValue = "GetObjectFieldValue"
    CmdCallStaticMethod = "CallStaticMethod"
    CmdCallObjectMethod = "CallObjectMethod"
    CmdCallExternalMethod = "CallExternalMethod"  # 调用外部jar包中的方法
    CmdSetActivityPopup = "SetActivityPopup"
    CmdSetThreadPriority = "SetThreadPriority"
    CmdSetWebViewDebuggingEnabled = "SetWebViewDebuggingEnabled"


def install_qt4a_helper(adb, root_path):
    from qt4a.androiddriver.util import AndroidPackage, version_cmp
    qt4a_helper_package = 'com.test.androidspy'
    apk_path = os.path.join(root_path, 'QT4AHelper.apk')
    if adb.get_package_path(qt4a_helper_package):
        # 判断版本
        installed_version = adb.get_package_version(qt4a_helper_package)
        package = AndroidPackage(apk_path)
        install_version = package.version
        if version_cmp(install_version, installed_version) > 0:
            adb.install_apk(apk_path, True)
    else:
        adb.install_apk(apk_path)


def copy_android_driver(device_id_or_adb, force=False, root_path=None, enable_acc=True):
    '''测试前的测试桩拷贝
    '''
    from qt4a.androiddriver.adb import ADB

    if isinstance(device_id_or_adb, ADB):
        adb = device_id_or_adb
    else:
        adb = ADB.open_device(device_id_or_adb)

    if not root_path:
        current_path = os.path.abspath(__file__)
        if not os.path.exists(current_path) and '.egg' in current_path:
            # in egg
            egg_path = current_path
            while not os.path.exists(egg_path):
                egg_path = os.path.dirname(egg_path)
            assert(egg_path.endswith('.egg'))
            root_path = os.path.join(tempfile.mkdtemp(), 'tools')
            extract_from_zipfile(
                egg_path, 'qt4a/androiddriver/tools', root_path)
        else:
            root_path = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), 'tools')
    dst_path = '/data/local/tmp/qt4a/'

    current_version_file = os.path.join(root_path, 'version.txt')
    f = open(current_version_file, 'r')
    current_version = int(f.read())
    f.close()

    if not force:
        version_file = dst_path + 'version.txt'
        version = adb.run_shell_cmd('cat %s' % version_file)

        if version and not 'No such file or directory' in version and current_version <= int(version):
            install_qt4a_helper(adb, root_path) # 避免QT4A助手被意外删除的情况
            # 不需要拷贝测试桩
            logger.warn('忽略本次测试桩拷贝：当前版本为%s，设备中版本为%s' %
                        (current_version, int(version)))
            return

    try:
        adb.chmod(dst_path[:-1], '777')
    except:
        pass

    rooted = adb.is_rooted()

    cpu_abi = adb.get_cpu_abi()
    print('Current CPU arch: %s' % cpu_abi)
    use_pie = False
    if adb.get_sdk_version() >= 21 and cpu_abi != 'arm64-v8a':
        use_pie = True

    file_list = [os.path.join(cpu_abi, 'droid_inject'), os.path.join(cpu_abi, 'libdexloader.so'), os.path.join(
        cpu_abi, 'screenkit'), os.path.join(cpu_abi, 'libandroidhook.so'), 'inject', 'AndroidSpy.jar', 'SpyHelper.jar', 'SpyHelper.sh']

    if cpu_abi == 'arm64-v8a':
        file_list.append(os.path.join(cpu_abi, 'droid_inject64'))
        file_list.append(os.path.join(cpu_abi, 'libdexloader64.so'))
        file_list.append('inject64')
    if adb.get_sdk_version() >= 21:
        file_list.append(os.path.join(cpu_abi, 'libandroidhook_art.so'))

    if rooted and adb.is_selinux_opened():
        # 此时如果还是开启状态说明关闭selinux没有生效,主要是三星手机上面
        adb.run_shell_cmd('rm -r %s' % dst_path, True)
        # adb.run_shell_cmd('chcon u:object_r:shell_data_file:s0 %slibdexloader.so' % dst_path, True)  # 恢复文件context，否则拷贝失败
        # adb.run_shell_cmd('chcon u:object_r:shell_data_file:s0 %slibandroidhook.so' % dst_path, True)

    for file in file_list:
        file_path = os.path.join(root_path, file)
        if use_pie and not '.' in file and os.path.exists(file_path + '_pie'):
            file_path += '_pie'
        if not os.path.exists(file_path):
            continue
        save_name = os.path.split(file)[-1]
        if save_name.endswith('_art.so'):
            save_name = save_name.replace('_art', '')
        adb.push_file(file_path, dst_path + save_name)

    adb.chmod('%sdroid_inject' % dst_path, 755)
    adb.chmod('%sinject' % dst_path, 755)
    adb.chmod('%sscreenkit' % dst_path, 755)
    adb.run_shell_cmd('ln -s %sscreenkit %sscreenshot' % (dst_path, dst_path))

    if cpu_abi == 'arm64-v8a':
        adb.chmod('%sdroid_inject64' % dst_path, 755)
        adb.chmod('%sinject64' % dst_path, 755)

    try:
        print(adb.run_shell_cmd('rm -R %scache' %
                                dst_path, rooted))  # 删除目录 rm -rf
    except RuntimeError as e:
        logger.warn('%s' % e)
    # logger.info(adb.run_shell_cmd('mkdir %scache' % (dst_path), True)) #必须使用root权限，不然生成odex文件会失败

    adb.mkdir('%scache' % (dst_path), 777)

    install_qt4a_helper(adb, root_path)

    version_file_path = os.path.join(root_path, 'version.txt')
    dst_version_file_path = dst_path + os.path.split(version_file_path)[-1]
    adb.push_file(version_file_path, dst_version_file_path + '.tmp')  # 拷贝版本文件

    if rooted and adb.is_selinux_opened():
        # 此时如果还是开启状态说明关闭selinux没有生效,主要是三星手机上面
        # 获取sdcars context
        if adb.get_sdk_version() >= 23:
            sdcard_path = adb.get_sdcard_path()
            result = adb.run_shell_cmd('ls -Z %s' % sdcard_path)
            # u:object_r:media_rw_data_file:s0 u:object_r:rootfs:s0
            pattern = re.compile(r'\s+(u:object_r:.+:s0)\s+')
            ret = pattern.search(result)
            if not ret:
                raise RuntimeError('get sdcard context failed: %s' % result)
            context = ret.group(1)
            logger.info('sdcard context is %s' % context)
            adb.run_shell_cmd('chcon %s %s' %
                              (context, dst_path), True)  # make app access
            adb.run_shell_cmd(
                'chcon u:object_r:app_data_file:s0 %sSpyHelper.jar' % dst_path, True)
            adb.run_shell_cmd(
                'chcon u:object_r:app_data_file:s0 %sSpyHelper.sh' % dst_path, True)
            # 不修改文件context无法加载so
            adb.run_shell_cmd(
                'chcon u:object_r:system_file:s0 %slibdexloader.so' % dst_path, True)
            adb.run_shell_cmd(
                'chcon u:object_r:app_data_file:s0 %slibandroidhook.so' % dst_path, True)
            adb.run_shell_cmd('chcon %s %sAndroidSpy.jar' %
                              (context, dst_path), True)
            adb.run_shell_cmd('chcon %s %scache' % (context, dst_path), True)
        else:
            # 不修改文件context无法加载so
            adb.run_shell_cmd(
                'chcon u:object_r:app_data_file:s0 %slibdexloader.so' % dst_path, True)
            adb.run_shell_cmd(
                'chcon u:object_r:app_data_file:s0 %slibandroidhook.so' % dst_path, True)
            adb.run_shell_cmd(
                'chcon u:object_r:app_data_file:s0 %scache' % dst_path, True)

    if rooted:
        if adb.get_sdk_version() < 24:
            # 7.0以上发现生成的dex与运行时生成的dex有差别，可能导致crash
            logger.info(adb.run_shell_cmd('sh %sSpyHelper.sh loadDex %sAndroidSpy.jar %scache' % (
                dst_path, dst_path, dst_path), rooted))
            adb.chmod('%scache/AndroidSpy.dex' % dst_path, 666)
    else:
        if not 'usage:' in adb.run_shell_cmd('sh %sSpyHelper.sh' % dst_path):
            adb.mkdir('%scache/dalvik-cache' % dst_path, 777)

    if rooted and adb.is_selinux_opened() and adb.get_sdk_version() >= 23:
        # 提升权限
        try:
            adb.list_dir('/system/bin/app_process32')
        except RuntimeError:
            adb.copy_file('/system/bin/app_process',
                          '%sapp_process' % dst_path)
        else:
            adb.copy_file('/system/bin/app_process32',
                          '%sapp_process' % dst_path)
        adb.chmod('%sapp_process' % dst_path, 755)
        adb.run_shell_cmd(
            'chcon u:object_r:system_file:s0 %sapp_process' % dst_path, True)

    adb.run_shell_cmd('mv %s %s' % (dst_version_file_path +
                                    '.tmp', dst_version_file_path), rooted)

    # 同步手机时间
    device_driver = DeviceDriver(adb)
    try:
        input_method = 'com.test.androidspy/.service.QT4AKeyboardService'
        device_driver.modify_system_setting(
            'secure', 'enabled_input_methods', input_method)
        device_driver.modify_system_setting(
            'secure', 'default_input_method', input_method)
        if enable_acc:
            device_driver.modify_system_setting('secure', 'enabled_accessibility_services',
                                                'com.test.androidspy/com.test.androidspy.service.QT4AAccessibilityService')
            device_driver.modify_system_setting(
                'secure', 'accessibility_enabled', 1)
    except:
        logger.exception('set default input method failed')
    try:
        device_driver.modify_system_setting('system', 'time_12_24', 24)
        device_driver.modify_system_setting(
            'system', 'screen_off_timeout', 600 * 1000)
    except:
        logger.exception('set system time failed')


class AndroidDriver(object):
    '''
    '''

    qt4a_path = '/data/local/tmp/qt4a'

    def __init__(self, device_driver, process_name, addr='127.0.0.1'):
        self._device_driver = device_driver
        self._adb = device_driver.adb
        self._process_name = process_name
        self._addr = addr
        self._process = {}  # 保存原始PID用于判断是否是新进程
        self._sync_lock = {}  # 同步锁
        self._max_block_time = 30  # 最长锁时间,防止卡死
        self._lock = threading.Lock()  # 创建AndroidDriver实例的互斥锁
        self._is_init = False
        self._client = None

    @staticmethod
    def create(process_name, device_or_driver):
        '''创建Driver实例

        :param process_name: 目标进程名
        :type  process_name: string
        :param device:       设备实例
        :type  device:       Device or DeviceDriver
        '''
        if hasattr(device_or_driver, '_device_driver'):
            device_driver = device_or_driver._device_driver
        else:
            device_driver = device_or_driver
        host_addr = '127.0.0.1'
        if not device_driver._is_local_device:
            host_addr = device_driver.adb.host_name
        return AndroidDriver(device_driver, process_name, addr=host_addr)

    @staticmethod
    def get_process_name_hash(process_name, device_id):
        '''根据进程名和设备id计算端口值
                结果范围：[5100, 5200)
        TODO: hash冲突的解决
        '''
        result = 0
        start_port = 15000
        port_range = 1000
        text = device_id + process_name
        for i in range(len(text)):
            c = text[i]
            asc = ord(c)
            result = 31 * result + asc

        if result > port_range:
            result %= port_range
        return result + start_port

    def _create_client(self):
        '''创建新的Client实例
        '''
        sock = self._adb.create_tunnel(self._process_name, 'localabstract')
        if sock == None:
            return None
        return DirectAndroidSpyClient(sock, timeout=360)

    def _safe_init_driver(self):
        '''多线程安全的初始化测试桩
        '''
        if not self._is_init:
            with Mutex(self._lock):
                if not self._is_init:
                    self._init_driver()
                    self._is_init = True

    def _init_driver(self):
        '''初始化测试桩
        '''
        self._client = self._create_client()
        if self._client != None:
            # 字段赋值
            self._process['name'] = self._process_name
            self._process['id'] = 0  # process id may change
            if self.hello() != None:
                self._process['id'] = self._adb.get_pid(self._process_name)
                return

        timeout = 20
        time0 = time.time()
        proc_exist = False
        while time.time() - time0 < timeout:
            if not proc_exist:
                pid = self._adb.get_pid(self._process_name)
                if pid > 0:
                    proc_exist = True
                    self._process['name'] = self._process_name
                    self._process['id'] = pid
                    break

            time.sleep(1)

        if not proc_exist:
            raise RuntimeError('进程：%s 在%d秒内没有出现' %
                               (self._process_name, timeout))

        inject_file = 'inject'
        if self._adb.is_app_process64(pid if self._adb.is_rooted() else self._process_name):
            # 64 bit process
            inject_file += '64'
        timeout = 30

        try:
            if self._adb.is_art():
                # Android 5.0上发现注入容易导致进程退出
                self._wait_for_cpu_low(20, 10)

            time0 = time.time()
            cmdline = '%s/%s %s' % (self._get_driver_root_path(),
                                    inject_file, self._process_name)
            while time.time() - time0 < timeout:
                if self._adb.is_rooted():
                    ret = self._adb.run_shell_cmd(
                        cmdline, True, timeout=120, retry_count=1)
                else:
                    ret = self._adb.run_as(
                        self._process_name, cmdline, timeout=120, retry_count=1)
                logger.debug('inject result: %s' % ret)
                if 'not found' in ret:
                    raise QT4ADriverNotInstalled(
                        'QT4A driver damaged, please reinstall QT4A driver')
                if 'Inject Success' in ret:
                    break
                elif 'Operation not permitted' in ret:
                    # 可能是进程处于Trace状态
                    pid = self._adb.get_pid(self._process_name)
                    status = self._adb.get_process_status(pid)
                    tracer_pid = int(status['TracerPid'])
                    if tracer_pid > 0:
                        if int(status['PPid']) == tracer_pid:
                            # 使用TRACEME方式防注入
                            raise Exception('应用使用了防注入逻辑,注入失败')
                        logger.warn('TracerPid is %d' % tracer_pid)
                        self._adb.kill_process(tracer_pid)
                time.sleep(1)

        except RuntimeError as e:
            logger.exception('%s\n%s' % (e, self._adb.run_shell_cmd('ps')))
            if self._adb.is_rooted():
                logger.info(self._adb.dump_stack(self._process_name))
            raise e
        timeout = 10
        time0 = time.time()
        while time.time() - time0 < timeout:
            if self._client == None:
                self._client = self._create_client()
            if self._client != None and self.hello() != None:
                return
            time.sleep(0.1)
        raise RuntimeError('连接测试桩超时')

    def _get_driver_root_path(self):
        '''获取驱动文件根目录
        '''
        if self._adb.is_rooted():
            return self.__class__.qt4a_path
        package_name = self._process_name
        if ':' in package_name:
            package_name = package_name.split(':')[0]
        if not self._device_driver.is_debug_package(package_name):
            raise NotImplementedError(
                'Non root device doesn\'t support release package')
        root_path = '/data/data/%s/qt4a' % package_name  # 使用应用目录作为根目录
        result = self._adb.run_as(package_name, 'ls -l %s/inject' % root_path)
        if not 'No such file or directory' in result:
            return root_path

        # 拷贝驱动文件
        self._adb.run_as(package_name, 'mkdir %s' % root_path)
        self._adb.run_as(package_name, 'mkdir %s/cache' % root_path)
        file_list = ['AndroidSpy.jar']  # , 'cache/AndroidSpy.dex'
        if self._adb.is_app_process64(package_name):
            file_list.extend(
                ['droid_inject64', 'inject64', 'libdexloader64.so'])
        else:
            file_list.extend(
                ['droid_inject', 'inject', 'libdexloader.so', 'libandroidhook.so'])
        for filename in file_list:
            self._adb.run_as(package_name, 'cp %s/%s %s/%s' %
                             (self.__class__.qt4a_path, filename, root_path, filename))
        # self._device.adb.run_as(package_name, 'sh %s/SpyHelper.sh loadDex %s/AndroidSpy.jar %s/cache' % (self.__class__.qt4a_path, self.__class__.qt4a_path, root_path))
        return root_path

    def _wait_for_cpu_low(self, max_p_cpu, max_t_cpu, timeout=20, interval=0.5):
        '''等待待注入进程CPU使用率降低到max_p_cpu，线程CPU使用率降低到max_t_cpu

        :param max_p_cpu: 进程占用的CPU
        :type max_p_cpu:  int
        :param max_t_cpu: 线程占用的CPU
        :type max_t_cpu:  int
        '''
        time0 = time.time()
        while time.time() - time0 < timeout:
            ret = self._adb.get_process_cpu(self._process_name)
            if ret != None:
                p_cpu, t_cpu = ret
                logger.debug('current cpu: %d, %d' % (p_cpu, t_cpu))
                if p_cpu < max_p_cpu and t_cpu < max_t_cpu:
                    return
            time.sleep(interval)

    def close(self):
        '''关闭连接
        '''
        if self._client:
            self._client.close()
            self._client = None

    def _get_lock(self, thread_id):
        '''获取锁
        '''
        if not thread_id in self._sync_lock:
            self._sync_lock[thread_id] = threading.Event()
            self._sync_lock[thread_id].set()
        return self._sync_lock[thread_id]

    def suspend_thread(self, thread_id, max_wait_time=30):
        '''阻塞
        '''
        self._max_block_time = max_wait_time
        self._get_lock(thread_id).clear()  # Reset the internal flag to false

    def resume_thread(self, thread_id):
        '''解锁
        '''
        self._get_lock(thread_id).set()  # Set the internal flag to true

    def _wait_for_event(self, thread_id, timeout):
        '''等待事件
        '''
        if self._get_lock(thread_id).is_set():
            return
        time0 = time.time()
        ret = self._get_lock(thread_id).wait(timeout)
        if ret:
            cost_time = time.time() - time0
            logger.debug('thread %s wait %s S' % (thread_id, cost_time))
        else:
            # 超时
            logger.warn('thread %s wait for sync event timeout' % thread_id)
            self.resume_thread(thread_id)  # 防止出错后一直等待
        return ret

    def send_command(self, cmd_type, **kwds):
        '''发送命令
        '''
        curr_thread_id = threading.current_thread().ident
        self._wait_for_event(curr_thread_id, self._max_block_time)

        if cmd_type != EnumCommand.CmdHello:
            self._safe_init_driver()  # 确保测试桩连接正常

        result = self._client.send_command(cmd_type, **kwds)
        if result == None:
            pid = self._adb.get_pid(self._process['name'])
            if pid > 0 and pid != self._process['id']:
                # 新进程，需要重新注入
                logger.info('process %s id changed: %d %d' %
                            (self._process['name'], self._process['id'], pid))
                self._is_init = False  # 需要重新初始化
                self._process['id'] = pid
                return self.send_command(cmd_type, **kwds)
            elif pid == 0:
                raise ProcessExitError('被测进程已退出，确认是否发生Crash')
            elif cmd_type != EnumCommand.CmdHello:
                # hello包不重试
                logger.debug('socket error, try to reconnect')
                for _ in range(3):
                    # 为防止由于设备短暂失联导致的连接断开，这里调一次adb forward
                    self._client = self._create_client()
                    result = self._client.send_command(cmd_type, **kwds)
                    if result != None:
                        return result
                raise SocketError('Connect Failed')
            else:
                raise SocketError('Connect Failed')
        if 'Error' in result:
            if result['Error'] == u'控件已失效':
                raise ControlExpiredError(result['Error'])
            elif result['Error'] == u'控件类型错误':
                control_type = self.get_control_type(kwds['Control'])
                raise TypeError('%s,当前控件类型为:%s' %
                                (result['Error'], control_type))
            else:
                raise AndroidSpyError(result['Error'])
        return result

    def hello(self):
        '''确认Server身份
        '''
        for _ in range(3):
            try:
                result = self.send_command(EnumCommand.CmdHello)
            except SocketError:
                time.sleep(1)
                continue
            except AndroidSpyError:
                logger.exception('init error')
                time.sleep(2)
                continue
            # self._enable_debug()
            if not 'Result' in result:
                raise RuntimeError('Server error')
            items = result['Result'].split(':')
            if len(items) > 0 and items[-1].isdigit():
                if self._process['id'] and int(items[-1]) != self._process['id']:
                    raise RuntimeError(
                        'Server pid not match %s' % result['Result'])
            return result['Result']

    def _enable_debug(self):
        '''启用Debug模式
        '''
        self.send_command(EnumCommand.CmdEnableDebug)

    def get_control(self, activity, parent, locator, get_position=False):
        '''获取控件hashcode
        '''
        kwds = {}
        if activity:
            kwds['Activity'] = activity
        if parent:
            kwds['Parent'] = parent
        kwds['Locator'] = locator
        if get_position:
            kwds['GetPosition'] = get_position
        try:
            result = self.send_command(EnumCommand.CmdGetControl, **kwds)
        except ControlExpiredError as e:
            raise e
        except AndroidSpyError as e:
            err_msg = e.args[0].strip()
            err_msg = general_encode(err_msg)
            if '找到重复控件' in err_msg or 'Multiple controls found' in err_msg:
                qpath = '/'.join(' && '.join([(key + it[key][0] + '"' + str(
                    it[key][1]) + '"') for key in it.keys()]) for it in locator)
                qpath = general_encode(qpath)
                err_msg = '定位到重复控件：/%s\n%s' % (qpath, '\n'.join(err_msg.split('\n')[1:]))
                raise ControlAmbiguousError(err_msg)
            elif '查找控件失败' in err_msg or 'Control not found' in err_msg:
                if get_position and ':' in err_msg:
                    _, pos = err_msg.split(':')
                    return int(pos)
            return 0
        if 'Result' in result:
            return result['Result']
        return 0

    def get_parent(self, control):
        '''获取父控件
        '''
        result = self.send_command(EnumCommand.CmdGetParent, Control=control)
        return result['Result']

    def get_children(self, control):
        '''获取子节点列表
        '''
        result = self.send_command(EnumCommand.CmdGetChildren, Control=control)
        return result['Result']

    def get_control_text(self, control, html_format=False):
        '''获取控件文本
        '''
        result = self.send_command(
            EnumCommand.CmdGetControlText, Control=control, UseHtml=html_format)
        result = result['Result']
        if html_format:
            # 处理html编码
            from six.moves.html_parser import HTMLParser
            result = HTMLParser().unescape(result)
        return result

    def set_control_text(self, control, text):
        '''设置控件文本
        '''
        result = self.send_command(
            EnumCommand.CmdSetControlText, Control=control, Text=text)
        return result['Result']

    def get_text_rect(self, control, start_offset, end_offset):
        '''获取文本框中指定字符串的区域坐标
        '''
        result = self.send_command(
            EnumCommand.CmdGetTextRect, Control=control, StartOffset=start_offset, EndOffset=end_offset)
        return result['Result']

    def get_control_type(self, control, include_baseclass=False):
        '''获取控件类型
        '''
        result = self.send_command(
            EnumCommand.CmdGetControlType, Control=control, IncludeBaseClass=include_baseclass)
        if not include_baseclass:
            return result['Result']
        else:
            return result['Result'].split(',')

    def get_control_rect(self, control):
        '''获取控件位置信息
        '''
        result = self.send_command(
            EnumCommand.CmdGetControlRect, Control=control)
        return result['Result']

    def get_control_visibility(self, control):
        '''获取控件可见性
        '''
        result = self.send_command(
            EnumCommand.CmdGetControlVisibility, Control=control)
        return result['Result']

    def get_control_checked(self, control):
        '''获取CommpandButton控件是否选择
        '''
        result = self.send_command(
            EnumCommand.CmdGetControlChecked, Control=control)
        return result['Result']

    def get_control_gravity(self, control):
        '''获取控件位置信息
        '''
        result = self.send_command(
            EnumCommand.CmdGetControlGravity, Control=control)
        return result['Result']

    def get_control_progress(self, control):
        '''获取ProgressBar控件的进度
        '''
        result = self.send_command(
            EnumCommand.CmdGetControlProgress, Control=control)
        return result['Result']

    def get_control_background(self, control):
        '''获取控件背景资源id
        '''
        result = self.send_command(
            EnumCommand.CmdGetControlBackground, Control=control)
        return result['Result']

    def get_control_scroll_rect(self, control):
        '''获取控件滚动区域范围
        '''
        result = self.send_command(
            EnumCommand.CmdGetControlScrollRect, Control=control)
        return result['Result']

    def get_control_image_resource(self, control):
        '''获取控件Image资源信息
        '''
        result = self.send_command(
            EnumCommand.CmdGetControlImageResource, Control=control)
        return result['Result']

    def get_listview_info(self, control, timeout=20):
        '''获取AbsListView类型的相关信息
        '''
        time0 = time.time()
        while time.time() - time0 < timeout:
            # 过滤掉一些明显错误的数据
            result = self.send_command(
                EnumCommand.CmdGetListViewInfo, Control=control)
            result = result['Result']
            if (result['Count'] > 0 and result['FirstPosition'] >= result['Count']) or \
                    result['LastPosition'] > result['Count']:  # 最后一项>=总项数 {"LastPosition":0,"FirstPosition":0,"Count":0}
                time.sleep(0.03)
                continue
            return result
        raise RuntimeError('获取ListView控件信息错误')

    def get_selected_tab_index(self, control):
        '''获取TabWidget控件当前所选项
        '''
        result = self.send_command(
            EnumCommand.CmdGetSelectedTabIndex, Control=control)
        return result['Result']

    def capture_control(self, control):
        result = self.send_command(
            EnumCommand.CmdCaptureControl, Control=control)
        data = result['Result']
        if not isinstance(data, bytes):
            data = data.encode()
        data = base64.decodestring(data)
        return data

    def send_key(self, key_list):
        '''发送按键，只允许单个按键或组合键
        '''
        from qt4a.androiddriver.util import KeyCode
        if isinstance(key_list, str):
            return self.send_keys(key_list)
        elif isinstance(key_list, int):
            # 将整型按键转为list
            key_list = [key_list]
        if len(key_list) == 0 or len(key_list) > 3:
            raise RuntimeError('按键错误')
        keys = ''
        for key in key_list:
            keys += str(key) + ','
        keys = keys[:-1]
        if keys == str(KeyCode.KEYCODE_HOME) or keys == str(KeyCode.KEYCODE_BACK):  # Home键需要特殊处理
            return self._device_driver.send_key(int(keys))
        else:
            return self.send_command(EnumCommand.CmdSendKey, Keys=keys)

    def send_keys(self, text):
        '''发送字符串，目前不支持中文
        '''
        from qt4a.androiddriver.util import KeyCode
        key_list = KeyCode.get_key_list(text)
        for key in key_list:
            self.send_key(key)

    def click(self, control, x, y, sleep_time=0):
        if x < 0 or y < 0:
            raise RuntimeError('坐标错误：(%d, %d)' % (x, y))

        try:
            if not control:
                result = self.send_command(
                    EnumCommand.CmdClick, X=x, Y=y, SleepTime=int(sleep_time * 1000))
            else:
                result = self.send_command(
                    EnumCommand.CmdClick, Control=control, X=x, Y=y, SleepTime=int(sleep_time * 1000))
            # print (result['Result'])
            return result['Result']
        except AndroidSpyError as e:
            if str(e).find('java.lang.SecurityException') >= 0:
                # 有时操作过快会出现该问题
                return False
            elif 'ErrControlNotShown' in str(e):
                return False
            elif str(e) == '控件已失效':
                # 认为点击成功了
                pic_name = '%s.png' % int(time.time())
                logger.warn('%s %s' % (e, pic_name))
                self._device_driver.take_screen_shot(pic_name)
                return True
            else:
                raise e

    def drag(self, x1, y1, x2, y2, count=5, wait_time=40, send_down_event=True, send_up_event=True):
        '''滑动
        :param x1: 起始横坐标
        :type x1:  int
        :param y1: 起始纵坐标
        :type y1:  int
        :param x2: 终点横坐标
        :type x2:  int
        :param y2: 终点纵坐标
        :type y2:  int
        :param count: 步数
        :type count: int
        :param wait_time: 滑动过程中每步之间的间隔时间，ms
        :type wait_time: int
        :param send_down_event: 是否发送按下消息
        :type send_down_event: boolean
        :param send_up_event: 是否发送弹起消息
        :type send_up_event: boolean 
        '''
        if y1 != y2 and abs(y1 - y2) < 60:  # 此时滑动距离会很短
            # 保证最短滑动距离为40，在索尼ce0682上发现小于40时会变成点击 三星9300上发现有时60像素以下滑动不起来
            m = (y1 + y2) // 2
            if y1 - y2 > 0:
                d = 30
            else:
                d = -30
            y1 = m + d  # TODO:坐标合法性判断
            y2 = m - d
        for _ in range(3):
            try:
                result = self.send_command(EnumCommand.CmdDrag, X1=x1, Y1=y1, X2=x2, Y2=y2,
                                           StepCount=count,
                                           SleepTime=wait_time,
                                           SendDownEvent=send_down_event,
                                           SendUpEvent=send_up_event)
            except AndroidSpyError as e:
                if str(e).find('java.lang.SecurityException') >= 0:
                    logger.info('java.lang.SecurityException,current activity:%s' %
                                self._device_driver.get_current_activity())  # 检测是否有弹窗
                    # 有时操作过快会出现该问题
                    time.sleep(0.1)
                else:
                    raise e
            else:
                return True
        logger.error('drag (%s, %s, %s, %s) failed' % (x1, y1, x2, y2))
        return False

    def enable_soft_input(self, control, enable=False):
        '''启用/禁止软键盘
        '''
        self.send_command(EnumCommand.CmdEnableSoftInput,
                          Control=control, Enable=enable)

    def _close_activity(self, activity):
        '''关闭Activity
        '''
        result = self.send_command(
            EnumCommand.CmdCloseActivity, Activity=activity)
        return result['Result']

    def close_activity(self, activity):
        '''关闭Activity
        '''
        try:
            return self._close_activity(activity)
        except ProcessExitError:
            logger.warn('close_activity error: process %s not exist' %
                        self._process_name)
            return -3  # 进程退出

    def eval_script(self, control, frame_xpaths, script):
        '''执行JavaScript
        '''
        result = self.send_command(
            EnumCommand.CmdEvalScript, Control=control, Script=script, Frame=frame_xpaths)
        return result['Result']

    def get_static_field_value(self, class_name, field_name):
        '''获取类`class_name`中静态字段`field_name`的值
        '''
        result = self.send_command(
            EnumCommand.CmdGetStaticFieldValue, ClassName=class_name, FieldName=field_name)
        return result['Result']

    def get_object_field_value(self, control, field_name):
        '''获取对象中字段`field_name`的值
        '''
        result = self.send_command(
            EnumCommand.CmdGetObjectFieldValue, Control=control, FieldName=field_name)
        return result['Result']

    def call_static_method(self, class_name, method_name, control=None, ret_type='', *args):
        '''调用静态方法
        '''
        kwargs = {}
        if control:
            kwargs['Control'] = control
        result = self.send_command(EnumCommand.CmdCallStaticMethod, ClassName=class_name,
                                   Method=method_name, RetType=ret_type, Args=args, **kwargs)
        return result['Result']

    def call_object_method(self, control, inner_obj, method_name, ret_type='', *args):
        '''调用对象方法
        '''
        result = self.send_command(EnumCommand.CmdCallObjectMethod, Control=control,
                                   InnerObject=inner_obj, Method=method_name, RetType=ret_type, Args=args)
        return result['Result']

    def call_external_method(self, jar_path, cls_name, add_to_classloader=False, **kwds):
        '''调用外部jar包中的方法
        '''
        result = self.send_command(EnumCommand.CmdCallExternalMethod, JarPath=jar_path,
                                   ClsName=cls_name, AddToClassLoader=add_to_classloader, Args=kwds)
        return result['Result']

    def set_activity_popup(self, activity, popup=False):
        '''禁用某些Activity自动弹出
        '''
        result = self.send_command(
            EnumCommand.CmdSetActivityPopup, Activity=activity, Popup=popup)
        return result['Result']

    def _format_control_tree(self, result, indent=0):
        '''格式化控件树
        '''
        if not result:
            return ''
        id = result.pop('Id')
        padding = '+--' * indent + '+'
        ret = '%s%s (' % (padding, id)
        rect = result.pop('Rect')
        bounding_rect = '(%s, %s, %s, %s)' % (
            rect['Left'], rect['Top'], rect['Width'], rect['Height'])
        children = result.pop('Children')

        for key in result.keys():
            ret += '%s: %s, ' % (key, result[key])
        ret += 'BoundingRect: %s)\n' % bounding_rect
        for child in children:
            ret += self._format_control_tree(child, indent + 1)
        return ret

    def _get_control_tree(self, activity, index):
        '''获取控件树
        '''
        return self.send_command('GetControlTree', Activity=activity, Index=index)['Result']

    def get_control_tree(self, activity, index=-1):
        '''获取控件树
        '''
        result = self._get_control_tree(activity, index)
        if len(activity) > 0:
            return self._format_control_tree(result)
        else:
            output = ''
            for activity in result.keys():
                output += '%s:\n' % activity
                output += self._format_control_tree(result[activity])
            return output

    def set_thread_priority(self, priority):
        '''设置测试线程优先级

        :param priority: 要设置的优先级
        :type priority:  EnumThreadPriority
        '''
        self.send_command(EnumCommand.CmdSetThreadPriority, Priority=priority)

    def set_webview_debugging_enabled(self, control, enable=True):
        '''设置WebView调试状态

        :param control: WebView控件hashcode
        :type  control: int/long
        :param enable: 是否开启WebView调试
        :type  enable: bool
        '''
        self.send_command(
            EnumCommand.CmdSetWebViewDebuggingEnabled, Control=control, Enable=True)


if __name__ == '__main__':
    pass
