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

'''Android App基类
'''

# 2013/5/30 apple 创建

import time
import threading
from tuia.exceptions import ControlNotFoundError
from qt4a.androiddriver.androiddevice import AndroidDevice
from qt4a.androiddriver.androiddriver import AndroidDriver
from qt4a.androiddriver.util import logger, ThreadEx, EnumThreadPriority
from qt4a.device import Device

class AndroidApp(object):
    '''Android App基类
    '''
    package_name = ''

    def __init__(self, process_name, device=None):
        if isinstance(device, (AndroidDevice, Device)):
            self._device = device
        elif isinstance(device, (str, unicode)):
            self._device = AndroidDevice(device)
        else:
            self._device = Device()

        if not self._device.is_app_installed(self.package_name):
            time.sleep(60)  # 这段时间手Q测试中会出现设备死机的问题,此时会报应用未安装的错误,通过sleep来减少失败用例
            raise RuntimeError('应用：%s 尚未安装' % self.package_name)

        self._drivers = {}  # 如果应用存在多个被测进程，就会有多个driver
        self._process_name = process_name  # 主程序名
        
        self._monitor_task_list = []
        self._monitor_run = True
        
        self._app_crashed = False
        self._device.wake_screen()  # 唤醒屏幕
        self._device.unlock_keyguard()  # 解屏幕锁
        self._close_other_window()
        self._main_thread_id = threading.current_thread().ident  # 创建该对象的线程一定是主线程
        self._monitor_thread = None
        self.start_monitor()
        self.add_monitor_task(self._detect_crash_window)

    @property
    def device(self):
        '''返回所在的设备
        '''
        return self._device

    @property
    def process_name(self):
        '''应用所在的主进程名
        '''
        return self._process_name

    @process_name.setter
    def process_name(self, name):
        self._process_name = name

    @property
    def crashed(self):
        return self._app_crashed

    def get_driver(self, process_name=''):
        '''根据进程名获取driver对象，默认为主程序driver
        '''
        if not process_name:
            if not self._process_name: raise RuntimeError('主程序名为空')
            process_name = self._process_name
        if not self._drivers.has_key(process_name):
            # 只有尚未创建的时候才需要互斥
            # logger.debug('wait for %s create driver' % process_name)
            # 创建driver
            driver = AndroidDriver.create(process_name, self._device)
            self._drivers[process_name] = driver
            # logger.debug('%s create driver success' % process_name)
        driver = self._drivers[process_name]
        return driver
    
    def close_driver(self, process_name):
        '''关闭测试桩
        '''
        self._drivers[process_name].close()
        del self._drivers[process_name]

    def wait_for_activity(self, activity, timeout=5, interval=0.5):
        '''等待Activity打开
        
        :param activity: Activtiy名称
        :type activity:  string
        :param timeout:  超时时间，单位：S
        :type timeout:   int/float
        :param interval: 检查间隔时间，单位：S
        :type interval:  int/float
        '''
        time0 = time.time()
        while time.time() - time0 < timeout:
            if self.crashed:
                raise RuntimeError('%s Crashed' % self.__class__.__name__)
            current_activity = self.device.get_current_activity()
            # print 'current_activity', current_activity
            if current_activity == activity: return True
            time.sleep(interval)
        raise ControlNotFoundError('等待Activity：%s 超时，当前Activity: %s' % (activity, current_activity))

    def drag(self, direction='right', count=1):
        '''滑动屏幕，适合一大块区域（如引导屏）的滑动，无需关心具体的控件
        :param direction: 方向，right、left、top、bottom
        :type direction:  string
        :param count: 次数
        :type count:  int
        '''
        width, height = self.device.screen_size
        mid_width = width / 2
        mid_height = height / 2
        x1 = x2 = mid_width
        y1 = y2 = mid_height
        if direction == 'right':
            x1 -= 50
            x2 += 50
        elif direction == 'left':
            x1 += 50
            x2 -= 50
        elif direction == 'top':
            y1 += 50
            y2 -= 50
        elif direction == 'bottom':
            y1 -= 50
            y2 += 50
        else:
            raise RuntimeError('不支持的方向：%s' % direction)

        for _ in range(count):
            self.get_driver().drag(x1, y1, x2, y2)
            time.sleep(0.5)

    def shake(self, process_name='', duration=4, interval=0.05):
        '''模拟摇一摇功能
        
        :param process_name: 要模拟的进程名，默认为主进程
        :type process_name:  string
        :param duration:     持续时间，单位：秒
        :type duration:      int
        :param interval:     发送的时间间隔
        :type interval:      float
        '''
        return self.get_driver(process_name).shake(duration, interval)

    def send_back_key(self):
        '''发送返回按键
        '''
        self._device.send_key(4)
    
    def send_key(self, key):
        '''发送单个按键
        :param key: 发送的按键字符串
        :type key:  string
        '''
        self.get_driver().send_key(key)
        
    def send_home_key(self):
        '''发送Home键
        '''
        self._device.send_key(3)
        
    def send_menu_key(self):
        '''发送菜单键
        '''
        self.get_driver().send_key('{MENU}')

    def close(self):
        '''关闭所有打开的driver
        '''
        # self.remove_monitor_task(self._detect_crash_window)
        self.remove_all_task()
        self.stop_monitor()
        for key in self._drivers.keys():
            self._drivers[key].close()
        self._drivers = {}

    def _close_other_window(self):
        '''关闭会影响用例执行的窗口
        '''
        import re
        from systemui import CrashWindow, AppNoResponseWindow, AppResolverPanel, StatusBar
        current_activity = self.device.get_current_activity()
        logger.debug('current_activity: %s' % current_activity)
        pattern = re.compile(AppNoResponseWindow.Activity)
        if current_activity == StatusBar.Activity:
            self.send_back_key()
        elif current_activity == CrashWindow.Activity or pattern.match(current_activity):
            # 如果是Crash窗口
            self.device.send_key(66)
            timeout = 10
            time0 = time.time()
            while time.time() - time0 < timeout:  # 等待窗口消失
                current_activity = self.device.get_current_activity()
                if current_activity == CrashWindow.Activity or pattern.match(current_activity):
                    time.sleep(0.5)
                    self.device.send_key(66)
                else:
                    return
            self.device.send_key(4)
        elif current_activity == AppResolverPanel.Activity:
            self.device.send_key(4)
            
    def _handle_system_crash_window(self):
        '''处理系统Crash窗口
        '''
        from systemui import CrashWindow
        crash_window = CrashWindow.findCrashWindow(self)
        if not crash_window: return False
        logger.error('detect crash window')
        crash_window.close()
        return True

    def _detect_crash_window(self):
        '''检测Crash窗口
        '''
        from systemui import CrashWindow
        current_activity = self.device.get_current_activity()
        # print current_activity
        if current_activity == CrashWindow.Activity:
            # TODO:Crash时测试桩无法获取当前进程名
            # if self._handle_system_crash_window(): return True
            self.on_crashed()
            return True

    def on_crashed(self):
        '''发生Crash之后的处理
        '''
        logger.error('detect crash')
        self._app_crashed = True
        self._monitor_run = False

    def add_monitor_task(self, task, last_time=0):
        '''添加监控任务
        '''
        if last_time > 0: last_time += time.time()
        self._monitor_task_list.append((task, last_time))
        logger.debug('add task: %s' % task.__name__)
        
    def remove_monitor_task(self, task):
        '''移除监控任务
        '''
        for item in self._monitor_task_list:
            if item[0] == task:
                self._monitor_task_list.remove(item)
                logger.debug('remove task: %s' % task.__name__)
                return True
        return False

    def remove_all_task(self):
        '''移除所有任务
        '''
        self._monitor_task_list = []
    
    def start_monitor(self):
        '''启动监控
        '''
        if self._monitor_thread: return
        self._monitor_run = True
        t = ThreadEx(target=self.monitor_thread, name='QT4A App Monitor Thread')
        t.setDaemon(True)
        t.start()
        self._monitor_thread = t
        
    def stop_monitor(self):
        '''停止检测
        '''
        if not self._monitor_thread: return
        self._monitor_run = False
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(30)
        self._monitor_thread = None
        
    def monitor_thread(self):
        '''监控线程
        '''
        interval = 1
        while self._monitor_run:
            for task, task_end_time in self._monitor_task_list:
                time_now = time.time()
                if task_end_time == 0 or (task_end_time > 0 and time_now < task_end_time):
                    try:
                        task()
                        time.sleep(0.1)
                    except:
                        logger.exception('run task %s failed' % task.__name__)
                        self._resume_main_thread()  # 防止出错后主线程阻塞一段时间
            time.sleep(interval)
        
    def get_string_resource(self, string_id, lang=''):
        '''获取字符串资源
        :param string_id: 字符串ID
        :type string_id:  string
        :param lang: 字符串语言，默认为当前系统语言
        :type lang:  string
        '''
        return self.device.get_string_resource(self.package_name, string_id, lang)
    
    def _suspend_main_thread(self, max_wait_time=30):
        '''阻塞主线程
        '''
        if self._main_thread_id == threading.current_thread().ident: return  # 避免卡死
        for key in self._drivers.keys():
            driver = self._drivers[key]
            driver.suspend_thread(self._main_thread_id, max_wait_time)
    
    def _resume_main_thread(self):
        '''解锁主线程
        '''
        if self._main_thread_id == threading.current_thread().ident: return
        for key in self._drivers.keys():
            driver = self._drivers[key]
            driver.resume_thread(self._main_thread_id)
    
    def is_debug(self):
        '''是否是debug包
        '''
        return self.device.is_debug_package(self.package_name)
    
    def _is_use_int_view_id(self):
        '''是否使用整型控件ID
        '''
        if hasattr(self, '_use_int_view_id'): return self._use_int_view_id
        if not self.is_debug():
            logger.debug('release version')
            _, file_list = self.device.list_dir('/data/local/tmp')
            for file in file_list:
                if file['name'] == '%s_map.txt' % self.package_name:
                    self._use_int_view_id = True
                    return True
        logger.debug('map file not exist')
        self._use_int_view_id = False
        return False
    
    def _get_view_id(self, str_id):
        '''从控件字符串ID获取整型ID
        '''
        if not str_id: raise RuntimeError('控件ID不能为空')
        try:
            return self.device._get_view_id(self.package_name, str_id)
        except RuntimeError, e:
            logger.warn(str(e))
            return None
        
    def _get_drawable_resource_origin_name(self, confuse_name):
        '''获取图片资源的原始名称
        
        :param confuse_name: 混淆后的资源名称
        :type confuse_name:  string
        '''
        return self.device._get_resource_origin_name(self.package_name, 'drawable', confuse_name)
    
    def set_activity_popup(self, activity, popup=False, process_name=''):
        '''设置Activity是否可以弹窗
        '''
        return self.get_driver(process_name).set_activity_popup(activity, popup)
    
    def send_image(self, activity, image_path):
        '''向Activity发送图片，支持多图
        
        :param activity:  目标Activity名称
        :type activity:   string
        :param image_path:图片在PC上的路径或路径列表
        :type image_path: string | list
        '''
        self.device.send_image_to_app('%s/%s' % (self.package_name, activity), image_path)
    
    def send_file(self, activity, file_path):
        '''向Activity发送文件
        
        :param activity: 目标Activity名称
        :type activity:  string
        :param file_path:文件在PC上的路径
        :type file_path: string
        '''
        self.device.send_file_to_app('%s/%s' % (self.package_name, activity), file_path)
    
    def set_driver_thread_priority(self, process_name='', priority=EnumThreadPriority.FOREGROUND):
        '''设置测试线程优先级
        '''
        self.get_driver(process_name).set_thread_priority(priority)
    
    def set_location(self, latitude, longitude, process_name=''):
        '''给应用设置位置信息
        
        :param latitude: 纬度
        :type latitude:  float
        :param longitude:经度
        :type longitude: float
        '''
        from androiddriver.androidhookdriver import AndroidHookDriver
        driver = AndroidHookDriver(self.get_driver(process_name))
        return driver.set_location(latitude, longitude)
    
    def enable_system_alert_window(self):
        '''允许弹出悬浮窗口
        '''
        return self._device.set_app_permission(self.package_name, 'SYSTEM_ALERT_WINDOW', True)
    
class AndroidBrowser(AndroidApp):
    '''浏览器应用
    '''
    def __init__(self, url, device=None):
        process_name = 'com.android.browser'
        super(AndroidBrowser, self).__init__(process_name, device)
        self.device.kill_process(process_name)
        self.device.start_activity('com.android.browser/.BrowserActivity', 'android.intent.action.VIEW', data_uri=url)

    @staticmethod
    def open_url(url, device=None):
        return AndroidBrowser(url, device)

    @property
    def webpage(self):
        from systemui import BrowserWebPage
        return BrowserWebPage(self)

if __name__ == '__main__':
    pass
