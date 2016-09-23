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

# 2013/5/13 apple 创建

import sys
import time
import json
import threading
from clientsocket import AndroidSpyClient
from util import logger, SocketError, AndroidSpyError, ControlExpiredError, Mutex

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
    CmdSensorEvent = "SensorEvent"
    CmdEnableSoftInput = "EnableSoftInput"
    CmdCloseActivity = "CloseActivity"
    CmdEvalScript = "EvalScript"
    CmdGetCurrentView = "GetCurrentView"
    CmdGetControlScrollRect = "GetControlScrollRect"
    CmdGetListViewInfo = "GetListViewInfo"
    CmdGetControlBackground = "GetControlBackground"
    CmdGetControlImageResource = "GetControlImageResource"
    CmdGetSelectedTabIndex = "GetSelectedTabIndex"
    CmdGetObjectFieldValue = "GetObjectFieldValue"
    CmdCallObjectMethod = "CallObjectMethod"
    CmdCallExternalMethod = "CallExternalMethod"  # 调用外部jar包中的方法
    CmdSetActivityPopup = "SetActivityPopup"
    CmdSetThreadPriority = "SetThreadPriority"
    
def copy_android_driver(device_id='', force=False):
    '''测试前的测试桩拷贝
    '''
    import os
    from adb import ADB
    if not device_id:
        device_list = ADB.list_device()
        device_list = [dev for dev in device_list if dev[1] == 'device']
        if len(device_list) == 0:
            raise RuntimeError('当前没有插入手机')
        elif len(device_list) == 1:
            device_id = device_list[0][0]
        elif len(device_list) > 1:
            i = 0
            text = '当前设备列表:\n'
            for dev in device_list:
                # if dev[1] != 'device': continue
                i += 1
                text += '%d. %s\n' % (i, dev[0])
            print text
            while True:
                result = raw_input('请输入要拷贝测试桩的设备序号:')
                if result.isdigit():
                    if int(result) > len(device_list):
                        print >> sys.stderr, '序号范围为: [1, %d]' % len(device_list)
                        time.sleep(0.1)
                        continue
                    device_id = device_list[int(result) - 1][0]
                else:
                    if not result in [dev[0] for dev in device_list]:
                        print >> sys.stderr, '设备序列号不存在: %r' % result
                        time.sleep(0.1)
                        continue
                    device_id = result
                break
            print '您将向设备"%s"拷贝测试桩……' % device_id
    adb = ADB.open_device(device_id)
    cur_path = os.path.dirname(os.path.abspath(__file__))
    dst_path = '/data/local/tmp/qt4a/'

    current_version_file = os.path.join(cur_path, 'tools', 'version.txt')
    f = open(current_version_file, 'r')
    vurrent_version = int(f.read())
    f.close()
    
    if not force:
        version_file = dst_path + 'version.txt'
        version = adb.run_shell_cmd('cat %s' % version_file)
    
        if version and not 'No such file or directory' in version and vurrent_version <= int(version):
            # 不需要拷贝测试桩
            if not adb.get_package_path('com.test.qt4amockapp'):
                logger.warn('install QT4AMockApp')
                adb.install_apk(os.path.join(cur_path, 'tools', 'QT4AMockApp.apk'))
            logger.warn('忽略本次测试桩拷贝：当前版本为%s，设备中版本为%s' % (vurrent_version, version))
            return
    
    if not adb.is_rooted():
        result = adb.run_shell_cmd('id', True)
        if not 'uid=0(root)' in result:
            raise RuntimeError('设备未root：%s' % result)
        
    cpu_abi = adb.get_cpu_abi()
    print '当前系统的CPU架构为：%s' % cpu_abi
    use_pie = False
    if adb.get_sdk_version() >= 21: use_pie = True
    file_list = [os.path.join(cpu_abi, 'inject'), os.path.join(cpu_abi, 'libdexloader.so'), os.path.join(cpu_abi, 'setpropex'), os.path.join(cpu_abi, 'libandroidhook.so'), 'AndroidSpy.jar', 'androidhook.jar', 'SpyHelper.jar', 'SpyHelper.sh']
    
    if adb.is_selinux_opened():
        # 此时如果还是开启状态说明关闭selinux没有生效,主要是三星手机上面
        adb.run_shell_cmd('chcon u:object_r:shell_data_file:s0 %slibdexloader.so' % dst_path, True)  # 恢复文件context，否则拷贝失败
        adb.run_shell_cmd('chcon u:object_r:shell_data_file:s0 %slibandroidhook.so' % dst_path, True)
        
    for file in file_list:
        file_path = os.path.join(cur_path, 'tools', file)
        if use_pie and not '.' in file: file_path += '_pie'
        adb.push_file(file_path, dst_path + os.path.split(file)[-1])
    dst_dir = dst_path[:dst_path.rfind('/')]
    # adb.run_shell_cmd('chmod 777 %s' % dst_dir, True)
    # logger.info(adb.run_shell_cmd('chmod 777 %sinject' % (dst_path), True))
    adb.chmod('%sinject' % dst_path, 777)
    # adb.run_shell_cmd('chmod 777 %sAndroidSpy.jar' % (dst_path), True)
    try:
        print adb.run_shell_cmd('rm -R %scache' % dst_path, True)  # 删除目录 rm -rf
    except RuntimeError, e:
        logger.warn('%s' % e)
    # logger.info(adb.run_shell_cmd('mkdir %scache' % (dst_path), True)) #必须使用root权限，不然生成odex文件会失败
    # logger.info(adb.run_shell_cmd('chmod 777 %scache' % dst_path, True))
    # adb.chmod('%scache' % dst_path, 777)
    adb.mkdir('%scache' % (dst_path), 777)
    logger.info(adb.run_shell_cmd('sh %sSpyHelper.sh loadDex %sAndroidSpy.jar %scache' % (dst_path, dst_path, dst_path), True))
    # logger.info(adb.run_shell_cmd('chmod 777 %ssetpropex' % dst_path, True))
    adb.chmod('%ssetpropex' % dst_path, 777)
    logger.info(adb.run_shell_cmd('.%ssetpropex ro.secure 0' % dst_path, True))

    adb.install_apk(os.path.join(cur_path, 'tools', 'QT4AMockApp.apk'), True)
    
    if adb.is_selinux_opened():
        # 此时如果还是开启状态说明关闭selinux没有生效,主要是三星手机上面
        adb.run_shell_cmd('chcon u:object_r:app_data_file:s0 %slibdexloader.so' % dst_path, True)  # 不修改文件context无法加载so
        adb.run_shell_cmd('chcon u:object_r:app_data_file:s0 %slibandroidhook.so' % dst_path, True)
        
    version_file_path = os.path.join(cur_path, 'tools', 'version.txt')
    adb.push_file(version_file_path, dst_path + os.path.split(version_file_path)[-1])  # 最后拷贝版本文件

    # 同步手机时间
    from androiddevice import AndroidDevice
    device = AndroidDevice(device_id)
    device.modify_system_setting('system', 'time_12_24', 24)
    device.modify_system_setting('system', 'screen_off_timeout', 600 * 1000)
    device.set_system_timezone()
    device.set_system_time()

class AndroidDriver(object):
    '''
    '''

    qt4a_path = '/data/local/tmp/qt4a'

    def __init__(self, device, process_name, addr='127.0.0.1'):
        self._device = device
        self._process_name = process_name
        port = self.get_process_name_hash(process_name, device.device_id)
        logger.info('port=%d' % port)
        self._port = port
        self._client = AndroidSpyClient(self._port, addr=addr, timeout=360)
        # self._client.pre_connect()
        self._process = {}  # 保存原始PID用于判断是否是新进程
        self._sync_lock = {}  # 同步锁
        self._max_block_time = 30  # 最长锁时间,防止卡死
        self._lock = threading.Lock()  # 创建AndroidDriver实例的互斥锁
        self._is_init = False
        
    @staticmethod
    def create(process_name, device=None):
        '''创建Driver实例
        '''
        from androiddevice import AndroidDevice
        if device == None:
            device = AndroidDevice('')
        if not isinstance(device, AndroidDevice):
            device = device._device
        host_addr = '127.0.0.1'
        if not device._is_local_device: host_addr = device.adb.host_name
        return AndroidDriver(device, process_name, addr=host_addr)
    
    @staticmethod
    def get_process_name_hash(process_name, device_id):
        '''根据进程名和设备id计算端口值
                结果范围：[5100, 5200)
        TODO: hash冲突的解决
        '''
        result = 0
        start_port = 15000
        port_range = 1000
        for c in process_name + device_id:
            asc = ord(c)
            result += 13 * asc
            if result > port_range:
                result %= port_range
        return result + start_port
    
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
        if AndroidSpyClient.server_opened(self._port): 
            # 字段赋值
            logger.info('port %d opened' % self._port)
            self._process['name'] = self._process_name
            self._process['id'] = self._device.adb.get_pid(self._process_name)
            if self.hello() != None:
                return

        timeout = 20
        time0 = time.time()
        proc_exist = False
        while time.time() - time0 < timeout:
            if not proc_exist:
                pid = self._device.adb.get_pid(self._process_name)
                if pid > 0:
                    proc_exist = True
                    self._process['name'] = self._process_name
                    self._process['id'] = pid
                    break

            time.sleep(1)

        if not proc_exist:
            raise RuntimeError('进程：%s 在%d秒内没有出现' % (self._process_name, timeout))
        
        timeout = 30
        
        try:
            if self._device.is_art():
                # Android 5.0上发现注入容易导致进程退出
                self._wait_for_cpu_low(20, 10)
            
            time0 = time.time()
            while time.time() - time0 < timeout:
                ret = self._device.adb.run_shell_cmd('.%s/inject %s' % (AndroidDriver.qt4a_path, self._process_name), True, timeout=120, retry_count=1)
                logger.debug('inject result: %s' % ret)
                if 'Inject Success' in ret: break
                elif 'Operation not permitted' in ret:
                    # 可能是进程处于Trace状态
                    pid = self._device.adb.get_pid(self._process_name)
                    status = self._device.adb.get_process_status(pid)
                    tracer_pid = int(status['TracerPid'])
                    if tracer_pid > 0:
                        if int(status['PPid']) == tracer_pid:
                            # 使用TRACEME方式防注入
                            raise Exception('应用使用了防注入逻辑,注入失败')
                        logger.warn('TracerPid is %d' % tracer_pid)
                        self._device.adb.kill_process(tracer_pid)
                time.sleep(1)
                
        except RuntimeError, e:
            logger.error('%s\n%s' % (e, self._device.adb.run_shell_cmd('ps')))
            logger.info(self._device.adb.dump_stack(self._process_name))
            raise e
        timeout = 10
        time0 = time.time()
        while time.time() - time0 < timeout:
            time.sleep(0.5)
            new_port = self._device.adb.forward(self._port, self._process_name, 'localabstract')  # TODO: 判断PC端口是否占用
            if new_port != self._port:
                self._port = new_port
                logger.info('new port=%d' % new_port)
            if self.hello() != None:
                return
        raise RuntimeError('连接测试桩超时')
    
    def _wait_for_cpu_low(self, max_p_cpu, max_t_cpu, timeout=20, interval=0.5):
        '''等待待注入进程CPU使用率降低到max_p_cpu，线程CPU使用率降低到max_t_cpu

        :param max_p_cpu: 进程占用的CPU
        :type max_p_cpu:  int
        :param max_t_cpu: 线程占用的CPU
        :type max_t_cpu:  int
        '''
        time0 = time.time()
        while time.time() - time0 < timeout:
            ret = self._device.adb.get_process_cpu(self._process_name)
            if ret != None:
                p_cpu, t_cpu = ret
                logger.debug('current cpu: %d, %d' % (p_cpu, t_cpu))
                if p_cpu < max_p_cpu and t_cpu < max_t_cpu: return
            time.sleep(interval)
            
    def get_current_activity(self):
        '''获取当前Activity
        '''
        return self._device.get_current_activity()

    def close(self):
        '''关闭连接
        '''
        self._client.close()
        self._client = None
    
    def _get_lock(self, thread_id):
        '''获取锁
        '''
        if not self._sync_lock.has_key(thread_id):
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
        if self._get_lock(thread_id).is_set(): return
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
        
        if cmd_type != EnumCommand.CmdHello: self._safe_init_driver()  # 确保测试桩连接正常
        
        result = self._client.send_command(cmd_type, **kwds)
        if result == None:
            pid = self._device.adb.get_pid(self._process['name'])
            if pid > 0 and pid != self._process['id']:
                # 新进程，需要重新注入
                logger.info('process %s id changed: %d %d' % (self._process['name'], self._process['id'], pid))
                self._is_init = False  # 需要重新初始化
                self._process['id'] = pid
                return self.send_command(cmd_type, **kwds)
            elif pid == 0:
                raise RuntimeError('被测进程已退出，确认是否发生Crash')
            elif cmd_type != EnumCommand.CmdHello:
                # hello包不重试
                logger.debug('socket error, try to reconnect')
                for _ in range(3):
                    # 为防止由于设备短暂失联导致的连接断开，这里调一次adb forward
                    self._device.adb.forward(self._port, self._process['name'], 'localabstract')
                    result = self._client.send_command(cmd_type, **kwds)
                    if result != None: return result
                raise SocketError('Connect Failed')
            else:
                raise SocketError('Connect Failed')
        if result.has_key('Error'):
            if result['Error'] == u'控件已失效':
                raise ControlExpiredError(result['Error'])
            elif result['Error'] == u'控件类型错误':
                control_type = self.get_control_type(kwds['Control'])
                raise TypeError('%s,当前控件类型为:%s' % (result['Error'], control_type))
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
            return result['Result']

    def _enable_debug(self):
        '''启用Debug模式
        '''
        self.send_command(EnumCommand.CmdEnableDebug)

    def get_current_view(self):
        '''
        '''
        result = self.send_command(EnumCommand.CmdGetCurrentView)
        return result['Result']

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
        except ControlExpiredError, e:
            raise e
        except AndroidSpyError, e:
            err_msg = e.args[0]
            if isinstance(err_msg, unicode):
                err_msg = err_msg.encode('utf8')
            if err_msg.find('java.lang.RuntimeException: 找到重复控件') >= 0:
                import sys
                try:
                    print >> sys.stderr, e.args[0]
                except:
                    pass
                err_msg = '定位到重复控件：%s' % locator
                try:
                    from tuia.exceptions import ControlAmbiguousError
                    raise ControlAmbiguousError(err_msg)
                except ImportError:
                    repeat_list = []
                    for line in e.args[0].split('\n')[1:]:
                        if not line: continue
                        pos = line.find('[')
                        pos2 = line.find(']', pos)
                        repeat_list.append(line[pos + 1 : pos2])
                    err_msg = 'RepeatList:%s' % json.dumps(repeat_list)
                    raise RuntimeError(err_msg)
            elif '查找控件失败' in err_msg:
                if get_position and ':' in err_msg:
                    _, pos = err_msg.split(':')
                    return int(pos)
            return 0
        if 'Result' in result: return result['Result']
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
        result = self.send_command(EnumCommand.CmdGetControlText, Control=control, UseHtml=html_format)
        result = result['Result']
        if html_format:
            # 处理html编码
            import HTMLParser
            html_parser = HTMLParser.HTMLParser()
            result = html_parser.unescape(result)
        return result
    
    def set_control_text(self, control, text):
        '''设置控件文本
        '''
        result = self.send_command(EnumCommand.CmdSetControlText, Control=control, Text=text)
        return result['Result']
    
    def get_text_rect(self, control, start_offset, end_offset):
        '''获取文本框中指定字符串的区域坐标
        '''
        result = self.send_command(EnumCommand.CmdGetTextRect, Control=control, StartOffset=start_offset, EndOffset=end_offset)
        return result['Result']
    
    def get_control_type(self, control, include_baseclass=False):
        '''获取控件类型
        '''
        result = self.send_command(EnumCommand.CmdGetControlType, Control=control, IncludeBaseClass=include_baseclass)
        if not include_baseclass:
            return result['Result']
        else:
            return result['Result'].split(',')
        
    def get_control_rect(self, control):
        '''获取控件位置信息
        '''
        result = self.send_command(EnumCommand.CmdGetControlRect, Control=control)
        return result['Result']

    def get_control_visibility(self, control):
        '''获取控件可见性
        '''
        result = self.send_command(EnumCommand.CmdGetControlVisibility, Control=control)
        return result['Result']

    def get_control_checked(self, control):
        '''获取CommpandButton控件是否选择
        '''
        result = self.send_command(EnumCommand.CmdGetControlChecked, Control=control)
        return result['Result']

    def get_control_gravity(self, control):
        '''获取控件位置信息
        '''
        result = self.send_command(EnumCommand.CmdGetControlGravity, Control=control)
        return result['Result']

    def get_control_progress(self, control):
        '''获取ProgressBar控件的进度
        '''
        result = self.send_command(EnumCommand.CmdGetControlProgress, Control=control)
        return result['Result']

    def get_control_background(self, control):
        '''获取控件背景资源id
        '''
        result = self.send_command(EnumCommand.CmdGetControlBackground, Control=control)
        return result['Result']

    def get_control_scroll_rect(self, control):
        '''获取控件滚动区域范围
        '''
        result = self.send_command(EnumCommand.CmdGetControlScrollRect, Control=control)
        return result['Result']

    def get_control_image_resource(self, control):
        '''获取控件Image资源信息
        '''
        result = self.send_command(EnumCommand.CmdGetControlImageResource, Control=control)
        return result['Result']

    def get_listview_info(self, control, timeout=20):
        '''获取AbsListView类型的相关信息
        '''
        time0 = time.time()
        while time.time() - time0 < timeout:
            # 过滤掉一些明显错误的数据
            result = self.send_command(EnumCommand.CmdGetListViewInfo, Control=control)
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
        result = self.send_command(EnumCommand.CmdGetSelectedTabIndex, Control=control)
        return result['Result']

    def capture_control(self, control):
        result = self.send_command(EnumCommand.CmdCaptureControl, Control=control)
        data = result['Result']
        # print data
        import base64
        data = base64.decodestring(data)
        return data

    def send_key(self, key_list):
        '''发送按键，只允许单个按键或组合键
        '''
        from util import KeyCode
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
            return self._device.send_key(int(keys))
        else:
            return self.send_command(EnumCommand.CmdSendKey, Keys=keys)

    def send_keys(self, text):
        '''发送字符串，目前不支持中文
        '''
        from util import KeyCode
        key_list = KeyCode.get_key_list(text)
        # print key_list
        for key in key_list:
            self.send_key(key)

    def click(self, control, x, y, sleep_time=0):
        if x < 0 or y < 0:
            raise RuntimeError('坐标错误：(%d, %d)' % (x, y))

        try:
            if not control:
                result = self.send_command(EnumCommand.CmdClick, X=x, Y=y, SleepTime=int(sleep_time * 1000))
            else:
                result = self.send_command(EnumCommand.CmdClick, Control=control, X=x, Y=y, SleepTime=int(sleep_time * 1000))
            # print result['Result']
            return result['Result']
        except AndroidSpyError, e:
            if str(e).find('java.lang.SecurityException') >= 0:
                # 有时操作过快会出现该问题
#                 pic_name = '%s.png' % int(time.time())
#                 logger.warn('%s %s' % (e, pic_name))
#                 self._device.take_screen_shot(pic_name)
                return False
            elif 'ErrControlNotShown' in str(e):
                return False
            elif str(e) == '控件已失效':
                # 认为点击成功了
                pic_name = '%s.png' % int(time.time())
                logger.warn('%s %s' % (e, pic_name))
                self._device.take_screen_shot(pic_name)
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
        :type step: int
        '''
        if y1 != y2 and abs(y1 - y2) < 60:  # 此时滑动距离会很短
            m = (y1 + y2) / 2  # 保证最短滑动距离为40，在索尼ce0682上发现小于40时会变成点击 三星9300上发现有时60像素以下滑动不起来
            if y1 - y2 > 0: d = 30
            else: d = -30
            y1 = m + d  # TODO:坐标合法性判断
            y2 = m - d
        for i in range(3):
            try:
                return self.send_command(EnumCommand.CmdDrag, X1=x1, Y1=y1, X2=x2, Y2=y2,
                                         StepCount=count,
                                         SleepTime=wait_time,
                                         SendDownEvent=send_down_event,
                                         SendUpEvent=send_up_event)
            except AndroidSpyError, e:
                if str(e).find('java.lang.SecurityException') >= 0:
                    # 有时操作过快会出现该问题
                    time.sleep(0.1)
                else:
                    raise e
        logger.error('drag (%s, %s, %s, %s) failed' % (x1, y1, x2, y2))

    def shake(self, duration=4, interval=0.05):
        '''摇一摇
        '''
        import random
        time0 = time.time()
        max_val = 40
        while time.time() - time0 < duration:
            x = random.randint(-max_val, max_val)
            y = random.randint(-max_val, max_val)
            z = random.randint(-max_val, max_val)
            self.send_command(EnumCommand.CmdSensorEvent, Sensor="Accelerometer", Data=[x, y, z], wait=True)
            time.sleep(interval)

    def enable_soft_input(self, control, enable=False):
        '''启用/禁止软键盘
        '''
        self.send_command(EnumCommand.CmdEnableSoftInput, Control=control, Enable=enable)
    
    def _close_activity(self, activity):
        '''关闭Activity
        '''
        try:
            result = self.send_command(EnumCommand.CmdCloseActivity, Activity=activity)
            return result['Result']
        except AndroidSpyError, e:
            logger.exception('close_activity error')
            if '不存在' in str(e): return True
            raise e
        
    def close_activity(self, activity):
        '''关闭Activity
        '''
        for _ in range(3):
            if self._close_activity(activity): return True
            time.sleep(1)
        return False

    def eval_script(self, control, frame_xpaths, script):
        '''执行JavaScript
        '''
        result = self.send_command(EnumCommand.CmdEvalScript, Control=control, Script=script, Frame=frame_xpaths)
        return result['Result']

    def get_object_field_value(self, control, field_name):
        '''
        '''
        result = self.send_command(EnumCommand.CmdGetObjectFieldValue, Control=control, FieldName=field_name)
        return result['Result']
    
    def call_object_method(self, control, inner_obj, method_name, ret_type='', *args):
        '''调用对象方法
        '''
        result = self.send_command(EnumCommand.CmdCallObjectMethod, Control=control, InnerObject=inner_obj, Method=method_name, RetType=ret_type, Args=args)
        return result['Result']
    
    def call_external_method(self, jar_path, cls_name, add_to_classloader=False, **kwds):
        '''调用外部jar包中的方法
        '''
        result = self.send_command(EnumCommand.CmdCallExternalMethod, JarPath=jar_path, ClsName=cls_name, AddToClassLoader=add_to_classloader, Args=kwds)
        return result['Result']
    
    def set_activity_popup(self, activity, popup=False):
        '''禁用某些Activity自动弹出
        '''
        result = self.send_command(EnumCommand.CmdSetActivityPopup, Activity=activity, Popup=popup)
        return result['Result']
    
    def _format_control_tree(self, result, indent=0):
        '''格式化控件树
        '''
        id = result.pop('Id')
        padding = '+--' * indent + '+'
        ret = '%s%s (' % (padding, id)
        rect = result.pop('Rect')
        bounding_rect = '(%s, %s, %s, %s)' % (rect['Left'], rect['Top'], rect['Width'], rect['Height'])
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
        return self._format_control_tree(result)
    
    def set_thread_priority(self, priority):
        '''设置测试线程优先级
        
        :param priority: 要设置的优先级
        :type priority:  EnumThreadPriority
        '''
        self.send_command(EnumCommand.CmdSetThreadPriority, Priority=priority)
        
if __name__ == '__main__':
    copy_android_driver('')
    exit()
