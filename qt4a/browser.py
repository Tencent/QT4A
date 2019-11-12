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

'''Android端浏览器封装
'''

import re
import time

from qt4a.andrcontrols import Window, TextView, WebView
from qt4a.androidapp import AndroidApp
from qt4a.device import Device
from qt4a.qpath import QPath
from qt4w.browser import IBrowser
from qt4w.webcontrols import WebPage

class QT4ABrowser(AndroidApp, IBrowser):
    '''QT4A助手实现的浏览器功能
    '''
    package_name = 'com.test.androidspy'
    process_name = package_name + ':browser'
    
    def __init__(self, device=None):
        if not device:
            from testbase import context
            tc = context.current_testcase()
            if tc:
                device = tc.acquire_device()
            else:
                # 使用本地设备
                device = Device()
        super(QT4ABrowser, self).__init__(self.process_name, device)
        
    def open_url(self, url, page_cls=None):
        '''打开一个url，返回page_cls类的实例
        
        :param url: 要打开页面的url
        :type url:  string
        :param page_cls: 要返回的具体WebPage类,为None表示返回WebPage实例
        :type page_cls: Class
        '''
        self.device.start_activity(self.package_name + '/' + QT4ABrowserWindow.Activity, data_uri=url)
        if page_cls == None: page_cls = WebPage
        browser_window = QT4ABrowserWindow(self)
        webview = browser_window.Controls['WebView']
        return page_cls(webview)
        
    def find_by_url(self, url, page_cls=None, timeout=10):
        '''在当前打开的页面中查找指定url,返回WebPage实例，如果未找到，返回None
        
        :param url: 要查找的页面url
        :type url:  string
        :param page_cls: 要返回的具体WebPage类,为None表示返回WebPage实例
        :type page_cls: Class
        :param timeout: 查找超时时间，单位：秒
        :type timeout: int/float
        '''
        time0 = time.time()
        if page_cls == None: page_cls = WebPage
        pattern = re.compile(url)
        while time.time() - time0 < timeout:
            browser_window = QT4ABrowserWindow(self)
            webview = browser_window.Controls['WebView']
            page = page_cls(webview)
            page_url = page.url
            if page_url == url or pattern.match(page_url): return page
            time.sleep(1)
        else:
            raise RuntimeError('find url %s failed' % url)

    def clear_data(self):
        '''清理浏览器数据
        '''
        self.device.adb.kill_process(QT4ABrowserWindow.Process)
        dir_path = '/data/data/%s/app_webview' % self.package_name
        cmdline = 'rm -r %s' % dir_path
        self.run_shell_cmd(cmdline)

    def close(self):
        '''关闭窗口
        '''
        browser_window = QT4ABrowserWindow(self)
        browser_window.close()


class QT4ABrowserWindow(Window):
    '''QT4A浏览器窗口
    '''
    Activity = QT4ABrowser.package_name + '.activity.BrowserActivity'
    Process = QT4ABrowser.process_name
    
    def __init__(self, browser):
        super(QT4ABrowserWindow, self).__init__(browser)
        self.updateLocator({'标题': {'type': TextView, 'root': self, 'locator': QPath('/Id="text_title"')},
                            'WebView': {'type': WebView, 'root': self, 'locator': QPath('/Id="webView1"')},
                            })

