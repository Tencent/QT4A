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

'''封装状态栏、通知栏等控件
'''

import os
from qpath import QPath
from andrcontrols import Window, WebView, View, TextView, EditText, ImageView, ScrollView, ListView, Button, RelativeLayout, GridView
from tuia.exceptions import ControlNotFoundError

def get_file_md5(filepath):
    '''计算文件MD5值
    '''
    import hashlib
    with open(filepath, 'rb') as f:
        md5obj = hashlib.md5()
        md5obj.update(f.read())
        hash = md5obj.hexdigest()
        return hash

class StatusBarWindow(Window):
    '''状态栏和通知栏
    '''
    Activity = 'com.android.systemui.statusbar.phone.StatusBarWindowView'

    def __init__(self, driver):
        super(StatusBarWindow, self).__init__(driver)
        self.updateLocator({'状态栏': {'type': View, 'root': self, 'locator': QPath('/Id="status_bar"')},
                            '通知栏 ': {'type': View, 'root': self, 'locator': QPath('/Id="notification_panel"')},
                            '通知栏图标': {'type': View, 'root': '@状态栏', 'locator': QPath('/Id="notificationIcons"')},
                            }
                           )

    def get_notify_icon_list(self):
        '''获取通知栏图标列表
        '''
        return self.Controls['通知栏图标'].children


#========================= Android 4.0.3 ================================================

class StatusBar(Window):
    '''状态栏
    '''
    Activity = 'StatusBar'

    def __init__(self, driver):
        super(StatusBar, self).__init__(driver)
        self.updateLocator({'通知图标列表': {'type': ListView, 'root': self, 'locator': QPath('/Id="notificationIcons"')},  # com.android.systemui.statusbar.phone.IconMerger
                            'Wifi': {'type': ImageView, 'root': self, 'locator': QPath('/Id="wifi_signal"')},
                            '手机信号': {'type': ImageView, 'root': self, 'locator': QPath('/Id="mobile_signal"')},
                            '电池': {'type': ImageView, 'root': self, 'locator': QPath('/Id="battery"')},
                            '时间': {'type': TextView, 'root': self, 'locator': QPath('/Id="clock"')}
                            })

class StatusBarExpanded(Window):
    '''通知栏
    '''
    Activity = 'StatusBarExpanded'

    def __init__(self, driver):
        super(StatusBarExpanded, self).__init__(driver)
        self.updateLocator({'日期': {'type': TextView, 'root': self, 'locator': QPath('/Id="content" /Id="data" && MaxDepth="4"')},
                            '设置': {'type': ImageView, 'root': self, 'locator': QPath('/Id="settings_button"')},
                            '清除': {'type': ImageView, 'root': self, 'locator': QPath('/Id="clear_all_button"')},
                            'Main': {'type': ScrollView, 'root': self, 'locator': QPath('/Id="content" /Id="scroll" && MaxDepth="3"')},
                            '通知列表': {'type': ListView, 'root': '@Main', 'locator': QPath('/Id="latestItems"')},
                            '图标': {'type': ImageView, 'root': '@通知列表', 'locator': QPath('/Id="status_bar_latest_event_content" /Id="icon"')},
                            '标题': {'type': TextView, 'root': '@通知列表', 'locator': QPath('/Id="status_bar_latest_event_content_large_icon" /Id="line1" /Id="title"')},
                            '时间': {'type': TextView, 'root': '@通知列表', 'locator': QPath('/Id="status_bar_latest_event_content_large_icon" /Id="line1" /Id="time"')},  # DateTimeView
                            '内容': {'type': TextView, 'root': '@通知列表', 'locator': QPath('/Id="status_bar_latest_event_content_large_icon" /Id="line3" /Id="text"')},
                            })

    @staticmethod
    def pull_down_status_bar(driver):
        '''拉下通知栏，如果已经拉下，则不操作
        '''
        import time
        if driver.get_current_activity() != StatusBarExpanded.Activity:
            status_bar = StatusBar(driver)
            rect = status_bar.bounding_rect
            x1 = (rect[0] + rect[2]) / 2
            y1 = (rect[1] + rect[3]) / 2
            driver.drag(x1, y1, x1, y1 + 500)  # 是否需要将终点设为屏幕中点？
        timeout = 2
        while timeout >= 0:
            if driver.get_current_activity() == StatusBarExpanded.Activity:
                return StatusBarExpanded(driver)
            time.sleep(0.5)
            timeout -= 0.5
        return None

class Toast(Window):
    '''封装Toast
    '''
    Activity = 'Toast'

    def __init__(self, driver):
        super(Toast, self).__init__(driver, False)
        self.updateLocator({'消息': {'type': TextView, 'root': self, 'locator': QPath('/Id="message"')},
                            })

    def _find_message(self, msg):
        '''查找消息
        '''
        if not self.Controls['消息'].exist(): return ''
        if msg != '' and not msg in self.message: return ''
        return self.message


    @property
    def message(self):
        '''显示的消息文本
        '''
        from qt4a.androiddriver.androiddriver import AndroidSpyError
        try:
            return self.Controls['消息'].text
        except AndroidSpyError:
            return ''

    @classmethod
    def wait_for_message(cls, app, msg='', timeout=10, interval=0.2):
        '''等待toast出现
        '''
        # 2014/10/08 banana 增加interval参数
        import time
        time0 = time.time()
        while time.time() - time0 < timeout:
            toast = cls(app)  # 可能会有多个toast
            ret = toast._find_message(msg)
            if ret: return ret
            time.sleep(interval)
        raise RuntimeError('未找到Toast')

    @classmethod
    def wait_for_message_disappear(cls, app, msg='', timeout=10):
        '''等待Toast消失
        '''
        import time
        cls.wait_for_message(app, msg, timeout=timeout)
        time0 = time.time()
        while time.time() - time0 < timeout:
            toast = cls(app)
            try:
                ret = toast._find_message(msg)
                if not ret: return True
            except ControlNotFoundError:
                return True
            time.sleep(0.2)

class CrashWindow(Window):
    '''Crash窗口
    '''
    Activity = 'Application'

    def __init__(self, app):
        super(CrashWindow, self).__init__(app)
        self.updateLocator({'提示': {'type': TextView, 'root': self, 'locator': QPath('/Id="message"')},
                            '确定': {'type': Button, 'root': self, 'locator': QPath('/Id="button1"')},
                            })

    @staticmethod
    def findCrashWindow(app):
        window = CrashWindow(app)
        try:
            message = window.Controls['提示'].text
            import re
            pattern = re.compile(r'很抱歉，“.+”已停止运行。')
            if pattern.match(message):
                return window
        except ControlNotFoundError:
            return None

    def close(self):
        '''关闭
        '''
        self.Controls['确定'].click()

class BrowserWebView(WebView):
    '''浏览器WebView
    '''
    @property
    def bounding_rect(self):  # TODO: 标题栏问题
        '''left, top, width, height
        '''
        root_rect = super(BrowserWebView, self).bounding_rect
        if self.container['标题栏'].visibility:
            titlebar_rect = self.container['标题栏'].bounding_rect
            return root_rect[0] + titlebar_rect[0], \
                root_rect[1] + titlebar_rect[1], \
                root_rect[2] - titlebar_rect[2], \
                root_rect[3] - titlebar_rect[3],
        else:
            return root_rect

class TitleBar(RelativeLayout):
    '''标题栏
    '''
    @property
    def visibility(self):
        return self._driver.get_object_field_value(self.hashcode, 'mShowing')

class UrlInputView(EditText):
    pass



class PastePopup(Window):
    '''弹出式粘贴按钮
    '''
    Activity = r'^PopupWindow:\w{8}$'

    def __init__(self, mqapp):
        super(PastePopup, self).__init__(mqapp, False)
        self.updateLocator({'粘贴': {'type': TextView, 'root': self, 'locator': QPath('/Text="%s"' % self._app.get_string_resource('paste'))},  # 粘贴
                            '替换': {'type': TextView, 'root': self, 'locator': QPath('/Text="替换..."')},
                            })

class AppChoosePanel(Window):
    '''应用选择面板
    '''
    Activity = 'com.android.internal.app.ChooserActivity'

    def __init__(self, app):
        super(AppChoosePanel, self).__init__(app)
#        self.updateLocator({'GridView': {'type': GridView, 'root': self, 'locator': QPath('/Id="resolver_grid"')},
#                            '应用名': {'type': TextView, 'root': '@GridView', 'locator': QPath('/Id="text1"')},
#                            })

    @staticmethod
    def create(app):
        '''工厂方法
        '''
        sdk_ver = app.device.sdk_version
        cls = None
        if sdk_ver <= 14:
            cls = AppChoosePanel_2_2
        elif sdk_ver in (15, 16):
            cls = AppChoosePanel_4_1
        return cls(app)

    def choose_file(self, file_path):
        '''选择文件
        '''
        sdcard_path = self.device.get_external_sdcard_path()
        ext_name = os.path.splitext(file_path)[-1]
        save_path = sdcard_path + '/QT4A/%s%s' % (get_file_md5(file_path), ext_name)
        # print save_path
        self.device.push_file(file_path, save_path)
        # uri = self.device.refresh_media_store(save_path)
        self.device.adb.run_shell_cmd('am startservice -n com.test.qt4amockapp/.MockerService')
        self.device.adb.run_shell_cmd('am broadcast -a setMockUri --es uri file://%s' % save_path)
        self.select('QT4AMockApp')

    def select(self, app_name):
        '''选择指定应用
        '''
        for app in self.Controls['GridView']:
            if app['应用名'].text == app_name:
                app.click()
                return
        raise RuntimeError('未找到指定应用：%s' % app_name)

class AppChoosePanel_2_2(AppChoosePanel):
    '''Android2.2
    '''
    def __init__(self, app):
        super(AppChoosePanel_2_2, self).__init__(app)
        self.updateLocator({'GridView': {'type': GridView, 'root': self, 'locator': QPath('/Id="select_dialog_listview"')},  # com.android.internal.app.AlertController$RecycleListView
                            '应用名': {'type': TextView, 'root': '@GridView', 'locator': QPath('/Id="text1"')},
                            })

class AppChoosePanel_4_1(AppChoosePanel):
    '''Android4.1
    '''
    def __init__(self, app):
        super(AppChoosePanel_4_1, self).__init__(app)
        self.updateLocator({'GridView': {'type': GridView, 'root': self, 'locator': QPath('/Id="resolver_grid"')},
                            '应用名': {'type': TextView, 'root': '@GridView', 'locator': QPath('/Id="text1"')},
                            })

class AppResolverPanel(Window):
    '''选择响应某个Intent请求的应用
    '''
    Activity = 'com.android.internal.app.ResolverActivity'
    
    def __init__(self, app):
        super(AppResolverPanel, self).__init__(app)
        self.updateLocator({'应用列表': {'type': GridView, 'root': self, 'locator': QPath('/Id="resolver_grid"')},
                            '应用名': {'type': TextView, 'root': '@应用列表', 'locator': QPath('/Id="text1"')},
                            '始终': {'type': Button, 'root': self, 'locator': QPath('/Id="button_always"')},
                            '仅此一次': {'type': Button, 'root': self, 'locator': QPath('/Id="button_once"')},
                            })
        
class AppNoResponseWindow(Window):
    '''应用不响应
    '''
    Activity = r'^\w{8}$'  # 其实获取到的只是窗口的hashcode

    def __init__(self, app):
        super(AppNoResponseWindow, self).__init__(app)
        self.updateLocator({'提示语': {'type': TextView, 'root': self, 'locator': QPath('/Id="message"')},
                            '等待': {'type': Button, 'root': self, 'locator': QPath('/Id="button2"')},
                            '确定': {'type': Button, 'root': self, 'locator': QPath('/Id="button1"')},
                            })

class BrowserWindow(Window):
    '''Android自带浏览器窗口
    '''
    Activity = 'com.android.browser.BrowserActivity'

    def __init__(self, app):
        super(BrowserWindow, self).__init__(app)
        self.updateLocator({'标题栏': {'type': TitleBar, 'root': self, 'locator': QPath('/Id="main_content" /Instance="2"')},
                            '地址栏': {'type': UrlInputView, 'root': '@标题栏', 'locator': QPath('/Id="url"')},
                            'WebView': {'type': BrowserWebView, 'root': self, 'locator': QPath('/Id="webview_wrapper" /Instance="1"')},
                            })
        
try:
    from webcontrols import WebPage, WebElement
except ImportError:
    pass
else:
    class BrowserWebPage(WebPage):
        '''浏览器页面基类
        '''
        def __init__(self, browser):
            browser_window = BrowserWindow(browser)
            super(BrowserWebPage, self).__init__(browser_window.Controls['WebView'])
            
if __name__ == '__main__':
    pass
