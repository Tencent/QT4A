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

import six
import os
import re
import socket
import struct
import time
import tempfile
import threading
import zipfile
from io import BytesIO
from pkg_resources import iter_entry_points

from testbase import logger as qta_logger
from testbase.conf import settings
from testbase.resource import LocalResourceHandler, LocalResourceManagerBackend
from qt4a.androiddriver.adb import ADB, LocalADBBackend
from qt4a.androiddriver.util import Singleton, logger, static_property, get_file_md5
from qt4a.androiddriver.devicedriver import DeviceDriver

class AndroidDeviceResourceHandler(LocalResourceHandler):
    
    def iter_resource(self, res_group=None, condition=None):
        """遍历全部资源（可以按照优先级顺序返回来影响申请资源的优先级）

        :param res_group: 资源分组
        :type res_group: str
        :param condition: 资源属性匹配
        :type condition: dict
        :returns: iterator of resource, dict type with key 'id'
        :rtypes: iterator(dict)
        """
        device_list = LocalDeviceProvider.list()
        
        for device in device_list:
            yield {'id': device}
            
# 注册android本地资源
LocalResourceManagerBackend.register_resource_type("android", AndroidDeviceResourceHandler())    

class IDeviceProvider(object):

    def connect_device(self, dev_prop):
        '''连接设备

        :param dev_prop: 设备属性
        :type  dev_prop: dict

        :return: Device实例
        '''
        pass

    def release_device(self, dev_id):
        '''释放设备

        :param dev_id: 设备ID
        :type  dev_id: str
        '''
        pass

class LocalDeviceProvider(IDeviceProvider):
    '''本地设备提供者
    '''

    @staticmethod
    def list():
        '''获取本地可用设备列表
        '''
        device_list = LocalADBBackend.list_device()
        _device_list = []
        for device in device_list:
            if device.startswith('emulator-'): continue  # 避免出现两个名字不同的同一设备
            _device_list.append(device)
        available_devices = os.environ.get('QT4A_AVAILABLE_DEVICES', '')
        if _device_list and available_devices:
            intersect_device_list = []
            available_device_list = available_devices.split(',')
            for available_device in available_device_list:
                available_device = available_device.strip()
                if available_device in _device_list:
                    intersect_device_list.append(available_device)
            _device_list = intersect_device_list

        import random
        random.shuffle(_device_list)  # 可以随机取设备
        return _device_list

    def connect_device(self, dev_prop):
        '''连接设备

        :param dev_prop: 设备属性
        :type  dev_prop: dict

        :return: Device实例
        '''
        if not 'id' in dev_prop: return None
        dev_id = dev_prop['id']
        if dev_id in LocalDeviceProvider.list():
            return Device(dev_id)
        return None

class DeviceProviderManager(Singleton):
    '''设备提供者管理
    '''

    def __init__(self):
        self._device_providers = [LocalDeviceProvider()]
        for ep in iter_entry_points("qt4a.device_provider"):
            device_provider_class = ep.load()
            self._device_providers.append(device_provider_class())
        self._acquired_devices = {}

    def connect_device(self, dev_prop):
        '''连接设备

        :param dev_prop: 设备属性
        :type  dev_prop: dict

        :return: Device实例
        '''
        for provider in self._device_providers:
            device = provider.connect_device(dev_prop)
            print (device)
            if device: 
                self._acquired_devices[device.device_id] = provider
                return device
        return None

    def release_all(self):
        '''释放所有设备
        '''
        for device_id in self._acquired_devices:
            self._acquired_devices[device_id].release(device_id)
        self._acquired_devices = {}

class Device(object):
    '''Android设备类
    '''
    device_list = [] 

    def __init__(self, id_or_adb_backend=None):
        '''获取一个Android设备，获取成功后则独占该设备。
        
        :param device_id: 获取制定设备id的Android设备。如果为空则任意获取一台空闲设备。
        '''
        self._device = None
        if isinstance(id_or_adb_backend, str):
            adb_backend = LocalADBBackend.open_device(id_or_adb_backend)
        elif not id_or_adb_backend:
            local_device_list = LocalDeviceProvider.list()
            if not local_device_list: raise RuntimeError('No local device found')
            adb_backend = LocalADBBackend.open_device(local_device_list[0])
        else:
            adb_backend = id_or_adb_backend
        self._adb = ADB.open_device(adb_backend)
        self._device_driver = DeviceDriver(self._adb)
        Device.device_list.append(self)

    def __del__(self):
        '释放设备'
        pass
        
    @staticmethod
    def release_all_device():
        '''释放所有设备
        '''
        qta_logger.info('释放设备资源')
        Device.device_list = []
        DeviceProviderManager().release_all()

    @static_property
    def device_id(self):
        '''设备ID
        '''
        return self.adb.device_name
    
    @property
    def device_host(self):
        '''设备主机
        '''
        return self.adb.device_host
        
    @static_property
    def cpu_type(self):
        '''cpu类型
        '''
        return self.adb.get_cpu_abi()

    @property
    def imei(self):
        '''手机串号
        '''
        if not hasattr(self, '_imei'):
            self._imei = self._device_driver.get_device_imei()
        return self._imei

    @static_property
    def model(self):
        '''设备型号
        '''
        return self.adb.get_device_model()

    @static_property
    def system_version(self):
        '''系统版本
        '''
        return self.adb.get_system_version()

    @static_property
    def sdk_version(self):
        '''SDK版本
        '''
        return self.adb.get_sdk_version()

    @property
    def screen_size(self):
        '''屏幕大小
        '''
        return self._device_driver.get_screen_size()
    
    @static_property
    def screen_scale(self):
        '''屏幕缩放比例
        '''
        if self.is_emulator_device():
            return int(self.adb.get_property('qemu.sf.lcd_density')) / 160.0
        else:
            return int(self.adb.get_property('ro.sf.lcd_density')) / 160.0
    
    @property
    def language(self):
        '''语言
        '''
        return self._device_driver.get_language()

    @property
    def country(self):
        '''国家
        '''
        return self._device_driver.get_country()
    
    @property
    def current_activity(self):
        '''当前Activity
        '''
        return self.get_current_activity()
    
    @property
    def adb(self):
        return self._adb
    
    @property
    def debuggable(self):
        '''是否是调试版系统
        '''
        return not (self.adb.get_property('ro.secure') == '1' and self.adb.get_property('ro.debuggable') == '0')

    def __str__(self):
        return '%s(%s %s Android %s)' % (self.device_id, self.model, self.cpu_type, self.system_version)
    
    def get_imei(self):
        '''获取设备imei号
        '''
        try:
            return self.adb.get_device_imei()
        except RuntimeError as e:
            logger.warn('Read device imei by dumpsys failed: %s' % e)
            return self._device_driver.get_device_imei()

    def is_rooted(self):
        '''是否root
        '''
        return self.adb.is_rooted()

    def is_emulator_device(self):
        '''是否是模拟器设备
        '''
        return self.adb.get_property('ro.kernel.android.qemud').strip() == '1'
        
    def run_shell_cmd(self, cmd, *args, **kwargs):
        '''执行adb shell命令
        '''
        return self.adb.run_shell_cmd(cmd, *args, **kwargs)
    
    def run_as(self, package_name, cmd, **kwargs):
        '''以package_name权限执行命令cmd
        
        :param package_name: 包名，必须是已经安装的debug包
        :type  package_name: string
        :param cmd:          命令行
        :type  cmd:          string
        '''
        return self.adb.run_as(package_name, cmd, **kwargs)
    
    def start_activity(self, activity_name, action='', type='', data_uri='', extra={}, wait=True):
        '''启动activity

        :param activity_name: Activity名称，如：com.tencent.mobileqq/.activity.SplashActivity
        :type  activity_name: string
        :param action:        Action名称
        :type  action:        string
        :param type:          mime类型
        :type  type:          string
        :param data_uri:      data uri
        :type  data_uri:      string
        :param extra:         额外参数
        :type  extra:         dict
        :param wait:          是否等待启动完成
        :type  wait:          boolean
        '''
        use_am = True

        for key in extra.keys():
            if isinstance(extra[key], (list, tuple)):
                use_am = False
                break
        if use_am: return self.adb.start_activity(activity_name, action, type, data_uri, extra, wait)
        
        params = {'Component': activity_name}
        if action: params['Action'] = action
        if type: params['Type'] = type
        if extra: params['FileUri'] = extra['android.intent.extra.STREAM']
        return self._device_driver.start_activity(params)

    def install_package(self, pkg_path, pkg_name='', overwrite=False):
        '''安装应用
        
        :param pkg_path:  安装包路径
        :type  pkg_path:  string
        :param pkg_name:  应用包名
        :type  pkg_name:  string
        :param overwrite: 是否是覆盖安装
        :type  overwrite: bool
        '''
        return self._device_driver.install_package(pkg_path, overwrite)
    
    def uninstall_package(self, pkg_name):
        '''卸载应用
        
        :param pkg_name: 包名
        :type  pkg_name: string
        '''
        return self.adb.uninstall_app(pkg_name)
        
    def kill_process(self, package_name):
        '''杀死进程
        
        :param package_name: 应用包名
        :type package_name: string
        '''
        return self._device_driver.kill_process(package_name)

    def push_file(self, src_path, dst_path):
        '''向手机中拷贝文件
        
        :param src_path: PC上的源路径
        :type src_path:  string
        :param dst_path: 手机上的目标路径
        :type dst_path:  string
        '''
        
        if not os.path.exists(src_path):
            raise RuntimeError('File: %s not exist' % src_path)
        file_size = os.path.getsize(src_path)
        is_zip = False
        if file_size >= 5 * 1024 * 1024:
            is_zip = True
            zip_file_path = src_path + '.zip'
            zip_file = zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED)
            if dst_path[-1] == '/':
                # filename not specified
                filename = os.path.split(src_path)[-1]
            else:
                filename = dst_path.split('/')[-1]
            zip_file.write(src_path, filename)
            zip_file.close()
            src_path = zip_file_path
            dst_path += '.zip'
        ret = self.adb.push_file(src_path, dst_path)
        if is_zip:
            os.remove(src_path)
            if not self._device_driver.unzip_file(dst_path, dst_path[:dst_path.rfind('/')]):
                logger.warn('unzip file %s failed' % dst_path)
                ret = self.adb.push_file(src_path[:-4], dst_path[:-4])
            elif dst_path.startswith('/data/'):
                self.adb.chmod(dst_path[:-4], '744')
            self.delete_file(dst_path)
            dst_path = dst_path[:-4]
        try:
            self.run_shell_cmd('touch "%s"' % dst_path)  # 修改文件修改时间
        except:
            logger.exception('touch file %s error' % dst_path)
        return ret
    
    def push_dir(self, src_path, dst_path):
        '''向手机中拷贝文件夹
        
        :param src_path: PC上的源目录路径
        :type src_path:  string
        :param dst_path: 手机上的目的目录路径
        :type dst_path:  string
        '''
        if not os.path.exists(src_path):
            raise RuntimeError('Directory %s not exist' % src_path)
        for file in os.listdir(src_path):
            file_src_path = os.path.join(src_path, file)
            file_dst_path = dst_path + '/' + file
            self.push_file(file_src_path, file_dst_path)

    def pull_file(self, src_path, dst_path):
        '''将手机中的文件拷贝到PC中
        
        :param src_path: 手机中的源路径
        :type src_path:  string
        :param dst_path: PC中的目的路径
        :type dst_path:  string
        '''
        self.adb.list_dir(src_path)
        try:
            ret = self.adb.pull_file(src_path, dst_path)
            if 'does not exist' not in ret: return
        except RuntimeError as e:
            logger.warn('pull file failed: %r' % e)
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
        
        :param src_path: 手机上的源目录路径
        :type src_path:  string
        :param dst_path: PC上的目的目录路径
        :type dst_path:  string
        '''
        if not os.path.exists(dst_path):
            os.mkdir(dst_path)
        subdirs, files = self.adb.list_dir(src_path)
        for file in files:
            self.pull_file(src_path + '/' + file['name'], os.path.join(dst_path, file['name']))
        for subdir in subdirs:
            self.pull_dir(src_path + '/' + subdir['name'], os.path.join(dst_path, subdir['name']))

    def list_dir(self, dir_path):
        '''列取目录
        '''
        return self.adb.list_dir(dir_path)
    
    def is_file_exists(self, file_path):
        '''判断文件或目录是否存在

        :param file_path: 文件或目录在设备中的路径
        :type  file_path: string
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
        return self.adb.delete_folder(folder_path)

    def delete_file(self, file_path):
        '''删除文件

        :param file_path: 文件在设备中的路径
        :type  file_path: string
        '''
        return self.adb.delete_file(file_path)

    def mkdir(self, dir_path):
        '''创建目录

        :param dir_path: 要创建的目录路径
        :type  dir_path: string
        '''
        return self.adb.mkdir(dir_path)
    
    def copy_file(self, src_path, dst_path):
        '''设备内复制文件
        
        :param src_path: 源路径
        :type src_path:  string
        :param dst_path: 目标路径
        :type dst_path:  string
        '''
        if not self.is_file_exists(src_path):
            raise RuntimeError('File %s not exist' % src_path)
        self.adb.copy_file(src_path, dst_path)
        
    def get_external_sdcard_path(self):
        '''获取外置SD卡路径
        '''
        return self._device_driver.get_external_sdcard_path()

    def refresh_media_store(self, file_path=''):
        '''刷新图库，显示新拷贝到手机的图片

        :param file_path: 要刷新的图片路径，不指定则刷新整个sdcard
        :type  file_path: string
        '''
        return self._device_driver.refresh_media_store(file_path)

    def get_current_activity(self):
        '''获取当前Activtiy
        '''
        return self._device_driver.get_current_activity()

    def take_screen_shot(self, save_path):
        '''截屏
        
        :param save_path: 截屏图片存放在PC上的路径
        :type save_path: string
        '''
        return self._device_driver.take_screen_shot(save_path)
    
    def record_screen(self, save_path, record_time, frame_rate=10, quality=20):
        '''录屏
        
        :param save_path:   保存路径，如果为已存在的目录路径，则会将每一帧图片保存到该目录下
        :type  save_path:   string
        :param record_time: 录制时间，单位：秒
        :type  record-time: int/float
        :param frame_rate:  帧率，1-30
        :type  frame_rate:  int
        :param quality:     压缩质量，10-100
        :type  quality:     int
        '''
        import shutil
        from qt4a.androiddriver.device_driver import qt4a_path
        to_video = True
        if os.path.exists(save_path) and os.path.isdir(save_path): to_video = False
        
        if frame_rate < 1 or frame_rate > 30:
            raise ValueError('frame rate must between 1 and 30')
        if quality < 10 or quality > 100:
            raise ValueError('quality must between 10 and 100')
        remote_tmp_path = '%s/screen.record' % qt4a_path
        self.run_shell_cmd('%s/screenshot record -p %s -t %d -f %d -q %d' % (qt4a_path, remote_tmp_path, int(record_time * 1000), int(frame_rate), int(quality)))
        local_tmp_path = tempfile.mktemp()
        self.pull_file(remote_tmp_path, local_tmp_path)
        save_dir = save_path
        if to_video: save_dir = tempfile.mkdtemp('.screenshot')
        frame_list = Device.extract_record_frame(local_tmp_path, save_dir)
        os.remove(local_tmp_path)
        if to_video:
            Device.screen_frame_to_video(frame_list, frame_rate, save_path)
            shutil.rmtree(save_dir)
        result = []
        for it in os.listdir(save_dir):
            result.append(os.path.join(save_dir, it))
        return result
    
    @staticmethod
    def screen_frame_to_video(frame_list, frame_rate, save_path):
        '''将录屏帧序列转换为视频文件
        '''
        try:
            import cv2
        except ImportError:
            return None
        
        _, width, height = cv2.imread(frame_list[0]).shape[::-1]
        format = 'MJPG'
        if save_path.lower().endswith('.flv'): format = 'FLV1'
        elif save_path.lower().endswith('.mp4'): format = 'DIVX'
        videoWriter = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*format), frame_rate, (width, height))
        for it in frame_list:
            img = cv2.imread(it) 
            videoWriter.write(img)
        return save_path
            
    @staticmethod
    def extract_record_frame(file_path, save_dir):
        '''提取录屏文件中的帧
        '''
        frame_list = []
        with open(file_path, 'rb') as fp:
            while True:
                data = fp.read(4)
                if not data: break
                timestamp = struct.unpack('I', data)[0]
                data_len = struct.unpack('I', fp.read(4))[0]
                data = fp.read(data_len)
                save_path = os.path.join(save_dir, '%.8d.jpg' % timestamp)
                with open(save_path, 'wb') as f:
                    f.write(data)
                frame_list.append(save_path)
        return frame_list
    
    def drag(self, x1, y1, x2, y2, count=5, wait_time=40, send_down_event=True, send_up_event=True):
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
        :param wait_time: 每步间等待的时长
        :type wait_time:  int，单位：ms
        :param send_down_event: 是否发送DOWN事件
        :type  send_down_event: bool
        :param send_up_event: 是否发送UP事件
        :type  send_up_event: bool
        '''
        return self._device_driver.drag(x1, y1, x2, y2, count, wait_time, send_down_event, send_up_event)

    def click(self, x, y):
        '''单击屏幕坐标

        :param x: 横坐标
        :type  x: int/float
        :param y: 纵坐标
        :type  y: int/float
        '''
        return self._device_driver.drag(x, y, x, y)

    def long_click(self, x, y, duration=1):
        '''长按屏幕坐标

        :param x: 横坐标
        :type  x: int/float
        :param y: 纵坐标
        :type  y: int/float
        :param duration: 按住时长，单位为秒
        :type duration:  int/float
        '''
        self._device_driver.drag(x, y, x, y, send_up_event=False)
        time.sleep(duration)
        self._device_driver.drag(x, y, x, y, send_down_event=False)

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
        return self._device_driver.reboot(wait_cpu_low, usage=usage, duration=duration, timeout=timeout)

    def connect_wifi(self, wifi_name, wifi_pass=''):
        '''连接指定的Wifi
        
        :param wifi_name: WiFi名称
        :type wifi_name:  string
        '''
        for _ in range(3):
            if self._device_driver.connect_wifi(wifi_name, wifi_pass): return True
            self.disable_wifi()  # 有些手机需要禁用一下wifi才能正常连接
            time.sleep(10)
        return False
    
    def enable_wifi(self):
        '''启用Wifi
        '''
        ssid = ''
        pwd = ''

        if hasattr(settings, 'QT4A_WIFI_SSID'):
            ssid = settings.QT4A_WIFI_SSID
        if hasattr(settings, 'QT4A_WIFI_PASSWORD'):
            pwd = settings.QT4A_WIFI_PASSWORD

        if ssid: return self.connect_wifi(ssid, pwd)

        return False

    def disable_wifi(self):
        '''禁用Wifi
        '''
        return self._device_driver.disable_wifi()
    
    def switch_to_data_connection(self):
        '''关闭WIFI,启用数据连接
        '''
        return self.disable_wifi() and self._device_driver.enable_data_connection()

    def disable_data_connection(self):
        '''禁用数据连接
        '''
        sim_state = self.get_sim_card_state()
        if 'SIM_STATE_ABSENT' in sim_state or 'SIM_STATE_UNKNOWN' in sim_state: return True
        return self._device_driver.disable_data_connection()

    def disable_network(self):
        '''禁用所有网络
        '''
        return self.disable_wifi() and self.disable_data_connection()

    def enable_network(self):
        '''启用任一网络，优先使用Wifi
        '''
        return self.enable_wifi() or self.enable_data_connection()

    def read_logcat(self, tag, process_name_pattern, pattern, num=1):
        '''查找最近满足条件的一条log
        
        :param tag: 期望的Tag
        :type tag:  string
        :param process_name_pattern: 期望的进程名，传入正则表达式
        :type process_name_pattern:  string
        :param pattern:  期望匹配的格式
        :type pattern:   Pattern
        :param num:  返回满足条件的日志条数
        :type num:   int
        '''
        from qt4a.androiddriver.util import logger
        pat = re.compile(r'^\[(.+)\(\d+\)\]\s+\[.+\]\s+\w/(.+)\(\s*\d+\):\s+(.+)$')
        log_pat = re.compile(pattern)
        log_list = self.adb.get_log(False)
        result_list = []
        k = 0
        for i in range(len(log_list) - 1, -1, -1):
            ret = pat.match(log_list[i])
            if not ret: 
                logger.info('read_logcat:%s not match ^\[(.+)\(\d+\)\]\s+\[.+\]\s+\w/(.+)\(\s*\d+\):\s+(.+)$' % log_list[i])
                continue
            if not process_name_pattern: continue
            process_pat = re.compile(process_name_pattern)
            if not process_pat.match(ret.group(1)): continue
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
        return self._device_driver.get_clipboard_text()
    
    def set_clipboard_text(self, text):
        '''设置剪贴板内容
        '''
        return self._device_driver.set_clipboard_text(text)
    
    def wake_screen(self, wake=True):
        '''唤醒屏幕
        '''
        return self._device_driver.wake_screen(wake)

    def unlock_keyguard(self):
        '''解锁屏幕
        '''
        return self._device_driver.unlock_keyguard()
    
    def lock_keyguard(self):
        '''锁屏
        '''
        return self._device_driver.lock_keyguard()
    
    def send_key(self, key):
        '''发送按键
        
        :param key: 按键
        :type key:  string
        '''
        return self._device_driver.send_key(key)
    
    def send_text(self, text):
        '''通过输入法方式发送文本
        
        :param text: 要发送的文本
        :type  text: string
        '''
        max_send_size = 960
        if isinstance(text, bytes):
            text = text.decode('utf8')
        text_en = ''
        i = 0
        while i < len(text):
            c = text[i]
            if c >= u'\ud800' and c <= u'\udbff':
                d = text[i + 1]
                if d >= u'\udc00' and d <= u'\udfff':
                    # 四字节unicode编码
                    text_en += r'\u%.4x\u%.4x' % (ord(c), ord(d))
                    i += 2
                    continue
            text_en += c
            i += 1
        
        text_en = text_en.encode('raw_unicode_escape')
        total_len = len(text_en)
        if total_len > max_send_size: raise RuntimeError('Text is too long %d' % total_len)
        extra = {'text': text_en}
        if len(text_en) == 1: extra['toClear'] = 'false'
        self.adb.send_broadcast('com.test.androidspy.input', extra)
        
    def clear_data(self, package_name):
        '''清理应用数据
        
        :param package_name: 包名
        :type package_name:  string
        '''
        if not self.adb.get_package_path(package_name): return True
        cmdline = 'pm clear %s' % package_name
        if self.adb.is_rooted():
            return 'Success' in self.run_shell_cmd(cmdline, True)
        else:
            result = self.run_shell_cmd(cmdline)
            if 'Success' in result:
                return True
            logger.warn('clear %s data failed: %s' % (package_name, result))
            return 'Success' in self.run_as(package_name, cmdline)

    def get_string_resource(self, pkg_name, string_id, lang=''):
        '''获取字符串资源
        '''
        result = self._device_driver.get_string_resource(pkg_name, string_id, lang)
        if result == ("Can't find string %s" % string_id) or 'Can\'t find class' in result:
            if pkg_name == 'android': raise RuntimeError(result)
            return self.get_string_resource('android', string_id, lang)
        else:
            return result
        
    def get_string_resource_id(self, pkg_name, text):
        '''获取字符串资源ID
        '''
        return self._device_driver.get_string_resource_id(pkg_name, text)

    def set_default_language(self, lang):
        '''设置默认语言
        '''
        return self._device_driver.set_default_language(lang)

    def is_app_installed(self, app_name):
        '''应用是否安装
        '''
        package_path = self.adb.get_package_path(app_name)
        return package_path != ''

    def get_static_field_value(self, pkg_name, cls_name, field_name, field_type=''):
        '''获取类中静态变量的值
        
        :param pkg_name:   包名
        :type pkg_name:    string
        :param cls_name:   类名
        :type cls_name:    string
        :param field_name: 字段名
        :type field_name:  string 
        '''
        return self._device_driver.get_static_field_value(pkg_name, cls_name, field_name, field_type)

    def set_default_app(self, action, type, new_app):
        '''设置默认应用
        
        :param action:  应用针对的类型，如：android.media.action.IMAGE_CAPTURE
        :type  action:  String
        :param new_app: 新的应用包名
        :type  new_app: String
        '''
        return self._device_driver.set_default_app(action, type, new_app)
    
    def set_camera_photo(self, pic_path):
        '''设置相机图片，调用该接口后，调用相机接口会返回指定图片
        
        :param pic_path: 图片在PC中的路径
        :type pic_path:  String
        '''
        if not os.path.exists(pic_path):
            raise RuntimeError('图片：%s 不存在' % pic_path)
        dst_path = '/sdcard/dcim/camera%s' % (os.path.splitext(pic_path)[1])
        self.push_file(pic_path, dst_path)
        self.adb.set_property('debug.mockcamera.image_path', dst_path)
        self.set_default_app('android.media.action.IMAGE_CAPTURE', '', 'com.test.androidspy')
    
    def clear_camera_default_app(self):
        '''清除默认相机应用
        '''
        from qt4a.androiddriver.util import logger
        if self.is_rooted():
            return self._device_driver.clear_default_app('android.media.action.IMAGE_CAPTURE')
        else:
            logger.warn('clear_camera_default_app need root')
           
    def has_gps(self):
        '''是否有GPS
        '''
        return self._device_driver.has_gps()
    
    def has_camera(self):
        '''是否有摄像头
        '''
        return self._device_driver.get_camera_number() > 0

    def get_sim_card_state(self):
        '''获取sim卡状态
        '''
        sim_state = self.adb.get_property('gsm.sim.state').strip()
        if sim_state == 'READY': return 'SIM_STATE_READY'
        if 'ABSENT' in sim_state or 'NOT_READY' in sim_state:
            return 'SIM_STATE_ABSENT'
        logger.info('sim state: %s' % sim_state)
        return 'SIM_STATE_UNKNOWN'
    
    def has_sim_card(self):
        '''是否有sim卡
        '''
        sim_state = self.get_sim_card_state()
        return sim_state != 'SIM_STATE_ABSENT' and sim_state != 'SIM_STATE_UNKNOWN'  # 虚拟机返回的状态是SIM_STATE_UNKNOWN
    
    def is_debug_package(self, package_name):
        '''是否是debug包
        '''
        return self._device_driver.is_debug_package(package_name)
    
    def _get_view_id(self, package_name, str_id):
        '''从控件字符串ID获取整型ID
        
        :param package_name: 应用包名
        :type package_name: string
        :param str_id: 字符串ID
        :type str_id:  string
        '''
        if not hasattr(self, '_view_id_dict'):
            self._view_id_dict = {}  # 该操作较为耗时，必须要缓存
        if not package_name in self._view_id_dict:
            self._view_id_dict[package_name] = {}
        if str_id in self._view_id_dict[package_name]:
            return self._view_id_dict[package_name][str_id]
        view_id = self._device_driver.get_view_id(package_name, str_id)
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
            self._resource_name[package_name][confuse_name] = self._device_driver.get_resource_origin_name(package_name, res_type, confuse_name)
        return self._resource_name[package_name][confuse_name]
    
    def send_text_to_app(self, activity, text):
        '''向app分享文本
        '''
        return self.start_activity(activity, action='android.intent.action.SEND', type='text/plain', extra={'android.intent.extra.TEXT': text})
    
    def send_image_to_app(self, activity, image_path):
        '''向app分享图片
        '''
        def _copy_image(src_path):
            from qt4a.androiddriver.util import get_file_md5
            if six.PY2 and not isinstance(src_path, unicode): src_path = src_path.decode('utf8')
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
            if six.PY2 and not isinstance(src_path, unicode): src_path = src_path.decode('utf8')
            file_name = os.path.split(src_path)[-1]
            dst_path = '/data/local/tmp/%s' % (file_name)
            self.push_file(src_path, dst_path)
            return dst_path
        file_path = 'file://' + _copy_file(file_path)
        return self.start_activity(activity, action='android.intent.action.SEND', type='application/octet-stream', extra={'android.intent.extra.STREAM': file_path})
    
    def check_netstat(self):
        '''检查网络状态
        '''
        try:
            return 'bytes from' in self.run_shell_cmd('ping -c 1 www.qq.com', self.is_rooted())
        except TimeoutError:
            return False
    
    def play_sound(self, file_path, volume=50):
        '''播放语音
        
        :param file_path: 音频文件路径
        :type  file_path: string
        '''
        from qt4a.androiddriver.util import get_file_md5
        self.set_volume(volume)  # 先设置音量
        file_ext = os.path.splitext(file_path)[-1]
        dst_path = '/data/local/tmp/%s%s' % (get_file_md5(file_path), file_ext)
        self.push_file(file_path, dst_path)
        return self._device_driver.play_sound(dst_path)

    def modify_hosts(self, new_hosts=[]):
        '''修改hosts
        
        :param new_hosts: 要修改的host列表,如果为空,表示恢复为默认hosts
        :type new_hosts: list
        '''
        hosts_path = '/system/etc/hosts'
        bak_hosts_path = hosts_path + '.bak'
        self.adb._set_system_writable()  # 需要system目录可写
        backup = 'echo "127.0.0.1        localhost" > %s' % (hosts_path)
        if new_hosts:
            if not self.is_file_exists(bak_hosts_path):
                # 先生成备份文件
                self.copy_file(hosts_path, bak_hosts_path)
            
            result = self.run_shell_cmd(backup, True)  # 保证当前的hosts文件是干净的
            if 'Permission denied' in result:
                self.run_shell_cmd('chmod 666 %s' % hosts_path, True)
                self.run_shell_cmd(backup, True)

            for ip, host in new_hosts:
                self.run_shell_cmd('echo "%s        %s" >> %s' % (ip, host, hosts_path), True)

            for ip, host in new_hosts:
                real_ip = self.resolve_domain(host)
                if real_ip != ip:
                    raise RuntimeError('设置hosts[%s %s]失败，当前解析值为：%s' % (ip, host, real_ip))
        else:
            # 恢复默认的hosts
            if self.is_file_exists(bak_hosts_path):
                self.copy_file(bak_hosts_path, hosts_path)
            else:
                self.run_shell_cmd(backup, True)

    def set_volume(self, volume):
        '''设置音量
        '''
        return self._device_driver.set_volume(volume)
        
    def get_phone_contacts(self):
        '''获取手机联系人列表
        '''
        return self._device_driver.get_phone_contacts()
        
    def add_phone_contacts(self, name, phone):
        '''添加手机联系人
        '''
        return self._device_driver.add_phone_contacts(name, phone)
    
    def del_phone_contacts(self, name):
        '''删除手机联系人
        '''
        return self._device_driver.del_phone_contacts(name)
    
    def set_app_permission(self, package_name, perm_name, is_allowed=True):
        '''设置应用权限
        
        :param package_name: 应用包名
        :type package_name:  string
        :param perm_name:    权限名称
        :type perm_name:     string
        :param is_allowed:   是否允许
        :type is_allowed:    bool
        '''
        return self._device_driver.set_app_permission(package_name, perm_name, is_allowed)
    
    def set_screen_off_time(self, timeout=600):
        '''设置灭屏时间
        
        :param timeout: 超时时间
        :type timeout:  int，单位为秒
        '''
        if timeout <= 0: timeout = 2147483647
        else: timeout = timeout * 1000
        return self._device_driver.modify_system_setting('system', 'screen_off_timeout', timeout)
    
    def set_auto_rotate_screen(self, rotate=False):
        '''设置是否旋转屏幕
        
        :param rotate: 是否旋转
        :type rotate:  boolean
        '''
        return self._device_driver.modify_system_setting('system', 'accelerometer_rotation', 1 if rotate else 0)
    
    def set_time_12_24(self, is_24=True):
        '''设置12/24小时格式
        
        :param is_24: 是否是24小时
        :type is_24:  boolean
        '''
        return self._device_driver.modify_system_setting('system', 'time_12_24', 24 if is_24 else 12)
    
    def set_allow_unknown_app(self, allow=True):
        '''设置是否允许安装未知来源的应用
        
        :param allow: 是否允许
        :type allow:  boolean
        '''
        return self._device_driver.modify_system_setting('secure', 'install_non_market_apps', 1 if allow else 0)
    
    def set_default_input_method(self, input_method):
        '''设置默认输入法
        
        :param input_method: 要设置的输入法服务名（package_name/service_name）
        :type  input_method: string
        '''
        self._device_driver.modify_system_setting('secure', 'enabled_input_methods', input_method)
        self._device_driver.modify_system_setting('secure', 'default_input_method', input_method)
    
    def connect_vpn(self, vpn_type, server, username, password):
        '''连接VPN
        
        :param vpn_type:  VPN类型
        :type vpn_type:   string
        :param server:    服务器地址
        :type server:     string
        :param username:  用户名
        :type username:   string
        :param password:  密码
        :type password:   string
        '''
        if vpn_type == 'PPTP':
            vpn_type = 0
        elif vpn_type == 'L2TP_IPSEC_PSK':
            vpn_type = 1
        elif vpn_type == 'L2TP_IPSEC_RSA':
            vpn_type = 2
        elif vpn_type == 'IPSEC_XAUTH_PSK':
            vpn_type = 3
        elif vpn_type == 'IPSEC_XAUTH_RSA':
            vpn_type = 4
        elif vpn_type == 'TYPE_IPSEC_HYBRID_RSA':
            vpn_type = 5
        else:
            raise RuntimeError('不支持的VPN类型：%s' % vpn_type)
        
        timeout = 10
        
        for _ in range(3):
            if not self._device_driver.connect_vpn(vpn_type, server, username, password): return False
            time0 = time.time()
            while time.time() - time0 < timeout:
                if self._device_driver.is_vpn_connected(): return True
                time.sleep(1)
        return False
    
    def disconnect_vpn(self):
        '''断开VPN
        '''
        return self._device_driver.disconnect_vpn()
    
    def end_call(self):
        '''挂断电话
        '''
        return self._device_driver.end_call()
    
    def grant_all_runtime_permissions(self, package_name):
        '''给APP授予所有运行时权限
        '''
        return self._device_driver.grant_all_runtime_permissions(package_name)
    
    def set_http_proxy(self, host, port):
        '''设置http代理
        
        :param host: 代理服务器地址
        :param port: 代理服务器端口
        '''
        return self._device_driver.set_http_proxy(host, port)
    
    def clear_http_proxy(self):
        '''清除http代理
        '''
        return self._device_driver.set_http_proxy(None, None)
    
    def register_screenshot_callback(self, callback, frame_rate=15):
        '''注册截图回调函数
        
        :param callback: 回调函数，回调参数为PIL的Image对象
        :type  callback: function
        :param frame_rate: 期望的帧率
        :type  frame_rate: int
        '''
        import copy
        from PIL import Image
        if not hasattr(self, '_screenshot_callbacks'):
            self._screenshot_callbacks = [callback]
            sock = self._device_driver.connect_screenshot_service()
            sock.send(struct.pack('II', 0x3, frame_rate))
            def recv_data(data_len):
                data = ''
                while len(data) < data_len:
                    try:
                        buff = sock.recv(data_len - len(data))
                        if not buff:
                            logger.warn('screenshot socket closed')
                            return
                        data += buff
                    except socket.error as e:
                        logger.warn('recv screenshot data error: %s' % e)
                        return
                return data
            
            def screenshot_thread():
                prev_image = None
                max_width = max_height = 0
                while True:
                    data = recv_data(24)
                    if not data: return
                    timestamp, left, top, width, height, data_len = struct.unpack('I' * 6, data)
                    if data_len > 0:
                        data = recv_data(data_len)
                        assert(len(data) == data_len)
                        fp = BytesIO(data)
                        image = Image.open(fp)
                        # image.verify()
                        w, h = image.size
                        if w > max_width: max_width = w
                        if h > max_height: max_height = h
                        if w < max_width or h < max_height:
                            # 此时prev_image一定不为空
                            try:
                                prev_image.paste(image, (left, top, left + width, top + height))
                            except Exception as e:
                                err_msg = 'compose image [%s]%r failed: %s' % (data_len, (left, top, width, height), e)
                                raise RuntimeError(err_msg)
                        else:
                            prev_image = image
                    for callback in self._screenshot_callbacks:
                        try:
                            callback(copy.deepcopy(prev_image))
                        except:
                            logger.exception('run callback %s failed' % callback.__name__)
            self._screenshot_thread = threading.Thread(target=screenshot_thread)
            self._screenshot_thread.setDaemon(True)
            self._screenshot_thread.start()
        else:
            if not callback in self._screenshot_callbacks: self._screenshot_callbacks.append(callback)
    
    def unregister_screenshot_callback(self, callback):
        '''注销截图回调函数
        
        :param callback: 回调函数
        :type  callback: function
        '''
        if hasattr(self, '_screenshot_callbacks') and callback in self._screenshot_callbacks:
            self._screenshot_callbacks.remove(callback)
 
    def resolve_domain(self, domain):
        '''解析域名
        '''
        return self._device_driver.resolve_domain(domain)

    def set_radio_enabled(self, enable):
        '''是否启用Radio
        '''
        return self._device_driver.set_radio_enabled(enable)

    def get_system_timezone(self):
        '''获取当前系统时区
        '''
        return self.adb.get_property('persist.sys.timezone')

    def set_system_timezone(self, new_timezone='Asia/Shanghai'):
        '''修改系统时区
        '''
        if self.get_system_timezone() != new_timezone:
            self.adb.set_property('persist.sys.timezone', new_timezone)
            
    def set_system_time(self, new_time=None):
        '''设置系统时间

        :param new_time: 新时间,默认为PC上的时间,格式为: 20151001.170000
        :type  new_time: str
        '''
        if not new_time:
            new_time = time.strftime("%Y%m%d.%H%M%S", time.localtime())
        self.adb.run_shell_cmd('date -s %s' % new_time, self.adb.is_rooted())

    def get_available_data_storage(self):
        '''获取数据存储区可用空间
        '''
        return self._device_driver.get_available_storage('/data')

    def get_available_external_storage(self):
        '''获取sdcard可用存储空间
        '''
        return self._device_driver.get_available_storage('/sdcard')

if __name__ == '__main__':
    pass
        
    
