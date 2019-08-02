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

'''Android设备驱动
'''

import json
import re
import os
import time
import six
from qt4a.androiddriver.adb import ADB
from qt4a.androiddriver.clientsocket import DirectAndroidSpyClient
from qt4a.androiddriver.util import SocketError, TimeoutError, QT4ADriverNotInstalled, KeyCode, logger

qt4a_path = '/data/local/tmp/qt4a'

def root_required(func):
    '''root权限装饰器
    '''
    def _wrap_func(self, *args, **kwargs):
        '''
        '''
        if not self.adb.is_rooted():
            raise RuntimeError('method %s need root device' % func.__name__)
        return func(self, *args, **kwargs)
    return _wrap_func

class DeviceDriver(object):
    '''Android设备驱动
    '''
    service_name = 'com.test.androidspy'
    service_port = 19862  # 部分机器只能使用TCP端口
    
    def __init__(self, adb):
        self._adb = adb
        self._device_id = adb.device_name
        self._is_local_device = ADB.is_local_device(self._device_id)
        self._client = None
        self._server_pid = 0
        self._timeout = 40

    def get_device_id(self):
        '''获取设备ID
        '''
        if not self._device_id:
            self._device_id = self.adb.run_shell_cmd('getprop ro.serialno')
        return self._device_id

    def run_driver_cmd(self, cmd, *args, **kwargs):
        '''执行驱动命令
        
        :param cmd:  命令
        :type  cmd:  string
        '''
        args = [('"%s"' % (it.replace('"', r'\"') if isinstance(it, str) else it)) for it in args]
        result = self.adb.run_shell_cmd('sh %s/SpyHelper.sh %s %s' % (qt4a_path, cmd, ' '.join(args)), **kwargs)
        if 'No such file or directory' in result:
            raise QT4ADriverNotInstalled('Please install QT4A driver first')
        return result

    def get_language(self):
        '''获取系统语言
        '''
        return self.run_driver_cmd('getLanguage')

    def get_country(self):
        '''获取国家
        '''
        return self.run_driver_cmd('getCountry')

    @property
    def adb(self):
        return self._adb

    @property
    def client(self):
        if self._client == None:
            # 运行SpyHelper.sh
            self._client = self.run_server()
            # self._client.pre_connect()
        return self._client
    
    def get_device_imei(self):
        '''获取设备imei号
        '''
        if self.adb.is_rooted():
            return self.run_driver_cmd('getDeviceImei', root=True)
        else:
            return self._send_command('GetDeviceImei')
                
    def is_package_installed(self, pkg_name, pkg_size, pkg_md5):
        '''安装包是否已安装
        
        :param pkg_name:  应用包名
        :type pkg_name:   string
        :param pkg_size:  安装包大小
        :type pkg_size:   int
        :param pkg_md5:   安装包md5
        :type pkg_md5:    string
        '''
        ret = self.run_driver_cmd('isPackageInstalled', pkg_name, pkg_size, pkg_md5, root=self.adb.is_rooted())
        return 'true' in ret
    
    def install_package(self, pkg_path, overwrite=False):
        '''安装应用
        '''
        from qt4a.androiddriver.util import get_file_md5
        if not os.path.exists(pkg_path):
            raise RuntimeError('APK: %r not exist' % pkg_path)
        
        pkg_size = os.path.getsize(pkg_path)
        pkg_md5 = get_file_md5(pkg_path)
        pkg_name = ADB._get_package_name(pkg_path)
        if self.is_package_installed(pkg_name, pkg_size, pkg_md5):
            logger.info('APP %s [%d]%s is installed' % (pkg_name, pkg_size, pkg_md5))
            return True
        
        self.adb.install_apk(pkg_path, overwrite)
        return True
    
    def kill_process(self, package_name):
        '''杀死进程
        '''
        try:
            self.run_driver_cmd('killProcess', package_name, root=self.adb.is_rooted())
        except RuntimeError as e:
            logger.warn('killProcess error: %r' % e)
        if not self.adb.is_rooted(): return
        for _ in range(3):
            ret = self.adb.kill_process(package_name)
            if ret == None: return True
            elif ret == False: return False
        return False

    def get_external_sdcard_path(self):
        '''获取外置SD卡路径
        '''
        return self.run_driver_cmd('getExternalStorageDirectory', root=self.adb.is_rooted())

    def refresh_media_store(self, file_path=''):
        '''刷新图库，显示新拷贝到手机的图片
        '''
        from qt4a.androiddriver.adb import TimeoutError
        command = ''
        if not file_path:
            if hasattr(self, '_last_refresh_all') and time.time() - self._last_refresh_all < 2 * 60:
                logger.warn('[DeviceDriver] 120S内不允许全盘重复刷新')
                return
            sdcard_path = self.get_external_sdcard_path()
            command = 'am broadcast -a android.intent.action.MEDIA_MOUNTED --ez read-only false -d file://%s' % sdcard_path
            self._last_refresh_all = time.time()
        else:
            if file_path.startswith('/sdcard/'):
                file_path = self.get_external_sdcard_path() + file_path[7:]
            command = 'am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://%s' % file_path
        try:
            self.adb.run_shell_cmd(command, self.adb.is_rooted())
        except TimeoutError:
            logger.exception('refresh_media_store failed')
            return False
        # self.adb.run_shell_cmd('am broadcast -a android.intent.action.BOOT_COMPLETED')
        if file_path and self.adb.get_sdk_version() >= 16:
            return self._wait_for_media_available(file_path)
    
    def _get_current_activity(self, has_package_name=False):
        '''获取当前Activity
        '''
        if has_package_name: has_package_name = 'true'
        else: has_package_name = 'false'
        ret = self.run_driver_cmd('getCurrentActivity', has_package_name, root=self.adb.is_rooted())
        return ret.strip().split('\n')[-1]
    
    def _get_current_window(self):
        '''使用dumpsys命令获取当前窗口
        '''
        result = self.adb.run_shell_cmd('dumpsys window windows')
        if result:
            line_list = result.split('\n')
            for line in line_list:
                if 'mCurrentFocus' in line:
                    result = line
                    break
        pattern = re.compile(r'mCurrentFocus=Window{(.+)}')
        ret = pattern.search(result)
        if not ret:
            logger.info('Get current window by dumpsys failed: %s' % result)
            return None
        result = ret.group(1).split(' ')[-1]
        if '/' in result: result = result.split('/')[-1]
        if 'Application Not Responding' in ret.group(1):
            result = 'Application Not Responding: %s' % result
        return result
    
    def get_current_activity(self):
        '''获取当前窗口
        '''
        timeout = 10
        time0 = time.time()
        result = None
        while time.time() - time0 < timeout:
            if not self.adb.is_rooted():
                result = self._get_current_window()
            else:
                try:
                    result = self._send_command('GetCurrentWindow')
                except SocketError as e:
                    raise e
                except RuntimeError as e:
                    logger.warn('GetCurrentWindow error: %s' % e)
            if not result or result == 'null':
                # 一般是设备黑屏之类
                time.sleep(0.5)
                continue
            return result
        
        if not self.adb.is_rooted(): return None
        
        logger.warn('GetCurrentWindow failed')
        return self._send_command('GetCurrentActivity')

    def get_screen_size(self):
        '''获取屏幕大小
        '''
        if self.adb.is_rooted():
            result = self._send_command('GetScreenSize')  # 使用Socket方式可能会出现获取到结果一直为0的情况
            if isinstance(result, dict) and result['Width'] > 0 and result['Height'] > 0:
                return result['Width'], result['Height']
            
        result = self.run_driver_cmd('getScreenSize', root=self.adb.is_rooted())
        result = result.split('\n')[-1]
        width, height = result.split(',')
        return int(width), int(height)
    
    def take_screen_shot(self, path, quality=90):
        '''截屏
        '''
        result = self.adb.run_shell_cmd('%s/screenshot capture -q %s' % (qt4a_path, quality), binary_output=True)
        # 为避免pull文件耗时，直接写到stdout
        if len(result) < 256:
            logger.warn('Take screenshot failed: %s' % result)
            return False
        with open(path, 'wb') as fp:
            fp.write(result)
        return True

    def drag(self, x1, y1, x2, y2, count=5, wait_time=40, send_down_event=True, send_up_event=True):
        '''在屏幕上拖拽
        '''
        if self.adb.is_rooted():
            self.client.send_command('Drag', X1=x1, Y1=y1, X2=x2, Y2=y2, StepCount=count, SleepTime=wait_time, SendDownEvent=send_down_event, SendUpEvent=send_up_event)
        else:
            # TODO: 改为访问QT4A助手服务进程
            self.run_driver_cmd('drag', x1, y1, x2, y2, count, wait_time, send_down_event, send_up_event)
            
    def _kill_server(self):
        '''杀死Server进程，用于Server卡死时
        '''
        if self.adb.is_rooted():
            return self.adb.kill_process(self.service_name + ':service')
        else:
            return self.adb.stop_service(self.service_name + '/.service.HelperService')
        
    def _server_opend(self):
        '''判断测试桩进程是否运行
        '''
        process_name = self.service_name + ':service'
        pid = self.adb.get_pid(process_name)
        if pid != 0 and pid != self._server_pid:
            logger.info('[DeviceDriver] %s pid is %d' % (process_name, pid))
        self._server_pid = pid
        return pid > 0

    def _run_server(self, server_name):
        '''运行系统测试桩
        '''
        if not self.adb.is_rooted():
            try:
                self.adb.start_service('%s/.service.HelperService' % server_name, {'serviceName': server_name})
            except RuntimeError:
                logger.warn('start helper server failed')
                self.adb.start_activity('%s/.activity.StartServiceActivity' % server_name, extra={'serviceName': 'HelperService'}, wait=False)
                time.sleep(1)
            return self._server_opend()
        
        timeout = 10
        time0 = time.time()
        while time.time() - time0 < timeout:
            try:
                ret = self.run_driver_cmd('runServer', server_name, root=self.adb.is_rooted(), retry_count=1, timeout=10)
                logger.debug('Run server %s' % ret)
                if 'service run success' in ret:
                    # wait for parent process exit
                    time.sleep(0.5)
                elif 'service is running' in ret:
                    pass
                elif 'java.lang.UnsatisfiedLinkError' in ret:
                    raise RuntimeError('启动系统测试桩进程失败：\n%s' % ret)
            except TimeoutError as e:
                logger.warn('Run server timeout: %s' % e)
            
            if self._server_opend(): return True
            time.sleep(1)
        return False

    def _create_client(self, server_name, server_type):
        '''创建Client实例
        '''
        sock = self._adb.create_tunnel(server_name, server_type)
        if sock == None: return None
        return DirectAndroidSpyClient(sock, False, timeout=360)
    
    def run_server(self, server_name=''):
        '''运行测试桩进程,创建服务端
        '''
        if server_name == '': server_name = self.service_name
        from qt4a.androiddriver.androiddriver import AndroidDriver
        port = AndroidDriver.get_process_name_hash(server_name, self.get_device_id())
        logger.info('[DeviceDriver] port is %d' % port)
        addr = '127.0.0.1'
        if not self._is_local_device: addr = self.adb.host_name
        if self._client: self._client.close()
        self._client = None
        
        server_type = 'localabstract'
        if self.adb.is_rooted() and self.adb.is_selinux_opened():
            # 创建TCP服务端
            server_name = str(self.service_port)
            server_type = 'tcp'

        time0 = time.time()
        timeout = 20
        
        while time.time() - time0 < timeout:
            self._client = self._create_client(server_name, server_type)
            if self._client: return self._client
            ret = self._run_server(server_name)
            logger.debug('[DeviceDriver] Server %s process created: %s' % (server_name, ret))
            time.sleep(0.1)
        raise RuntimeError('连接系统测试桩超时')
    
    def _restart_server(self):
        '''重启系统测试桩
        '''
        if self._client:
            self._client.close()
            self._client = None
        self._kill_server()
        self.run_server()
        
    def _send_command(self, cmd_type, **kwds):
        '''发送命令
        '''
        result = self.client.send_command(cmd_type, **kwds)
        if result == None:
            logger.error('系统测试桩连接错误')
            self._kill_server()
            if self._client: self._client.close()
            self._client = None
            return self._send_command(cmd_type, **kwds)
            # raise SocketError('Socket连接错误')
        if 'Error' in result:
            raise RuntimeError(result['Error'])
        if not 'Result' in result:
            raise RuntimeError('%s返回结果错误：%s' % (cmd_type, result))
        return result['Result']

    def hello(self):
        '''
        '''
        result = self._client.hello()
        if result == None: return
        if not 'Result' in result:
            logger.warn('[DeviceDriver] no Result in hello rsp')
            raise RuntimeError('Server error')
        logger.info('[DeviceDriver] %s' % result['Result'])
        items = result['Result'].split(':')

        if len(items) > 0 and items[-1].isdigit():
            if self._server_pid == 0:
                logger.warn('[DeviceDriver] Server pid is 0')
            elif self._server_pid != 0 and int(items[-1]) != self._server_pid:
                logger.warn('[DeviceDriver] Server pid not match: %s' % (int(items[-1])))
                raise RuntimeError('Server error %s' % result['Result'])
        return result
    
    def close(self):
        if self._client != None:
            self._client.send_command('Exit')
            self._client = None

    def reboot(self, wait_cpu_low=True, usage=20, duration=10, timeout=120):
        '''重启手机
        
        :param wait_cpu_low:   是否等待CPU使用率降低
        :type wait_cpu_low:    bool
        :param usage:          cpu使用率阈值
        :type  usage:          int
        :param duration:       持续时间(秒)
        :type  duration:       int
        :param timeout:        超时时间，超市时间到后，无论当前CPU使用率是多少，都会返回
        :type  timeout:        int
        '''
        pattern = re.compile(r'^.+:\d+$')
        try:
            ret = self.run_driver_cmd('reboot', root=self.adb.is_rooted(), retry_count=1, timeout=30)
            if ret == 'false': return
        except RuntimeError as e:
            logger.warn('reboot: %r' % e)
            if pattern.match(self._device_id):
                try:
                    self.adb.reboot(60)
                except RuntimeError:
                    logger.warn('reboot: %s' % e)
                    # 虚拟机会出现明明重启成功却一直不返回的情况
            else:
                self.adb.reboot(0)  # 不能使用reboot shell命令，有些手机需要root权限才能执行

        time.sleep(10)  # 防止设备尚未关闭，一般重启不可能在10秒内完成
        self._adb.wait_for_boot_complete()
        # self._adb = None  # 重启后部分属性可能发生变化,需要重新实例化

        if wait_cpu_low == True:
            self.wait_for_cpu_usage_low(usage, duration, timeout)

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
            cpu_usage = self._adb.get_cpu_usage()
            # print (cpu_usage)
            if cpu_usage > usage :
                time1 = time.time()
            if time.time() - time1 > duration:
                break
            time.sleep(1)

    def connect_wifi(self, wifi_name, wifi_pass=''):
        '''连接指定的Wifi
        '''
        if not self.adb.is_rooted():
            return self._send_command('ConnectWifi', WifiName=wifi_name)
        else:
            result = self.run_driver_cmd('connectWifi', wifi_name, wifi_pass, root=True, timeout=60)
            if not 'true' in result:
                logger.debug('Connect wifi result: %s' % result)
                return False
            return True
        
    def disable_wifi(self):
        '''禁用Wifi
        '''
        return self._send_command('DisableWifi')

    def enable_data_connection(self):
        '''启用数据连接
        '''
        result = self.run_driver_cmd('setDataConnection', 'true', root=self.adb.is_rooted(), timeout=60)
        if not 'true' in result:
            sim_state = self.get_sim_card_state()
            if 'SIM_STATE_ABSENT' in sim_state or 'SIM_STATE_UNKNOWN' in sim_state:
                raise RuntimeError('设备中没有SIM卡')
            raise RuntimeError('启用数据连接失败:%r' % result)
        return True

    def disable_data_connection(self):
        '''禁用数据连接
        '''
        result = self.run_driver_cmd('setDataConnection', 'false', root=self.adb.is_rooted(), timeout=60)
        if not 'true' in result:
            raise RuntimeError('禁用数据连接失败: %r' % result)
        return True

    def get_clipboard_text(self):
        '''获取剪切板内容
        '''
        result = self.run_driver_cmd('getClipboardText', root=self.adb.is_rooted())
        if six.PY2:
            return result.decode('raw-unicode-escape')
        return result
    
    def set_clipboard_text(self, text):
        '''设置剪贴板内容
        '''
        if six.PY2:
            text = text.encode('raw-unicode-escape')
        self.run_driver_cmd('setClipboardText', text, root=self.adb.is_rooted())
    
    @root_required
    def is_screen_lock_enabled(self):
        '''屏幕锁是否可用
        6.0以下需要系统权限：You either need MANAGE_USERS or CREATE_USERS permission to: query users
        '''
        return 'true' in self.run_driver_cmd('isScreenLockEnabled', root=True)
    
    @root_required
    def set_screen_lock_enable(self, enable=True):
        '''设置屏幕锁可用/不可用
        '''
        if enable: enable = 'true'
        else: enable = 'false'
        return 'true' in self.run_driver_cmd('setScreenLockEnable', enable, root=True)
        
    def is_screen_on(self):
        '''屏幕是否点亮
        '''
        return 'true' in self.run_driver_cmd('isScreenOn', root=self.adb.is_rooted())
    
    def wake_screen(self, wake=True):
        '''唤醒屏幕
        '''
        if self.is_screen_on() == wake: return True
        if self.adb.is_rooted():
            self.send_key(KeyCode.KEYCODE_POWER)
        else:
            return 'true' in self.run_driver_cmd('wakeScreen', 'true' if wake else 'false')
        return True
    
    def is_keyguard_locked(self):
        '''屏幕锁是否锁定
        '''
        return 'true' in self.run_driver_cmd('isKeyguardLocked', root=self.adb.is_rooted())
    
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
        if self.is_keyguard_locked(): return True  # 已经是锁屏状态
        if self.adb.is_rooted():
            self.set_screen_lock_enable(True)
        if self.adb.get_sdk_version() >= 16:
            # 发送电源键
            self.send_key(KeyCode.KEYCODE_POWER)
            return True
        
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
    
    def _unlock_keyguard_ge_16(self):
        '''4.1以上使用APP方式解锁
        '''
        self.adb.start_activity('com.test.androidspy/.activity.UnlockKeyguardActivity', wait=False)
        time.sleep(1)
        return True
        
    def unlock_keyguard(self):
        '''解锁屏幕
        '''
        if self.adb.is_rooted():
            if not self.is_keyguard_locked(): return True
            self.set_screen_lock_enable(False)
        if not self.is_keyguard_locked(): return True
        
        if self.adb.get_sdk_version() >= 16:
            self._unlock_keyguard_ge_16()
        else:
            # 使用接口解锁
            if self._unlock_keyguard(): return True
            old_activity = self._get_current_activity(True)
            logger.debug('before send HOME is %s' % old_activity)
            self.send_key(KeyCode.KEYCODE_HOME)

        return True

    def send_key(self, keys):
        '''发送按键
        '''
        if isinstance(keys, str):
            for item in KeyCode.get_key_list(keys):
                self.send_key(item)
            return
        elif isinstance(keys, list):
            # 组合键
            keys = [str(item) for item in keys]
            keys = ','.join(keys)
            
        if self.adb.is_rooted():
            logger.debug('SendKey %s' % keys)
            return self._send_command('SendKey', Keys=keys)
        else:
            return 'true' in self.run_driver_cmd('sendKey', keys)

    def get_mac_address(self):
        '''获取设备mac地址
        '''
        mac = self.run_driver_cmd('getWlanMac')
        if mac != 'null': return mac.replace(':', '')
        return None

    def _query_media_info(self, file_path):
        '''查询媒体文件信息
        '''
        result = self.run_driver_cmd('getMediaUri', file_path, root=self.adb.is_rooted())
        logger.debug('Get media uri result: %s' % result)
        if not result or 'content://' not in result:
            return ''
        return result[result.find('content://'):]

    def _wait_for_media_available(self, file_path, timeout=180):
        '''等待媒体文件存储到数据库
        '''
        time0 = time.time()
        while time.time() - time0 < timeout:
            uri = self._query_media_info(file_path)
            if uri: return uri
            time.sleep(5)
        raise RuntimeError('等待媒体文件:%r 刷新超时' % file_path)

    def get_string_resource(self, pkg_name, string_id, lang=''):
        '''获取字符串资源
        '''
        result = self._send_command('GetStringResource', PkgName=pkg_name, Id=string_id, Lang=lang)
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
        
        pattern_lang = re.compile(r'^[a-z]{2}_[A-Z]{2}$')
        if not pattern_lang.match(lang):
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
        self.run_driver_cmd('updateLangConfig', lang, root=self.adb.is_rooted())
        # 重启测试桩进程，保证重新加载资源
        self._restart_server()

    def get_static_field_value(self, pkg_name, cls_name, field_name, field_type):
        '''获取类中静态变量的值
        
        :param pkg_name:   包名
        :type pkg_name:    string
        :param cls_name:   类名
        :type cls_name:    string
        :param field_name: 字段名
        :type field_name:  string 
        '''
        return self.run_driver_cmd('getStaticFieldValue', pkg_name, cls_name, field_name, field_type)

    def get_system_boot_time(self):
        '''获取系统启动时间，单位为秒
        '''
        for _ in range(3):
            ret = self.run_driver_cmd('getSystemBootTime', root=self.adb.is_rooted())
            if ret and ret.isdigit(): return int(ret / 1000)
            logger.warn('getSystemBootTime return %r' % ret)
            time.sleep(2)
        return 0

    def get_available_storage(self, path):
        '''获取分区可用存储空间
        '''
        return int(self.run_driver_cmd('getAvailableStorage', path, root=self.adb.is_rooted()))

    @root_required
    def get_default_app(self, action):
        '''获取默认App
        '''
        return self.run_driver_cmd('getPreferedApp', action, root=True)
    
    @root_required
    def set_default_app(self, action, type, new_app):
        '''设置默认应用
        
        :param action: 应用针对的类型，如：android.media.action.IMAGE_CAPTURE
        :type action:  String
        :param new_app:新的应用包名
        :type new_app: String
        '''
        ret = self.run_driver_cmd('setPreferedApp', action, type, new_app, root=True)
        if 'false' in ret:
            raise RuntimeError('设置默认应用：%s 失败，检查应用是否安装并具有处理：%s 操作的能力' % (new_app, action))
        return ret
    
    @root_required
    def clear_default_app(self, action, type=''):
        '''清除默认应用设置
        需要android.permission.SET_PREFERRED_APPLICATIONS权限，只有系统应用可以获取
        '''
        return 'true' in self.run_driver_cmd('clearPreferedApp', action, type, root=True)

    def has_gps(self):
        '''是否有GPS
        '''
        return 'true' in self.run_driver_cmd('hasGPS')
    
    def get_camera_number(self):
        '''获取摄像头数目
        '''
        return int(self.run_driver_cmd('getCameraNumber', root=self.adb.is_rooted()))

    def is_debug_package(self, package_name):
        '''是否是debug包
        '''
        ret = self.run_driver_cmd('isDebugPackage', package_name, root=self.adb.is_rooted())
        logger.info('isDebugPackage ret: %s' % ret)
        if 'NameNotFoundException' in ret:
            raise RuntimeError('APP: %s not installed' % package_name)
        return 'true' in ret
    
    def get_view_id(self, package_name, view_str_id):
        '''获取控件整型ID
        '''
        id_list = []  # 可能会存在多个整型ID（应用和android）
        for package_name in [package_name, 'android']:
            time0 = time.time()
            result = self._send_command('GetViewId', PkgName=package_name, StrId=view_str_id)
            if result > 0:
                logger.debug('get_view_id %s in %s use %s S, result=%d' % (view_str_id, package_name, time.time() - time0, result))
                id_list.append(result)
            else:
                if package_name == 'android' and len(id_list) == 0:
                    raise RuntimeError('View id: %s not exist' % view_str_id)
        return id_list
    
    def get_resource_origin_name(self, package_name, res_type, confuse_name):
        '''获取资源原始名称
        '''
        time0 = time.time()
        result = self._send_command('GetResourceOriginName', PkgName=package_name, ResType=res_type, ConfuseName=confuse_name)
        logger.debug('get_resource_origin_name %s in %s use %s S, result=%s' % (confuse_name, package_name, time.time() - time0, result))
        return result
    
    def start_activity(self, params):
        '''使用系统测试桩启动Activity
        '''
        if isinstance(params['FileUri'], (list, tuple)):  # and len(param['FileUri']) > 10:
            # 使用Socket方式，命令行方式有参数长度限制
            result = self._send_command('StartActivity', **params)
            if not result in range(5):
                raise RuntimeError('Start activity %s failed: %s' % (activity_name, result))
        else:
            result = self.run_driver_cmd('startActivity', json.dumps(param), root=self.adb.is_rooted())
            if 'Error:' in result or 'Exception' in result:
                raise RuntimeError('Start activity %s failed: %s' % (activity_name, result))
    
    def play_sound(self, file_path):
        '''播放语音
        
        :param file_path: 音频文件在手机中的路径
        '''
        return self._send_command('PlaySound', FilePath=file_path)
    
    def set_volume(self, volume):
        '''设置音量
        '''
        self.run_driver_cmd('setVolume', int(volume), root=self.adb.is_rooted())
        
    def get_phone_contacts(self):
        '''获取手机联系人列表
        '''
        result = self._send_command('GetPhoneContacts')
        return json.loads(result)
        
    def add_phone_contacts(self, name, phone):
        '''添加手机联系人
        '''
        return 'true' in self._content_provider_patch_func(self.run_driver_cmd)('addPhoneContacts', name, phone, root=self.adb.is_rooted())
    
    def del_phone_contacts(self, name):
        '''删除手机联系人
        '''
        return 'true' in self._content_provider_patch_func(self.run_driver_cmd)('delPhoneContacts', name, root=self.adb.is_rooted())

    def _content_provider_patch_func(self, func):
        '''解决4.0以下版本手机中访问ContentProvider的限制
        '''
        def wrap_func(*args, **kwargs):
            if self.adb.get_sdk_version() >= 16:
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
        result = self._content_provider_patch_func(self.run_driver_cmd)('isAppShortcutExist', package_name, root=self.adb.is_rooted())
        return 'true' in result
    
    def set_app_permission(self, package_name, perm_name, is_allowed=True):
        '''设置应用权限
        '''
        if self.adb.get_sdk_version() < 19: return False
        result = self.run_driver_cmd('setAppPermission', package_name, perm_name, 'true' if is_allowed else 'false', root=self.adb.is_rooted())
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
        result = self._content_provider_patch_func(self.run_driver_cmd)('modifySystemSetting', type, name, value, root=self.adb.is_rooted())
        return 'true' in result
    
    def is_vpn_connected(self):
        '''VPN是否连接
        '''
        result = self.run_driver_cmd('isVpnConnected')
        return 'true' in result
    
    def connect_vpn(self, vpn_type, server, username, password):
        '''连接VPN
        
        :param vpn_type:  VPN类型
        :type vpn_type:   int
        :param server:    服务器地址
        :type server:     string
        :param username:  用户名
        :type username:   string
        :param password:  密码
        :type password:   string
        '''
        result = self.run_driver_cmd('connectVpn', vpn_type, server, username, password, root=self.adb.is_rooted())
        return 'true' in result
    
    def disconnect_vpn(self):
        '''断开VPN
        '''
        result = self.run_driver_cmd('disconnectVpn', root=self.adb.is_rooted())
        return 'true' in result
    
    def end_call(self):
        '''挂断电话
        '''
        result = self.run_driver_cmd('endCall', root=self.adb.is_rooted())
        return 'true' in result
    
    def grant_all_runtime_permissions(self, package_name):
        '''给APP授予所有运行时权限
        '''
        result = self.run_driver_cmd('grantAllRuntimePermissions', package_name, root=self.adb.is_rooted())
        return not 'null' in result

    def resolve_domain(self, domain):
        '''解析域名
        '''
        result = self.run_driver_cmd('resolveDomain', domain, root=self.adb.is_rooted())
        return result.strip()

    def set_radio_enabled(self, enable):
        '''是否启用Radio
        '''
        return 'true' in self.run_driver_cmd('setRadioEnabled', 'true' if enable else 'false', root=self.adb.is_rooted())
    
    def set_http_proxy(self, host, port):
        '''设置http代理
        '''
        return 'true' in self.run_driver_cmd('setHttpProxy', host if host else '', port if port else '', root=self.adb.is_rooted())
    
    def connect_screenshot_service(self):
        '''连接截屏服务
        '''
        timeout = 10
        time0 = time.time()
        screenshot_service_name = 'qt4a_screenshot'
        while time.time() - time0 < timeout:
            sock = self.adb.create_tunnel(screenshot_service_name, 'localabstract')
            if sock: return sock
            self.adb.run_shell_cmd('%s/screenshot runserver -d' % qt4a_path)
        else:
            raise RuntimeError('start screenshot service failed')
    
    def unzip_file(self, zip_file, save_dir):
        '''解压文件
        
        :param zip_file: 压缩文件路径
        :type  zip_file: string
        :param save_dir: 保存目录路径
        :type  save_dir: string
        '''
        result = self.run_driver_cmd('unzip', zip_file, save_dir)
        return 'true' in result

if __name__ == '__main__':
    pass
