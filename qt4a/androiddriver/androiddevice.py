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

'''Android设备
'''

# 2013/6/28 apple 创建

import os
import time
import json
from clientsocket import AndroidSpyClient
from util import logger

qt4a_path = '/data/local/tmp/qt4a'
    
class AndroidDevice(object):
    '''Android设备
    '''
    device_dict = {}
    service_name = 'com.test.androidspy'
    service_port = 19862  # 部分机器只能使用TCP端口
    
    def __init__(self, device_id):
        self._device_id = device_id
        from adb import ADB
        self._is_local_device = ADB.is_local_device(device_id)
        self._adb = None
        self._client = None
        self._use_socket = True
        self._module = ''
        self._system_version = ''
        self._sdk_version = 0
        self._cpu_type = None
        self._imei = ''
        self._width = 0
        self._height = 0

    @staticmethod
    def get_instance(device_id):
        if device_id in AndroidDevice.device_dict.keys():
            return AndroidDevice.device_dict[device_id]
        device = AndroidDevice(device_id)
        AndroidDevice.device_dict[device_id] = device
        return device

    @property
    def device_id(self):
        if not self._device_id:
            self._device_id = self.adb.run_shell_cmd('getprop ro.serialno')
        return self._device_id

    @property
    def cpu_type(self):
        '''cpu类型
        '''
        if not self._cpu_type:
            self._cpu_type = self.adb.get_cpu_abi()
        return self._cpu_type

    @property
    def imei(self):
        '''手机串号
        '''
        if not self._imei:
            self._imei = self.get_device_imei()
        return self._imei

    @property
    def module(self):
        '''设备型号
        '''
        if self._module == '':
            self._module = self._get_device_module()
        return self._module

    @property
    def system_version(self):
        '''系统版本
        '''
        if self._system_version == '':
            self._system_version = self._get_system_version()
        return self._system_version

    @property
    def sdk_version(self):
        '''SDK版本
        '''
        if self._sdk_version == 0:
            self._sdk_version = self._get_sdk_version()
        return self._sdk_version

    @property
    def debuggable(self):
        '''是否是调试版系统
        '''
        if not hasattr(self, '_debuggable'):
            self._debuggable = not (self.adb.run_shell_cmd('getprop ro.secure') == '1' and self.adb.run_shell_cmd('getprop ro.debuggable') == '0')
        return self._debuggable

    @property
    def screen_size(self):
        '''屏幕大小
        '''
#         if self._width == 0 or self._height == 0:
#             self._width, self._height = self.get_screen_size()
#         return self._width, self._height
        return self.get_screen_size()  # 横竖屏变化时长宽会交换
    
    @property
    def language(self):
        '''语言
        '''
        return self.adb.run_shell_cmd('sh %s/SpyHelper.sh getLanguage' % (qt4a_path))

    @property
    def country(self):
        '''国家
        '''
        return self.adb.run_shell_cmd('sh %s/SpyHelper.sh getCountry' % (qt4a_path))

    @property
    def adb(self):
        if self._adb == None:
            from adb import ADB
            self._adb = ADB.open_device(self._device_id)
        return self._adb

    @property
    def client(self):
        if self._client == None:
            # 运行SpyHelper.sh
            self._client = self.run_server()
            self._client.pre_connect()
        return self._client

    def __str__(self):
        return '%s(%s %s Android %s)' % (self.device_id, self.module, self.cpu_type, self.system_version)

    @staticmethod
    def list_local_devices():
        '''获取本地设备列表
        '''
        from adb import ADB
        result = []
        for device_id in ADB.list_device():
            result.append(AndroidDevice(device_id))
        return result
    
    def get_property(self, prop):
        '''读取系统属性
        
        :param prop: 属性名称
        :type prop:
        '''
        return self.adb.run_shell_cmd('getprop %s' % prop)
    
    def set_property(self, prop, value):
        '''设置属性
        '''
        self.adb.run_shell_cmd('setprop %s %s' % (prop, value), True)
        
    def exist(self):
        '''设备是否存在
        '''
        return 'device' in self.adb.get_state()
    
    def is_art(self):
        '''是否是art虚拟机
        '''
        if not hasattr(self, '_is_art'):
            ret = self.get_property('persist.sys.dalvik.vm.lib')
            if not ret: ret = self.get_property('persist.sys.dalvik.vm.lib.2')
            self._is_art = 'libart.so' in ret
        return self._is_art
    
    def get_device_imei(self):
        '''获取设备imei号
        '''
        try:
            return self.adb.get_device_imei()
        except RuntimeError, e:
            logger.warn('获取设备imei失败: %s' % e)
            return self.adb.run_shell_cmd('sh %s/SpyHelper.sh getDeviceImei' % (qt4a_path), True)
        
    def is_remote_device(self):
        '''是否是远程设备
        '''
        from adb import RemoteADB
        return isinstance(self.adb, RemoteADB)

    def install_package(self, pkg_path, pkg_name='', overwrite=False):
        '''安装应用
        '''
        from util import InstallPackageFailedError
        from adb import TimeoutError
        if not os.path.exists(pkg_path):
            raise RuntimeError('安装包：%r 不存在' % pkg_path)
        for _ in range(3):
            self.adb.install_apk(pkg_path, overwrite)
            try:
                boot_time = self.get_system_boot_time()
            except TimeoutError:
                logger.exception('get_system_boot_time failed')
                return True
            if boot_time >= 60 * 5: return True
            logger.info('System Boot Time: %s S' % boot_time)
            time0 = time.time()
            if not pkg_name: pkg_name = self.adb._get_package_name(pkg_path)
            install_success = True
            while time.time() - time0 < 60:
                # 酷派大神F2和中兴红牛V5上发现重启后安装应用容易失败
                dir_root_list = ['/data/data/%s' % pkg_name, '/sdcard/Android/data/%s' % pkg_name]
                for i in range(len(dir_root_list)):
                    try:
                        self.adb.list_dir(dir_root_list[i])
                        if len(dir_root_list) > 1: dir_root_list = [dir_root_list[i]]  # 只保留正确的位置
                        break
                    except RuntimeError, e:
                        logger.warn(u'install app error: %r' % e)
                        if i >= len(dir_root_list) - 1:
                            install_success = False
                            break
                if not install_success: break
                time.sleep(1)
            if install_success: return True
        raise InstallPackageFailedError('安装应用失败')
    
    def kill_process(self, package_name):
        '''杀死进程
        '''
        try:
            self.adb.run_shell_cmd('sh %s/SpyHelper.sh killProcess %s' % (qt4a_path, package_name), True)
        except RuntimeError, e:
            logger.warn('killProcess error: %r' % e)
        for _ in range(3):
            if not self.adb.kill_process(package_name): return True
        return False

    def push_file(self, src_path, dst_path):
        '''向手机中拷贝文件
        '''
        if not os.path.exists(src_path):
            raise RuntimeError('文件：%r 不存在' % src_path)
        fuse_path = '/storage/emulated/0'  # 4.2中对sdcard的引用
        if dst_path.startswith(fuse_path):
            dst_path = dst_path.replace(fuse_path, '/sdcard')
        return self.adb.push_file(src_path, dst_path)

    def push_dir(self, src_path, dst_path):
        '''向手机中拷贝文件夹
        '''
        if not os.path.exists(src_path):
            raise RuntimeError('文件夹：%s 不存在' % src_path)
        for file in os.listdir(src_path):
            file_src_path = os.path.join(src_path, file)
            file_dst_path = dst_path + '/' + file
            self.push_file(file_src_path, file_dst_path)

    def pull_file(self, src_path, dst_path):
        '''将手机中的文件拷贝到PC中
        '''
        fuse_path = '/storage/emulated/0'  # 4.2中对sdcard的引用
        if src_path.startswith(fuse_path):
            src_path = src_path.replace(fuse_path, '/sdcard')
        try:
            ret = self.adb.pull_file(src_path, dst_path)
            if ret.find('does not exist') < 0: return
        except RuntimeError, e:
            logger.warn('pull file failed: %s' % e)
            if src_path.startswith('/data/local/tmp/'): raise e
        _, files = self.adb.list_dir(src_path)
        # 需要root权限
        tmp_path = '/data/local/tmp/%s' % files[0]['name']
        self.adb.copy_file(src_path, tmp_path)
        self.adb.chmod(tmp_path, 444)
        self.pull_file(tmp_path, dst_path)
        self.adb.delete_file(tmp_path)

    def pull_dir(self, src_path, dst_path):
        '''从手机中拷贝文件夹到PC
        '''
        if not os.path.exists(dst_path):
            os.mkdir(dst_path)
        subdirs, files = self.adb.list_dir(src_path)
        for file in files:
            self.pull_file(src_path + '/' + file['name'], os.path.join(dst_path, file['name']))
        for subdir in subdirs:
            self.pull_dir(src_path + '/' + subdir['name'], os.path.join(dst_path, subdir['name']))

    def delete_folder(self, folder_path):
        '''删除文件夹
        '''
        self.adb.run_shell_cmd('rm -R %s' % folder_path, True, timeout=60)

    def _get_device_module(self):
        '''获取设备型号
        '''
        return self.adb.get_device_module()

    def _get_system_version(self):
        '''获取系统版本
        '''
        return self.adb.get_system_version()

    def _get_sdk_version(self):
        '''获取SDK版本
        '''
        return self.adb.get_sdk_version()

    def get_external_sdcard_path(self):
        '''获取外置SD卡路径
        '''
        if not self._use_socket:
            return self.adb.run_shell_cmd('sh %s/SpyHelper.sh getExternalStorageDirectory' % (qt4a_path), True)
        else:
            result = self.client.send_command('GetExternalStorageDirectory')
            result = result['Result']
            if not result:
                raise RuntimeError('获取SD卡路径失败')
            return result

    def refresh_media_store(self, file_path=''):
        '''刷新图库，显示新拷贝到手机的图片
        '''
        from adb import TimeoutError
        command = ''
        if not file_path:
            sdcard_path = self.get_external_sdcard_path()
            command = 'am broadcast -a android.intent.action.MEDIA_MOUNTED --ez read-only false -d file://%s' % sdcard_path
        else:
            if file_path.startswith('/sdcard/'):
                file_path = self.get_external_sdcard_path() + file_path[7:]
            command = 'am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://%s' % file_path
        try:
            self.adb.run_shell_cmd(command, True)
        except TimeoutError:
            logger.exception('refresh_media_store failed')
            return False
        # self.adb.run_shell_cmd('am broadcast -a android.intent.action.BOOT_COMPLETED')
        if file_path and self.sdk_version >= 16:
            return self._wait_for_media_available(file_path)

    def get_process_meminfo(self, process_name):
        '''获取进程内存信息
        '''
        return self.adb.get_process_meminfo(process_name)
    
    def _get_current_activity(self, has_package_name=False):
        '''获取当前Activity
        '''
        if has_package_name: has_package_name = 'true'
        else: has_package_name = 'false'
        ret = self.adb.run_shell_cmd('sh %s/SpyHelper.sh getCurrentActivity %s' % (qt4a_path, has_package_name), True)
        if '\r\n' in ret: return ret.split('\r\n')[-1]
        return ret
    
    def get_current_activity(self):
        '''获取当前窗口
        '''
        # 突然发现目前的2.3设备都可以修改系统属性了，暂时改为全部使用ViewServer获取当前窗口
#        if self.sdk_version <= 10 and not self.debuggable:  # 使用GetCurrentActivity延时较大，改用logcat方式
#            import time
#            if not hasattr(self, '_activity_logcat'):
#                self._start_activity_logcat_thread()
#
#            timeout = 10
#            time0 = time.time()
#            while time.time() - time0 < timeout:
#                if self._current_activity: return self._current_activity
#                time.sleep(1)
#            return self._send_command('GetCurrentActivity')
        if not self._use_socket:
            return self.adb.run_shell_cmd('sh %s/SpyHelper.sh getCurrentWindow' % (qt4a_path), True)
        else:
            from androiddriver import SocketError
            timeout = 5
            time0 = time.time()
            while time.time() - time0 < timeout:
                try:
                    result = self._send_command('GetCurrentWindow')
                    if not result:
                        time.sleep(0.5)
                        continue
                    return result
                except SocketError, e:
                    raise e
                except RuntimeError, e:
                    logger.warn('GetCurrentWindow error: %s' % e)
            # raise RuntimeError('获取当前Activity失败')

            logger.warn('GetCurrentWindow failed')
            return self._send_command('GetCurrentActivity')

    def get_screen_size(self):
        '''获取屏幕大小
        '''
        result = self._send_command('GetScreenSize')  # 使用Socket方式可能会出现获取到结果一直为0的情况
        if isinstance(result, dict) and result['Width'] > 0 and result['Height'] > 0:
            return result['Width'], result['Height']
        else:
            result = self.adb.run_shell_cmd('sh %s/SpyHelper.sh getScreenSize' % (qt4a_path), True)
            result = result.split('\n')[-1]
            width, height = result.split(',')
            return int(width), int(height)
    
    def _take_screen_shot(self, path, _format='png', quality=90):
        '''使用命令截图
        '''
        result = self.adb.run_shell_cmd('sh %s/SpyHelper.sh takeScreenshot %s %s %s' % (qt4a_path, path, _format, quality), True)
        if not 'true' in result:
            logger.warn('take_screen_shot failed: %s' % result)
            self.adb.run_shell_cmd('screencap %s' % path, True)
            self.adb.run_shell_cmd('chmod 444 %s' % path, True)
        return True
                    
    def take_screen_shot(self, path, _format='png', quality=90):
        '''截屏
        '''
        tmp_path = '%s/screen.png' % qt4a_path
        err = None
        result = self.client.send_command('TakeScreenshot', SavePath=tmp_path, Format=_format, Quality=quality)
        if result == None:
            if self.exist(): 
                self._take_screen_shot(tmp_path, _format, quality)
            else:
                err = 'device not found'
        else:
            if 'Result' in result:
                if not result['Result']: self._take_screen_shot(tmp_path, _format, quality)
            else:
                logger.warn('screenshot error：%s' % result.get('Error'))
                if 'NullPointerException' in result.get('Error'):
                    self._restart_server()
                self._take_screen_shot(tmp_path, _format, quality)
        if err:
            raise RuntimeError('手机屏幕截图错误：%s' % err)
        self.pull_file(tmp_path, path)
        return True

    def drag(self, x1, y1, x2, y2, count=5, sleep_time=40):
        '''
        '''
        self.client.send_command('Drag', X1=x1, Y1=y1, X2=x2, Y2=y2, StepCount=count, SleepTime=sleep_time)

    def _kill_server(self):
        '''杀死Server进程，用于Server卡死时
        '''
        return self.adb.kill_process(self.service_name + ':service')

    def _server_opend(self):
        '''判断测试桩进程是否运行
        '''
        pid = self.adb.get_pid(self.service_name + ':service')
        return pid > 0

    def _run_server(self, server_name):
        '''运行系统测试桩
        '''
        from util import TimeoutError
        timeout = 10
        time0 = time.time()
        while time.time() - time0 < timeout:
            try:
                ret = self.adb.run_shell_cmd('sh %s/SpyHelper.sh runServer %s' % (qt4a_path, server_name), root=True, retry_count=1, timeout=10)
                logger.debug('run_server %s' % ret)
                if 'java.lang.UnsatisfiedLinkError' in ret:
                    raise RuntimeError('启动系统测试桩进程失败：\n%s' % ret)
            except TimeoutError, e:
                logger.warn('runServer timeout: %s' % e)
            
            if self._server_opend(): return True
            # 在三星Nexus S上发现子进程会退出
            self.adb.run_shell_cmd('sh %s/SpyHelper.sh runServer %s forkChild' % (qt4a_path, server_name), root=True, sync=False)
            if self._server_opend(): return True
            time.sleep(1)
        return False

    def run_server(self, server_name=''):
        '''运行测试桩进程,创建服务端
        '''
        if server_name == '': server_name = self.service_name
        from androiddriver import AndroidDriver
        port = AndroidDriver.get_process_name_hash(server_name, self.device_id)
        from clientsocket import TCPSocketClient
        addr = '127.0.0.1'
        if not self._is_local_device: addr = self.adb.host_name
        client = AndroidSpyClient(port, addr=addr, enable_log=False)  # False

        # if TCPSocketClient.server_opened(port, addr): return client
 
        time0 = time.time()
        timeout = 20
        kill_server = False
        
        if self.adb.is_selinux_opened():
            # 创建TCP服务端
            server_name = str(self.service_port)
            
        while time.time() - time0 < timeout:
            if not kill_server and time.time() - time0 >= timeout / 2:
                # server进程存在问题，强杀
                self._kill_server()
                if self._client: self._client.close()
                self._client = None
                kill_server = True
            ret = self._run_server(server_name)
            logger.debug('server opend: %s' % ret)
            server_type = 'localabstract'
            if server_name == str(self.service_port): server_type = 'tcp'
            new_port = self.adb.forward(port, server_name, server_type)
            if new_port != port:
                client = AndroidSpyClient(new_port, addr=addr, enable_log=False)
                logger.info('new port=%d' % new_port)
            if client.hello() != None: return client
        raise RuntimeError('连接系统测试桩超时')
    
    def _restart_server(self):
        '''重启系统测试桩
        '''
        self._kill_server()
        self._client.close()
        self._client = None
        self.run_server()
        
    def _send_command(self, cmd_type, **kwds):
        '''发送命令
        '''
        result = self.client.send_command(cmd_type, **kwds)
        # print result
        if result == None:
            logger.error('系统测试桩连接错误')
            self._kill_server()
            if self._client: self._client.close()
            self._client = None
            return self._send_command(cmd_type, **kwds)
            # raise SocketError('Socket连接错误')
        if result.has_key('Error'):
            raise RuntimeError(result['Error'])
        if not result.has_key('Result'):
            raise RuntimeError('%s返回结果错误：%s' % (cmd_type, result))
        return result['Result']

    def _hello(self):
        return self.client.send_command('Hello')

    def close(self):
        if self._client != None:
            self._client.send_command('Exit')
            self._client = None

    def reboot(self, wait_cpu_low=True, min_boot_time=0, **kwds):
        '''重启手机
        
        :param wait_cpu_low:   是否等待CPU使用率降低
        :type wait_cpu_low:    bool
        :param min_boot_time: 允许重启的最短开机时间，单位为小时
        :type min_boot_time:  int
        '''
        import re
        pattern = re.compile(r'^.+:\d+$')
        try:
            ret = self.adb.run_shell_cmd('sh /data/local/tmp/qt4a/SpyHelper.sh reboot %d' % min_boot_time, True, retry_count=1, timeout=30)
            if ret == 'false': return
        except RuntimeError, e:
            logger.warn('reboot: %r' % e)
            if pattern.match(self.device_id):
                try:
                    self.adb.reboot(60)
                except RuntimeError:
                    logger.warn('reboot: %s' % e)
                    # 虚拟机会出现明明重启成功却一直不返回的情况
            else:
                self.adb.reboot(0)  # 不能使用reboot shell命令，有些手机需要root权限才能执行
#        if pattern.match(self.device_id):
#            time.sleep(10)  # 虚拟机会提示已连接但是并没有连上
#            while True:
#                if self.adb.connect_device(self.device_id): break
#                time.sleep(5)
        time.sleep(10)  # 防止设备尚未关闭，一般重启不可能在10秒内完成
        self.adb.wait_for_boot_complete()
        self._adb = None  # 重启后部分属性可能发生变化,需要重新实例化
        
        timeout = 120

        if wait_cpu_low == True:
            usage = 20
            duration = 10
            if kwds != None :
                if kwds.has_key('usage'):
                    usage = kwds['usage']
                if kwds.has_key('duration'):
                    duration = kwds['duration']
                if kwds.has_key('timeout') :
                    timeout = kwds['timeout']
            self.wait_for_cpu_usage_low(usage, duration, timeout)
        else:
            # 等待su正常工作，酷派5890上发现重启后要一段时间su才能正常使用
            time0 = time.time()
            while time.time() - time0 < timeout:
                try:
                    for _ in range(3):
                        self.adb._check_need_quote(10)  # 连续3次不超时才认为没有问题
                    break
                except RuntimeError, e:
                    text = ''
                    try:
                        text = 'reboot: %s' % e
                    except UnicodeEncodeError:
                        text = 'reboot: %r' % e
                    logger.warn(text)
                    time.sleep(20)

    def wait_for_cpu_usage_low(self, usage=20, duration=10, timeout=120):
        '''等待CPU使用率持续时间内在指定值以下
        :param usage:    cpu使用率阈值
        :type  usage:    int
        :param duration: 持续时间(秒)
        :type  duration: int
        :param timeout:  超时时间，超市时间到后，无论当前CPU使用率是多少，都会返回
        :type  timeout:  int
        '''
        time0 = time.time()
        time1 = time0
        while time.time() - time0 < timeout:
            cpu_usage = self.adb.get_cpu_usage()
            # print cpu_usage
            if cpu_usage > usage :
                time1 = time.time()
            if time.time() - time1 > duration:
                break
            time.sleep(1)

    def connect_wifi(self, wifi_name):
        '''连接指定的Wifi
        '''
        # return self._send_command('ConnectWifi', WifiName=wifi_name)
        result = self.adb.run_shell_cmd('sh %s/SpyHelper.sh connectWifi %s' % (qt4a_path, wifi_name), True, timeout=60)
        if not 'true' in result:
            logger.debug('connect wifi result: %s' % result)
            return False
        return True
        
    def disable_wifi(self):
        '''禁用Wifi
        '''
        return self._send_command('DisableWifi')

    def enable_data_connection(self):
        '''启用数据连接
        '''
        result = self.adb.run_shell_cmd('sh %s/SpyHelper.sh setDataConnection true' % (qt4a_path), True, timeout=60)
        if not 'true' in result:
            sim_state = self.get_sim_card_state()
            if 'SIM_STATE_ABSENT' in sim_state or 'SIM_STATE_UNKNOWN' in sim_state:
                raise RuntimeError('设备中没有SIM卡')
            raise RuntimeError('启用数据连接失败:%r' % result)
        return True
        # return self._send_command('SetDataConnection', Enable=True)

    def disable_data_connection(self):
        '''禁用数据连接
        '''
        result = self.adb.run_shell_cmd('sh %s/SpyHelper.sh setDataConnection false' % (qt4a_path), True, timeout=60)
        if not 'true' in result:
            raise RuntimeError('禁用数据连接失败:%r' % result)
        return True
        # return self._send_command('SetDataConnection', Enable=False)

    def read_logcat(self, tag, process_name, pattern, num=1):
        '''查找最近满足条件的一条log
        '''
        import re
        pat = re.compile(r'^\[(.+)\]\s+\[.+\]\s+\w/(.+)\(\s*\d+\):\s+(.+)$')
        log_pat = re.compile(pattern)
        log_list = self.adb.get_log(False)
        result_list = []
        k = 0
        for i in range(len(log_list) - 1, -1, -1):
            ret = pat.match(log_list[i])
            # print ret.group(1), ret.group(2), ret.group(3)
            if not process_name or ret.group(1) != process_name: continue
            if ret.group(2) != tag: continue
            if log_pat.search(ret.group(3)):
                if num == 1:
                    return ret.group(3)
                elif num == 0 or k < num:
                    k += 1
                    result_list.append(ret.group(3))
                else:
                    break
        return result_list

    def get_clipboard_text(self):
        '''获取剪切板内容
        '''
        result = self.adb.run_shell_cmd('sh %s/SpyHelper.sh getClipboardText' % (qt4a_path), True)
        return result.decode('raw-unicode-escape')
    
    def set_clipboard_text(self, text):
        '''设置剪贴板内容
        '''
        self.adb.run_shell_cmd('sh %s/SpyHelper.sh setClipboardText "%s"' % (qt4a_path, text.encode('raw-unicode-escape')), True)
    
    def is_screen_lock_enabled(self):
        '''屏幕锁是否可用
        '''
        return 'true' in self.adb.run_shell_cmd('sh %s/SpyHelper.sh isScreenLockEnabled' % (qt4a_path), True)
    
    def set_screen_lock_enable(self, enable=True):
        '''设置屏幕锁可用/不可用
        '''
        if enable: enable = 'true'
        else: enable = 'false'
        return 'true' in self.adb.run_shell_cmd('sh %s/SpyHelper.sh setScreenLockEnable %s' % (qt4a_path, enable), True)
    
    def is_screen_on(self):
        '''屏幕是否点亮
        '''
        return 'true' in self.adb.run_shell_cmd('sh %s/SpyHelper.sh isScreenOn' % (qt4a_path), True)
    
    def wake_screen(self, wake=True):
        '''唤醒屏幕
        '''
        try:
            ret = self._send_command('WakeScreen', Wake=wake)
        except RuntimeError, e:
            logger.warn('wake_screen error: %s' % e)
            if 'NullPointerException' in str(e):
                # 重启下系统测试桩
                self._restart_server()
                return self.wake_screen(wake)
        if not ret:
            logger.warn('wake screen failed')
            self.send_key(26)
            return not (self.is_screen_on() ^ wake)
        return True
        # return self.adb.run_shell_cmd('sh %s/SpyHelper.sh wakeScreen' % (qt4a_path), True) == 'true'
    
    def is_keyguard_locked(self):
        '''屏幕锁是否锁定
        '''
        return 'true' in self.adb.run_shell_cmd('sh %s/SpyHelper.sh isKeyguardLocked' % (qt4a_path), True)
    
    def _lock_keyguard(self):
        '''
        '''
        return self._send_command('LockKeyguard')
    
    def _unlock_keyguard(self):
        '''
        '''
        return self._send_command('UnlockKeyguard')
    
    def lock_keyguard(self):
        '''锁屏
        '''
        if not self.is_screen_lock_enabled():
            # 先设置为有屏幕锁
            self.set_screen_lock_enable(True)
        self._last_activity_before_lock = self._get_current_activity(True)  # 保存锁屏前的Activity
        logger.debug('锁屏前Activity为：%r' % self._last_activity_before_lock)
        ret = self._lock_keyguard()
        if not ret: 
            logger.warn('lock keyguard failed')
            self.wake_screen(False)
            time.sleep(1)
            self.wake_screen(True)
            return self.is_keyguard_locked()
        return True
    
    def _swipe_unlock_keyguard(self):
        '''滑动解锁
        '''
        width, height = self.screen_size
        x = width / 2
        y = height / 2
        x1 = width / 4
        x2 = width * 3 / 4
        y1 = height / 4
        y2 = height * 3 / 4
        action1 = (x, y2, x, y1)  # 上滑
        action2 = (x, y1, x, y2)  # 下滑
        action3 = (x1, y, x2, y)  # 右滑
        action4 = (x2, y, x1, y)  # 左滑
        for action in (action1, action2, action3, action4):
            logger.debug('drag %s' % str(action))
            self.drag(*action)
            time.sleep(1)
            if not self.is_keyguard_locked(): return True
        else:
            return False
                
    def unlock_keyguard(self):
        '''解锁屏幕
        '''
        old_activity = self._get_current_activity(True)
        ret = self._unlock_keyguard()
        timeout = 10
        time0 = time.time()
        while time.time() - time0 < timeout:
            current_activity = self.get_current_activity()
            if current_activity != 'Keyguard': 
                ret = not self.is_keyguard_locked()
                break
            # self._lock_keyguard()  # 解锁后再自动锁上需要先锁一次，再解锁才行
            ret = self._unlock_keyguard()
            time.sleep(1)
        else:
            return self._swipe_unlock_keyguard()
            # raise RuntimeError('屏幕解锁失败')
        if not ret: 
            for _ in range(2):
                self.send_key('{HOME}')  # 发送Home键可以让inKeyguardRestrictedInputMode返回false
                if not self.is_keyguard_locked(): 
                    if hasattr(self, '_last_activity_before_lock') and self._last_activity_before_lock: 
                        self.start_activity(self._last_activity_before_lock)
                        self._last_activity_before_lock = ''
                    elif old_activity != 'Keyguard':
                        from adb import TimeoutError
                        try:
                            self.start_activity(old_activity)
                        except TimeoutError, e:
                            logger.warn('start activity %s failed: %s' % (old_activity, e))
                    return True
                time.sleep(1)
            else:
                logger.warn('unlock keyguard failed')
                # 尝试滑动解锁
                return self._swipe_unlock_keyguard()
        return True

    def send_key(self, key):
        '''发送按键
        '''
        from util import KeyCode
        if isinstance(key, str):
            key = [str(item) for item in KeyCode.get_key_list(key)]
            key = ','.join(key)
        logger.debug('SendKey %s' % key)
        return self._send_command('SendKey', Keys=key)

    def clear_data(self, package_name):
        '''清理数据
        '''
        if not self.adb.get_package_path(package_name): return True
        return self.adb.run_shell_cmd('pm clear %s' % package_name).find('Success') >= 0

    def get_device_unique_id(self):
        '''获取设备唯一ID
        '''
        imei = self.adb.get_device_imei()
        if imei != 'null': return imei
        mac = self.adb.run_shell_cmd('sh %s/SpyHelper.sh getWlanMac' % qt4a_path)
        if mac != 'null': return mac.replace(':', '')
        raise RuntimeError('获取设备唯一ID失败')

    def is_app_installed(self, app_name):
        '''应用是否安装
        '''
        package_path = self.adb.get_package_path(app_name)
        return package_path != ''

    def _query_media_info(self, file_path):
        '''查询媒体文件信息
        '''
        result = self.adb.run_shell_cmd('sh %s/SpyHelper.sh getImageUri %s' % (qt4a_path, file_path), True)
        if not result or result.find('content://') < 0:
            logger.debug('getImageUri: %r' % result)
            return ''
            # raise RuntimeError('查询媒体信息失败：%s' % result)
        return result[result.find('content://'):]

    def _wait_for_media_available(self, file_path, timeout=120):
        '''等待媒体文件存储到数据库
        '''
        time0 = time.time()
        while time.time() - time0 < timeout:
            uri = self._query_media_info(file_path)
            if uri: return uri
            time.sleep(5)
        raise RuntimeError('等待媒体文件:%r 刷新超时' % file_path)

    def get_app_size(self, package_name):
        '''获取应用所占大小
        '''
        self.adb.kill_process('/system/bin/installd')  # 不杀死此进程会导致无法返回
        result = self.adb.run_shell_cmd('sh %s/SpyHelper.sh getPackageSizeInfo %s' % (qt4a_path, package_name), True)
        result = result.split('\r\n')[-1]
        result = result.split()
        return int(result[1]), int(result[2]), int(result[3])  # codeSize dataSize cacheSize

    def get_string_resource(self, pkg_name, string_id, lang=''):
        '''获取字符串资源
        '''
        result = self._send_command('GetStringResource', PkgName=pkg_name, Id=string_id, Lang=lang)
        if result == ("Can't find string %s" % string_id):
            if pkg_name == 'android': raise RuntimeError(result)
            return self.get_string_resource('android', string_id, lang)
        return result

    def get_string_resource_id(self, pkg_name, text, lang=''):
        '''获取字符串资源ID
        '''
        result = self._send_command('GetStringResourceId', PkgName=pkg_name, Text=text, Lang=lang)
        if not result:
            if pkg_name == 'android': return {}
            return self.get_string_resource_id('android', text, lang)  # 查找系统资源
        return result

    def set_default_language(self, lang):
        '''设置默认语言
        '''
        lang_dict = {'中文': 'zh',
                     '英文': 'en',
                     '阿拉伯文': 'ar',
                     '德文': 'de',
                     '西班牙文': 'es',
                     '法文': 'fr',
                     '意大利文': 'it',
                     '日文': 'ja',
                     '韩文': 'ko'
                     }  # 语言对应关系
        country_dict = {'中国': 'CN',
                        '香港': 'HK',
                        '台湾': 'TW',
                        '美国': 'US',
                        '英国': 'GB',
                        '澳大利亚': 'AU',
                        '加拿大': 'CA',
                        '爱尔兰': 'IE',
                        '印度': 'IN',
                        '新西兰': 'NZ',
                        '新加坡': 'SG',
                        '南非': 'ZA',
                        '意大利': 'IT',
                        '瑞士': 'CH',
                        '日本': 'JP',
                        '韩国': 'KR',
                        }  # 国家(地区)对应关系
        import re
        pattern = re.compile(r'(.+)\((.+)\)')
        if lang == '简体中文':
            lang = '中文(中国)'
        elif lang == '繁体中文':
            lang = '中文(台湾)'
        mat = pattern.match(lang)
        if mat:
            lang = '%s_%s' % (lang_dict[mat.group(1)], country_dict[mat.group(2)])
        else:
            # 没有地区
            lang = lang_dict[lang]
        self.adb.run_shell_cmd('sh %s/SpyHelper.sh updateLangConfig %s' % (qt4a_path, lang), True)
        # 重启测试桩进程，保证重新加载资源
        self.close()
    
    def get_system_timezone(self):
        '''获取当前系统时区
        '''
        return self.get_property('persist.sys.timezone')
    
    def set_system_timezone(self, new_timezone='Asia/Shanghai'):
        '''修改系统时区
        '''
        if self.get_system_timezone() != new_timezone:
            self.set_property('persist.sys.timezone', new_timezone)
            # 不发送广播仅影响系统时间显示,对应用没有影响
#             try:
#                 self.adb.run_shell_cmd('am broadcast -a android.intent.action.TIMEZONE_CHANGED', retry_count=1, timeout=10)  # 通知桌面程序时区发生变化
#             except TimeoutError:
#                 pass
            
    def set_system_time(self, new_time=None):
        '''设置系统时间
        '''
        if not new_time:
            new_time = time.strftime("%Y%m%d.%H%M%S", time.localtime())
        self.adb.run_shell_cmd('date -s %s' % new_time, True)

    def get_static_field_value(self, pkg_name, cls_name, field_name, field_type):
        '''获取类中静态变量的值
        
        :param pkg_name:   包名
        :type pkg_name:    string
        :param cls_name:   类名
        :type cls_name:    string
        :param field_name: 字段名
        :type field_name:  string 
        '''
        return self.adb.run_shell_cmd('sh %s/SpyHelper.sh getStaticFieldValue %s %s %s %s' % (qt4a_path, pkg_name, cls_name, field_name, field_type))

    def get_system_boot_time(self):
        '''获取系统启动时间，单位为秒
        '''
        for _ in range(3):
            ret = self.adb.run_shell_cmd('sh %s/SpyHelper.sh getSystemBootTime' % qt4a_path, True)
            if ret != '' and ret.isdigit(): return int(ret) / 1000
            logger.warn('getSystemBootTime return %r' % ret)
            time.sleep(2)
        return 0

    def get_battery_capacity(self):
        '''获取当前电池电量
        '''
        ret = self.adb.run_shell_cmd('cat /sys/class/power_supply/battery/capacity')
        if 'No such file or directory' in ret:
            # 魅族flyme3.0.2系统上
            ret = self.adb.run_shell_cmd('cat /sys/class/power_supply/fuelgauge/capacity')
        return int(ret)

    def get_available_data_storage(self):
        '''获取数据存储区可用空间
        '''
        return self.get_available_storage('/data')

    def get_available_external_storage(self):
        '''获取sdcard可用存储空间
        '''
        return int(self.adb.run_shell_cmd('sh %s/SpyHelper.sh getExternalAvailableStorage /data' % qt4a_path, True))

    def get_available_storage(self, dir_path):
        '''获取目录可用空间
        '''
        return int(self.adb.run_shell_cmd('sh %s/SpyHelper.sh getAvailableStorage %s' % (qt4a_path, dir_path), True))

    def clean_directory(self, dir_path, min_storage=100 * 1024 * 1024):
        '''清理目录文件
        此方法有些暴力，注意是否会对系统产生影响
        
        :param dir_path: 要清理的目录路径
        :type dir_path:  string
        :param min_storage: 清理目录保证的最小存储空间
        :type min_storage:  long
        '''
        current_storage = self.get_available_storage(dir_path)
        if current_storage >= min_storage: return
        dir_list, file_list = self.adb.list_dir(dir_path)
        for dir in dir_list:
            subfolder = dir_path + '/' + dir['name']
            if subfolder.startswith('/data/local'): continue  # 防止测试桩被删除
            if subfolder.startswith('/data/dalvik-cache'): continue  # 删除该文件夹系统会出现问题
            self.adb.delete_folder(subfolder)
            if self.get_available_storage(dir_path) >= min_storage: return
        for file in file_list:
            file_path = dir_path + '/' + file['name']
            self.adb.delete_folder(subfolder)
            if self.get_available_storage(dir_path) >= min_storage: return
    
    def get_default_app(self, action):
        '''获取默认App
        '''
        return self.adb.run_shell_cmd('sh %s/SpyHelper.sh getPreferedApp %s' % (qt4a_path, action), True)
    
    def set_default_app(self, action, new_app):
        '''设置默认应用
        
        :param action: 应用针对的类型，如：android.media.action.IMAGE_CAPTURE
        :type action:  String
        :param new_app:新的应用包名
        :type new_app: String
        '''
        ret = self.adb.run_shell_cmd('sh %s/SpyHelper.sh setPreferedApp %s %s' % (qt4a_path, action, new_app), True)
        if 'false' in ret:
            raise RuntimeError('设置默认应用：%s 失败，检查应用是否安装并具有处理：%s 操作的能力' % (new_app, action))
        return ret
    
    def clear_default_app(self, action):
        '''清除默认应用设置
        '''
        return 'true' in self.adb.run_shell_cmd('sh %s/SpyHelper.sh clearPreferedApp %s' % (qt4a_path, action), True)
    
    def has_gps(self):
        '''是否有GPS
        '''
        return 'true' in self.adb.run_shell_cmd('sh %s/SpyHelper.sh hasGPS' % qt4a_path)
    
    def get_camera_number(self):
        '''获取摄像头数目
        '''
        return int(self.adb.run_shell_cmd('sh %s/SpyHelper.sh getCameraNumber' % qt4a_path))
    
    def get_sim_card_state(self):
        '''获取sim卡状态
        '''
        return self.adb.run_shell_cmd('sh %s/SpyHelper.sh getSimCardState' % qt4a_path, True)
    
    def is_debug_package(self, package_name):
        '''是否是debug包
        '''
        ret = self.adb.run_shell_cmd('sh %s/SpyHelper.sh isDebugPackage %s' % (qt4a_path, package_name))
        if 'NameNotFoundException' in ret:
            raise RuntimeError('应用：%s 未安装' % package_name)
        return 'true' in ret
    
    def get_view_id(self, package_name, view_str_id):
        '''获取控件整型ID
        '''
        # ret = self.adb.run_shell_cmd('sh %s/SpyHelper.sh getViewId %s %s' % (qt4a_path, package_name, view_str_id))
        id_list = []  # 可能会存在多个整型ID（应用和android）
        for package_name in [package_name, 'android']:
            time0 = time.time()
            result = self._send_command('GetViewId', PkgName=package_name, StrId=view_str_id)
            if result > 0:
                logger.debug('get_view_id %s in %s use %s S, result=%d' % (view_str_id, package_name, time.time() - time0, result))
                id_list.append(result)
            else:
                if package_name == 'android' and len(id_list) == 0:
                    raise RuntimeError('控件ID：%s 不存在' % view_str_id)
        return id_list
    
    def get_resource_origin_name(self, package_name, res_type, confuse_name):
        '''获取资源原始名称
        '''
        time0 = time.time()
        result = self._send_command('GetResourceOriginName', PkgName=package_name, ResType=res_type, ConfuseName=confuse_name)
#         ret = self.adb.run_shell_cmd('sh %s/SpyHelper.sh getResourceOriginName %s %s %s' % (qt4a_path, package_name, res_type, confuse_name), True)
#         if 'not found' in ret:
#             logger.warn('get_resource_origin_name failed: %s' % ret)
#             return confuse_name
        logger.debug('get_resource_origin_name %s in %s use %s S, result=%s' % (confuse_name, package_name, time.time() - time0, result))
        return result
    
    def start_activity(self, activity_name, action='', type='', data_uri='', extra={}, wait=True):
        '''
        '''
        use_am = True

        for key in extra.keys():
            if isinstance(extra[key], (list, tuple)):
                use_am = False
                break
        if use_am: return self.adb.start_activity(activity_name, action, type, data_uri, extra, wait)
        
        param = {'Component': activity_name}
        if action: param['Action'] = action
        if type: param['Type'] = type
        if extra: param['FileUri'] = extra['android.intent.extra.STREAM']
        if isinstance(param['FileUri'], (list, tuple)):  # and len(param['FileUri']) > 10:
            # 使用Socket方式，命令行方式有参数长度限制
            result = self._send_command('StartActivity', **param)
            if not result in range(5):
                raise RuntimeError('启动%s失败：%s' % (activity_name, result))
        else:
            result = self.adb.run_shell_cmd('sh %s/SpyHelper.sh startActivity "%s"' % (qt4a_path, json.dumps(param).replace('"', r'\"')), True)  # 用转义方式在不同手机上可能会有问题
            if 'Error:' in result or 'Exception' in result:
                raise RuntimeError('启动%s失败：%s' % (activity_name, result))
    
    def play_sound(self, file_path):
        '''播放语音
        
        :param file_path: 音频文件路径
        '''
        from util import get_file_md5
        self.set_volume(50)  # 先设置音量
        file_ext = os.path.splitext(file_path)[-1]
        dst_path = '/data/local/tmp/%s%s' % (get_file_md5(file_path), file_ext)
        self.push_file(file_path, dst_path)
        return self._send_command('PlaySound', FilePath=dst_path)
    
    def set_volume(self, volume):
        '''设置音量
        '''
        self.adb.run_shell_cmd('sh %s/SpyHelper.sh setVolume %d' % (qt4a_path, int(volume)), True)
        
    def get_phone_contacts(self):
        '''获取手机联系人列表
        '''
        result = self._send_command('GetPhoneContacts')
        return json.loads(result)
        
    def add_phone_contacts(self, name, phone):
        '''添加手机联系人
        '''
        # self.start_activity('com.test.qt4amockapp/.ContactsManagerActivity', 'addPhoneContacts', extra={'name': name, 'phone_number': str(phone)}, wait=False)
        return 'true' in self._content_provider_patch_func(self.adb.run_shell_cmd)('sh %s/SpyHelper.sh addPhoneContacts "%s" "%s"' % (qt4a_path, name, phone), True)
    
    def del_phone_contacts(self, name):
        '''删除手机联系人
        '''
        # self.start_activity('com.test.qt4amockapp/.ContactsManagerActivity', 'delPhoneContacts', extra={'name': name}, wait=False)
        return 'true' in self._content_provider_patch_func(self.adb.run_shell_cmd)('sh %s/SpyHelper.sh delPhoneContacts "%s"' % (qt4a_path, name), True)

    def _content_provider_patch_func(self, func):
        '''解决4.0以下版本手机中访问ContentProvider的限制
        '''
        def wrap_func(*args, **kwargs):
            if self.sdk_version >= 16:
                return func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
                if 'java.lang.SecurityException' in result:
                    for _ in range(3):
                        ret = self.adb.run_shell_cmd('.%s/inject system_server' % qt4a_path, True, timeout=60, retry_count=1)
                        if 'Inject Success' in ret: break
                    result = func(*args, **kwargs)
                return result
        return wrap_func

    def is_shortcut_exist(self, package_name):
        '''判断快捷方式是否存在
        '''
        result = self._content_provider_patch_func(self.adb.run_shell_cmd)('sh %s/SpyHelper.sh isAppShortcutExist %s' % (qt4a_path, package_name), True)
        return 'true' in result
    
    def set_app_permission(self, package_name, perm_name, is_allowed=True):
        '''设置应用权限
        '''
        if self.sdk_version < 19: return False
        result = self.adb.run_shell_cmd('sh %s/SpyHelper.sh setAppPermission %s %s %s' % (qt4a_path, package_name, perm_name, 'true' if is_allowed else 'false'), True)
        return 'true' in result
    
    def modify_system_setting(self, type, name, value):
        '''修改系统设置
        
        :param type: 设置类型，一般为system
        :type type:  string
        :param name: 要设置的键值
        :type name:  string
        :param value:要设置的数值
        :type value: string/int
        '''
        result = self._content_provider_patch_func(self.adb.run_shell_cmd)('sh %s/SpyHelper.sh modifySystemSetting %s %s %s' % (qt4a_path, type, name, value), True)
        return 'true' in result
        
if __name__ == '__main__':
    device = AndroidDevice('') 
    
    
