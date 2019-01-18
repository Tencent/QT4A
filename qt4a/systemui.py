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

'''封装系统窗口控件
'''

import os

from tuia.exceptions import ControlNotFoundError
from qt4a.qpath import QPath
from qt4a.andrcontrols import Window, View, TextView, Button, GridView

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
            pattern = re.compile(r'很抱歉，“.+”已停止运行。')
            if pattern.match(message):
                return window
        except ControlNotFoundError:
            return None

    def close(self):
        '''关闭
        '''
        self.Controls['确定'].click()


class PastePopup(Window):
    '''弹出式粘贴按钮
    '''
    Activity = r'^PopupWindow:\w{7,8}$'

    def __init__(self, app):
        super(PastePopup, self).__init__(app, False)
        self.updateLocator({'粘贴': {'type': TextView, 'root': self, 'locator': QPath('/Text="%s"' % self._app.get_string_resource('paste'))},  # 粘贴
                            '替换': {'type': TextView, 'root': self, 'locator': QPath('/Text="替换..."')},
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


if __name__ == '__main__':
    pass
