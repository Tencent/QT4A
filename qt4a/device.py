# -*- coding=utf8 -*-
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
'''
Android 设备模块
'''
# 2013/11/19 cherry created
# 2013/11/21 apple 将AndroidDevice中的接口挪到Device类中
# 2013/11/25 apple 添加PerformDevice类，允许性能测试通过环境变量传递要使用的设备ID

import os
import time

class Device(object):
    '''Android设备类，封装Android的设备操作
    '''
    # 2013/11/19 cherry created

    device_list = []  # 已申请设备列表

    def __init__(self, device_id=None, attrs={}):
        '''获取一个Android设备，获取成功后则独占该设备。
        
        :param device_id: 获取制定设备id的Android设备。如果为空则任意获取一台空闲设备。
        '''
        # 2014/09/26 banana 增加等待设备的时间
        
        from androiddriver.androiddevice import AndroidDevice
        device_id_list = [device.device_id for device in self.device_list]
        self._device = None

        if device_id:
            self._device = AndroidDevice(device_id)
            self.device_list.append(self)  # 需要单独释放
            return

        local_device_list = self.get_available_device_list()
        if local_device_list:
            for device in self.get_available_device_list():
                if device.device_id in device_id_list: continue
                if device_id and device_id != device.device_id: continue
                self._device = device
                self.device_list.append(self)
                return

        if not self._device: raise RuntimeError('设备%s申请失败' % (': %s' % device_id if device_id else ''))

    def __del__(self):
        '释放设备'
        pass

    @staticmethod
    def release_all_device():
        '''释放所有设备
        '''
        Device.device_list = []

    @staticmethod
    def get_available_device_list():
        '''获取本地可用设备列表
        '''
        from androiddriver.adb import ADB
        from androiddriver.androiddevice import AndroidDevice
        remote_device_list = []
        device_list = ADB.list_device() + remote_device_list
        _device_list = []
        for device, state in device_list:
            if state != 'device': continue
            if device.startswith('emulator-'): continue  # TODO: adb会自动连接5555-5585端口
            _device_list.append(AndroidDevice.get_instance(device))

        import random
        random.shuffle(_device_list)  # 可以随机取设备
        return _device_list

    @property
    def device_id(self):
        '''设备ID
        '''
        return self._device.device_id
    
    @property
    def device_host(self):
        '''设备主机
        '''
        if self.is_remote_device():
            return self.adb.host_name
        else:
            return '127.0.0.1'
        
    @property
    def cpu_type(self):
        '''cpu类型
        '''
        return self._device.cpu_type

    @property
    def imei(self):
        '''手机串号
        '''
        if not hasattr(self, '_imei'):
            self._imei = self._device.imei
        return self._imei

    @property
    def module(self):
        '''设备型号
        '''
        return self._device.module

    @property
    def system_version(self):
        '''系统版本
        '''
        return self._device.system_version

    @property
    def sdk_version(self):
        '''SDK版本
        '''
        return self._device.sdk_version

    @property
    def screen_size(self):
        '''屏幕大小
        '''
        return self._device.screen_size

    @property
    def language(self):
        '''语言
        '''
        return self._device.language

    @property
    def country(self):
        '''国家
        '''
        return self._device.country
    
    @property
    def current_activity(self):
        '''当前Activity
        '''
        return self.get_current_activity()
    
    @property
    def adb(self):
        return self._device.adb

    def __str__(self):
        return str(self._device)

    def is_remote_device(self):
        '''是否是远程设备
        '''
        return self._device.is_remote_device()

    def is_virtual_device(self):
        '''是否是虚拟机
        '''
        return 'genymobile' in self.run_shell_cmd('getprop ro.build.host')
    
    def run_shell_cmd(self, cmd, *argv, **kwds):
        '''执行adb shell命令
        '''
        return self._device.adb.run_shell_cmd(cmd, *argv, **kwds)

    def start_activity(self, activity_name, action='', type='', data_uri='', extra={}, wait=True):
        '''启动activity
        '''
        return self._device.start_activity(activity_name, action, type, data_uri, extra, wait)

    def install_package(self, pkg_path, pkg_name, overwrite=False):
        '''安装应用
        
        :param pkg_path: 安装包路径
        :type pkg_path:  string
        :param pkg_name: 应用包名
        :type pkg_name:  string
        :param overwrite:是否是覆盖安装
        :type overwrite: bool
        '''
        return self._device.install_package(pkg_path, pkg_name, overwrite)

    def kill_process(self, package_name):
        '''杀死进程
        
        :param package_name: 应用包名
        :type package_name: string
        '''
        return self._device.kill_process(package_name)

    def push_file(self, src_path, dst_path):
        '''向手机中拷贝文件
        
        :param src_path: PC上的源路径
        :type src_path:  string
        :param dst_path: 手机上的目标路径
        :type dst_path:  string
        '''
        return self._device.push_file(src_path, dst_path)

    def push_dir(self, src_path, dst_path):
        '''向手机中拷贝文件夹
        
        :param src_path: PC上的源目录路径
        :type src_path:  string
        :param dst_path: 手机上的目的目录路径
        :type dst_path:  string
        '''
        return self._device.push_dir(src_path, dst_path)

    def pull_file(self, src_path, dst_path):
        '''将手机中的文件拷贝到PC中
        
        :param src_path: 手机中的源路径
        :type src_path:  string
        :param dst_path: PC中的目的路径
        :type dst_path:  string
        '''
        return self._device.pull_file(src_path, dst_path)
    
    def pull_dir(self, src_path, dst_path):
        '''从手机中拷贝文件夹到PC
        
        :param src_path: 手机上的源目录路径
        :type src_path:  string
        :param dst_path: PC上的目的目录路径
        :type dst_path:  string
        '''
        return self._device.pull_dir(src_path, dst_path)
    
    def list_dir(self, dir_path):
        '''列取目录
        '''
        return self._device.adb.list_dir(dir_path)
    
    def is_file_exists(self, file_path):
        '''判断文件或目录是否存在
        '''
        try:
            self.list_dir(file_path)
            return True
        except RuntimeError:
            return False
        
    def delete_folder(self, folder_path):
        '''删除文件夹
        
        :param folder_path: 手机中的文件夹路径
        :type folder_path:  string
        '''
        return self._device.delete_folder(folder_path)

    def delete_file(self, file_path):
        '''删除文件
        '''
        return self._device.adb.delete_file(file_path)

    def mkdir(self, dir_path):
        '''创建目录
        '''
        return self._device.adb.mkdir(dir_path)
    
    def copy_file(self, src_path, dst_path):
        '''设备内复制文件
        
        :param src_path: 源路径
        :type src_path:  string
        :param dst_path: 目标路径
        :type dst_path:  string
        '''
        if not self.is_file_exists(src_path):
            raise RuntimeError('文件:%s 不存在' % src_path)
        self._device.adb.copy_file(src_path, dst_path)
        
    def get_external_sdcard_path(self):
        '''获取外置SD卡路径
        '''
        return self._device.get_external_sdcard_path()

    def refresh_media_store(self, file_path=''):
        '''刷新图库，显示新拷贝到手机的图片
        '''
        return self._device.refresh_media_store(file_path)

    def get_process_meminfo(self, process_name):
        '''获取进程内存信息
        
        :param process_name: 进程名
        :type process_name:  string
        '''
        return self._device.get_process_meminfo(process_name)

    def get_current_activity(self):
        '''获取当前Activtiy
        '''
        return self._device.get_current_activity()

    def take_screen_shot(self, path):
        '''截屏
        
        :param path: 截屏图片存放在PC上的路径
        :type path: string
        '''
        return self._device.take_screen_shot(path)

    def drag(self, x1, y1, x2, y2, count=5, sleep_time=40):
        '''滑动
        
        :param x1: 起始x坐标
        :type x1:  int
        :param y1: 起始y坐标
        :type y1:  int
        :param x2: 终止x坐标
        :type x2:  int
        :param y2: 终止y坐标
        :type y2:  int
        :param count: 滑动的步数
        :type count:  int
        :param sleep_time: 每步间sleep的时长
        :type sleep_time:  int，单位：ms
        '''
        return self._device.drag(x1, y1, x2, y2, count, sleep_time)

    def close(self):
        '''关闭创建的系统测试桩进程
        '''
        return self._device.close()

    def reboot(self, wait_cpu_low=True, min_boot_time=0, **kwds):
        '''重启手机
        
        :param wait_cpu_low:   是否等待CPU使用率降低
        :type wait_cpu_low:    bool
        :param min_boot_time: 允许重启的最短开机时间，单位为小时
        :type min_boot_time:  int
        '''
        return self._device.reboot(wait_cpu_low, min_boot_time, **kwds)

    def connect_wifi(self, wifi_name):
        '''连接指定的Wifi
        
        :param wifi_name: WiFi名称
        :type wifi_name:  string
        '''
        for _ in range(3):
            if self._device.connect_wifi(wifi_name): return True
            if self.is_virtual_device(): return True
            self.disable_wifi()  # 有些手机需要禁用一下wifi才能正常连接
            time.sleep(10)
        return False
    
    def enable_wifi(self):
        '''启用Wifi
        '''
        from testbase.testcase import Environ
        try:
            if not self.is_virtual_device():
                ssid = 'Tencent-StaffWiFi'
                env = Environ()
                if env.has_key('WIFI_SSID'): ssid = env['WIFI_SSID']
                return self.connect_wifi(ssid)  # Tencent-FreeWiFi 7/11停止
            else:
                return self.connect_wifi('WiredSSID')  # Tencent-FreeWiFi 7/11停止
        except RuntimeError:
            return False

    def disable_wifi(self):
        '''禁用Wifi
        '''
        return self._device.disable_wifi()
    
    def switch_to_data_connection(self):
        '''关闭WIFI,启用数据连接
        '''
        return self.disable_wifi() and self.enable_data_connection()
    
    def enable_data_connection(self):
        '''启用数据连接
        '''
        return self._device.enable_data_connection()

    def disable_data_connection(self):
        '''禁用数据连接
        '''
        sim_state = self._device.get_sim_card_state()
        if 'SIM_STATE_ABSENT' in sim_state or 'SIM_STATE_UNKNOWN' in sim_state: return True
        return self._device.disable_data_connection()

    def disable_network(self):
        '''禁用所有网络
        '''
        return self.disable_wifi() and self.disable_data_connection()

    def enable_network(self):
        '''启用任一网络，优先使用Wifi
        '''
        return self.enable_wifi() or self.enable_data_connection()

    def read_logcat(self, tag, process_name, pattern, num=1):
        '''查找最近满足条件的一条log
        
        :param tag: 期望的Tag
        :type tag:  string
        :param process_name: 期望的进程名
        :type process_name:  string
        :param pattern:  期望匹配的格式
        :type pattern:   Pattern
        :param num:  返回满足条件的日志条数
        :type num:   int
        '''
        return self._device.read_logcat(tag, process_name, pattern, num)

    def get_clipboard_text(self):
        '''获取剪切板内容
        '''
        return self._device.get_clipboard_text()
    
    def set_clipboard_text(self, text):
        '''设置剪贴板内容
        '''
        return self._device.set_clipboard_text(text)
    
    def wake_screen(self, wake=True):
        '''唤醒屏幕
        '''
        return self._device.wake_screen(wake)

    def unlock_keyguard(self):
        '''解锁屏幕
        '''
        return self._device.unlock_keyguard()
    
    def lock_keyguard(self):
        '''锁屏
        '''
        return self._device.lock_keyguard()
    
    def send_key(self, key):
        '''发送按键
        
        :param key: 按键
        :type key:  string
        '''
        return self._device.send_key(key)

    def clear_data(self, package_name):
        '''清理应用数据
        
        :param package_name: 包名
        :type package_name:  string
        '''
        return self._device.clear_data(package_name)

    def get_device_unique_id(self):
        '''获取设备唯一ID
        '''
        return self._device.get_device_unique_id()

    def get_app_size(self, package_name):
        '''获取应用所占大小
        '''
        return self._device.get_app_size(package_name)

    def get_string_resource(self, pkg_name, string_id, lang=''):
        '''获取字符串资源
        '''
        return self._device.get_string_resource(pkg_name, string_id, lang)

    def get_string_resource_id(self, pkg_name, text):
        '''获取字符串资源ID
        '''
        return self._device.get_string_resource_id(pkg_name, text)

    def set_default_language(self, lang):
        '''设置默认语言
        '''
        return self._device.set_default_language(lang)

    def is_app_installed(self, app_name):
        '''应用是否安装
        '''
        return self._device.is_app_installed(app_name)

    def get_static_field_value(self, pkg_name, cls_name, field_name, field_type=''):
        '''获取类中静态变量的值
        
        :param pkg_name:   包名
        :type pkg_name:    string
        :param cls_name:   类名
        :type cls_name:    string
        :param field_name: 字段名
        :type field_name:  string 
        '''
        return self._device.get_static_field_value(pkg_name, cls_name, field_name, field_type)

    def get_battery_capacity(self):
        '''获取当前电池电量
        '''
        return self._device.get_battery_capacity()

    def set_camera_photo(self, pic_path):
        '''设置相机图片，调用该接口后，调用相机接口会返回指定图片
        
        :param pic_path: 图片在PC中的路径
        :type pic_path:  String
        '''
        if not os.path.exists(pic_path):
            raise RuntimeError('图片：%s 不存在' % pic_path)
        dst_path = '/sdcard/dcim/camera%s' % (os.path.splitext(pic_path)[1])
        self.push_file(pic_path, dst_path)
        self.run_shell_cmd('am startservice -n com.test.qt4amockapp/.MockerService')
        self.run_shell_cmd('am broadcast -a setMockUri --es uri file://%s' % dst_path)
        self._device.set_default_app('android.media.action.IMAGE_CAPTURE', 'com.test.qt4amockapp')
    
    def clear_camera_default_app(self):
        '''清除默认相机应用
        '''
        return self._device.clear_default_app('android.media.action.IMAGE_CAPTURE')
        
    def has_gps(self):
        '''是否有GPS
        '''
        return self._device.has_gps()
    
    def has_camera(self):
        '''是否有摄像头
        '''
        return self._device.get_camera_number() > 0
    
    def has_sim_card(self):
        '''是否有sim卡
        '''
        sim_state = self._device.get_sim_card_state()
        return sim_state != 'SIM_STATE_ABSENT' and sim_state != 'SIM_STATE_UNKNOWN'  # 虚拟机返回的状态是SIM_STATE_UNKNOWN
    
    def is_debug_package(self, package_name):
        '''是否是debug包
        '''
        return self._device.is_debug_package(package_name)
    
    def _get_view_id(self, package_name, str_id):
        '''从控件字符串ID获取整型ID
        
        :param package_name: 应用包名
        :type package_name: string
        :param str_id: 字符串ID
        :type str_id:  string
        '''
        if not hasattr(self, '_view_id_dict'):
            self._view_id_dict = {}  # 该操作较为耗时，必须要缓存
        if not self._view_id_dict.has_key(package_name):
            self._view_id_dict[package_name] = {}
        if self._view_id_dict[package_name].has_key(str_id):
            return self._view_id_dict[package_name][str_id]
        view_id = self._device.get_view_id(package_name, str_id)
        self._view_id_dict[package_name][str_id] = view_id
        return view_id
    
    def _get_resource_origin_name(self, package_name, res_type, confuse_name):
        '''根据获取资源混淆后的名称获取原始名称
        
        :param package_name: 应用包名
        :type package_name:  string
        :param res_type:     资源类型
        :type res_type:      string
        :param confuse_name: 混淆后的名称
        :type confuse_name:  string
        '''
        if confuse_name == '': return ''  # 处理空字符串情况
        if len(confuse_name) > 4: return confuse_name  # 必然没有混淆
        if not hasattr(self, '_resource_name'):
            self._resource_name = {}  # 进行缓存
        if not package_name in self._resource_name:
            self._resource_name[package_name] = {}
        if not confuse_name in self._resource_name[package_name]:
            self._resource_name[package_name][confuse_name] = self._device.get_resource_origin_name(package_name, res_type, confuse_name)
        return self._resource_name[package_name][confuse_name]
    
    def send_text_to_app(self, activity, text):
        '''向app分享文本
        '''
        return self.start_activity(activity, action='android.intent.action.SEND', type='text/plain', extra={'android.intent.extra.TEXT': text})
    
    def send_image_to_app(self, activity, image_path):
        '''向app分享图片
        '''
        def _copy_image(src_path):
            from androiddriver.util import get_file_md5
            if not isinstance(src_path, unicode): src_path = src_path.decode('utf8')
            file_ext = os.path.splitext(src_path)[-1]
            dst_path = '/sdcard/dcim/%s%s' % (get_file_md5(src_path), file_ext)
            self.push_file(src_path, dst_path)
            return dst_path
        
        action = 'android.intent.action.SEND'
        if isinstance(image_path, (list, tuple)):
            image_path_new = [None for _ in range(len(image_path))]
            for i in range(len(image_path)):
                image_path_new[i] = 'file://' + _copy_image(image_path[i])
            image_path = image_path_new
            action = 'android.intent.action.SEND_MULTIPLE'
        else:
            image_path = 'file://' + _copy_image(image_path)
        return self.start_activity(activity, action=action, type='image/*', extra={'android.intent.extra.STREAM': image_path})
    
    def send_file_to_app(self, activity, file_path):
        '''向app分享文件
        '''
        def _copy_file(src_path):
            if not isinstance(src_path, unicode): src_path = src_path.decode('utf8')
            file_name = os.path.split(src_path)[-1]
            dst_path = '/data/local/tmp/%s' % (file_name)
            self.push_file(src_path, dst_path)
            return dst_path
        file_path = 'file://' + _copy_file(file_path)
        return self.start_activity(activity, action='android.intent.action.SEND', type='application/octet-stream', extra={'android.intent.extra.STREAM': file_path})
    
    def check_netstat(self):
        '''检查网络状态
        '''
        from androiddriver.util import TimeoutError
        try:
            return 'bytes from' in self.run_shell_cmd('ping -c 1 www.qq.com', True)
        except TimeoutError:
            return False
    
    def play_sound(self, file_path):
        '''播放语音
        
        :param file_path: 音频文件路径
        '''
        return self._device.play_sound(file_path)
    
    def modify_hosts(self, new_hosts=[]):
        '''修改hosts
        
        :param new_hosts: 要修改的host列表,如果为空,表示恢复为默认hosts
        :type new_hosts: list
        '''
        hosts_path = '/system/etc/hosts'
        bak_hosts_path = hosts_path + '.bak'
        self.adb._set_system_writable()  # 需要system目录可写
        if new_hosts:
            if not self.is_file_exists(bak_hosts_path):
                # 先生成备份文件
                self.copy_file(hosts_path, bak_hosts_path)
            else:
                # 先恢复成默认hosts
                self.copy_file(bak_hosts_path, hosts_path)
            for ip, host in new_hosts:
                self.run_shell_cmd('echo "%s        %s" >> %s' % (ip, host, hosts_path), True)
        else:
            # 恢复默认的hosts
            if self.is_file_exists(bak_hosts_path):
                self.copy_file(bak_hosts_path, hosts_path)
            else:
                self.run_shell_cmd('echo "127.0.0.1        localhost" > %s' % (hosts_path), True)
    
    def set_volume(self, volume):
        '''设置音量
        '''
        return self._device.set_volume(volume)
        
    def get_phone_contacts(self):
        '''获取手机联系人列表
        '''
        return self._device.get_phone_contacts()
        
    def add_phone_contacts(self, name, phone):
        '''添加手机联系人
        '''
        return self._device.add_phone_contacts(name, phone)
    
    def del_phone_contacts(self, name):
        '''删除手机联系人
        '''
        return self._device.del_phone_contacts(name)
    
    def set_app_permission(self, package_name, perm_name, is_allowed=True):
        '''设置应用权限
        
        :param package_name: 应用包名
        :type package_name:  string
        :param perm_name:    权限名称
        :type perm_name:     string
        :param is_allowed:   是否允许
        :type is_allowed:    bool
        '''
        return self._device.set_app_permission(package_name, perm_name, is_allowed)
    
    def set_screen_off_time(self, timeout=600):
        '''设置灭屏时间
        
        :param timeout: 超时时间
        :type timeout:  int，单位为秒
        '''
        return self._device.modify_system_setting('system', 'screen_off_timeout', timeout * 1000)
    
    def set_auto_rotate_screen(self, rotate=False):
        '''设置是否旋转屏幕
        
        :param rotate: 是否旋转
        :type rotate:  boolean
        '''
        return self._device.modify_system_setting('system', 'accelerometer_rotation', 1 if rotate else 0)
    
    def set_time_12_24(self, is_24=True):
        '''设置12/24小时格式
        
        :param is_24: 是否是24小时
        :type is_24:  boolean
        '''
        return self._device.modify_system_setting('system', 'time_12_24', 24 if is_24 else 12)
    
    def set_allow_unknown_app(self, allow=True):
        '''设置是否允许安装未知来源的应用
        
        :param allow: 是否允许
        :type allow:  boolean
        '''
        return self._device.modify_system_setting('secure', 'install_non_market_apps', 1 if allow else 0)
    
    def _initialize(self):
        '''初始化设备
        '''
        self.set_screen_off_time()
        self.set_auto_rotate_screen()
        self.set_time_12_24()
        self.set_allow_unknown_app()
    
    def set_system_time(self, new_time=None):
        '''设置系统时间
        
        :param new_time: 新时间,默认为PC上的时间,格式为: 20151001.170000
        :type  new_time: str
        '''
        return self._device.set_system_time(new_time)
    
class PerformDevice(Device):
    '''性能测试用设备，允许在环境变量中指定要测试的设备
    '''
    def __init__(self, device_id=None, attrs={}):
        '''获取一个Android设备，获取成功后则独占该设备。如果未安装qt4a的驱动，则自动安装。
        
        :param device_id: 获取指定设备id的Android设备。如果为空则任意获取一台空闲设备。
        '''
        from tuia.env import run_env, EnumEnvType
        if os.environ.has_key('PREFER_DEVICE_ID'):
            # 存在该变量时去设备管理平台申请
            super(PerformDevice, self).__init__(attrs={'dev_mb_serialno': os.environ['PREFER_DEVICE_ID']})
            del os.environ['PREFER_DEVICE_ID']  # 防止第二次还是使用这个DeviceID申请
            return
        if not device_id and os.environ.has_key('DEVICE_ID'):
            device_id_list = [device.device_id for device in self.device_list]  # 已申请设备列表
            if not os.environ['DEVICE_ID'] in device_id_list:
                super(PerformDevice, self).__init__(os.environ['DEVICE_ID'])
                return
        super(PerformDevice, self).__init__(device_id)

if __name__ == '__main__':
    pass
    