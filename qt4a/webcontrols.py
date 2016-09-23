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

'''Android Web页面
'''

# 2013/6/25 apple 创建

import time
import re

from androiddriver.util import logger

use_qt4w = False

try:
    from testbase.testcase import Environ
    env = Environ()
    if env.has_key('USE_QT4W') and env['USE_QT4W'] == '1':
        use_qt4w = True
except ImportError:
    use_qt4w = True

if use_qt4w:
    from qt4w.webcontrols import WebPage, WebElement
else:
    for _ in range(3):
        try:
            from tuia._autoweb import XPath
            break
        except Exception, e:
            if 'CoInitialize' in str(e):
                import pythoncom
                pythoncom.CoInitialize()
            else:
                logger.exception('import XPath error')
    else:
        raise ImportError('from tuia._autoweb import XPath failed')

    from tuia._autoweb.webkit import _webkit as webkit
    from androiddriver.webdriver import WebDriver
    
    from andrcontrols import Window, ScrollView, VerticalSwipe
    
    class WebElement(object):
        '''页面元素
        '''
        def __init__(self, root, locator):
            self._root = root
            self._parent = root
            self._locator = locator
            self.__obj = None
            self._ui_map = {}
            
        @property
        def _obj(self):
            if self.__obj == None:
                class WebElementWrapper(webkit.WebElement):
                    '''
                    '''
                    def _wait(self, func, timeout=10, interval=0.5):
                        '''重写该方法，延长超时时间
                        '''
                        return super(WebElementWrapper, self)._wait(func, timeout, interval)
                try:
                    self.__obj = WebElementWrapper(self._root, self._locator)
                except AttributeError, e:
                    # 防止出现AttributeError是进入无穷递归
                    import traceback
                    traceback.print_exc()
                    raise RuntimeError(e)
    
            return self.__obj
        
        def exist(self):
            '''检查元素是否有效
            
            :rtype: bool
            :return: 定位成功为True，不成功为False
            '''
            try:
                self._obj
                return True
            except:
                return False
    
        def __getattr__(self, attr):
            return getattr(self._obj, attr)
        
        def __setattr__(self, attr, value):
            if attr[0] == '_':
                self.__dict__[attr] = value
            else:
                return setattr(self._obj, attr, value)
        
        def __str__(self):
            return '<%s object at 0x%.8X XPath="%s">' % (self.__class__.__name__, id(self), self._locator)
        
        @property
        def Displayed(self):
            '''当前元素是否显示
            
            :rtype: bool
            :return: 元素是否显示
            '''
            if not self._obj.Displayed: return False
            rect = self._obj.BoundingRect
            if rect.Width == 0 or rect.Height == 0: return False
            return True
        
        @property
        def visible(self):
            '''控件是否视觉可见
            '''
            root_rect = self._page.container.rect
            self_rect = self.BoundingRect
            if self_rect.Left >= root_rect[0] and \
                self_rect.Left + self_rect.Width <= root_rect[0] + root_rect[2] and \
                self_rect.Top >= root_rect[1] and \
                self_rect.Top + self_rect.Height <= root_rect[1] + root_rect[3]:
                return True
            return False
        
        def wait_for_visible(self, timeout=10, interval=0.1):
            '''等待控件可见
            
            :param timeout: 超时时间
            :type timeout:  float
            :param interval:查询间隔时间
            :type interval: float
            '''
            from tuia.util import Timeout
            from tuia.exceptions import TimeoutError
            try:
                Timeout(timeout, interval).waitObjectProperty(self, 'visible', True)
            except TimeoutError:
                raise TimeoutError('控件:%s 未在%sS内出现，当前坐标为：%s' % (self, timeout, self.BoundingRect))
            
        def scroll_to_visible(self):
            '''滚动到可视区域
            '''
            timeout = 20
            time0 = time.time()
            while time.time() - time0 < timeout:
                root_rect = self._page.container.rect
                self_rect = self.BoundingRect
    
                if self_rect.Left >= root_rect[0] and \
                    self_rect.Left + self_rect.Width <= root_rect[0] + root_rect[2] and \
                    self_rect.Top >= root_rect[1] and \
                    self_rect.Top + self_rect.Height <= root_rect[1] + root_rect[3]:
                    return
                
                mid_x = self_rect.Left + self_rect.Width / 2
                mid_y = self_rect.Top + self_rect.Height / 2
                delta = 10  # 中心点四周delta像素可见也认为控件可见
                if mid_x - delta >= root_rect[0] and \
                    mid_x + delta <= root_rect[0] + root_rect[2] and \
                    mid_y - delta >= root_rect[1] and \
                    mid_y + delta <= root_rect[1] + root_rect[3]:
                    return
                elif mid_y - delta < root_rect[1]:
                    # 需要下滑
                    self._page.container.swipe_down()
                elif mid_y + delta > root_rect[1] + root_rect[3]:
                    # 需要上滑
                    self._page.container.swipe_up()
                else:
                    # 左滑和右滑需要判断滑动的区域
                    parent = self._parent
                    while not isinstance(parent, WebPage):
                        if parent.visible: break
                        parent = parent._parent
                    if isinstance(parent, WebPage):
                        parent = parent._container
                    if mid_x < root_rect[0]:  # 右滑
                        parent.swipe('right')
                    elif mid_x >= root_rect[0] + root_rect[2]:  # 左滑
                        parent.swipe('left')
                    else:
                        return
                time.sleep(0.5)
                
        def click(self, xOffset=None, yOffset=None):
            '''鼠标左键单击
            @type xOffset: int
            @param xOffset: 距离控件区域左上角的横向偏移。
            @type yOffset: int
            @param yOffset: 距离控件区域左上角的纵向偏移。
            '''
            self.scroll_to_visible()  # 自动滚动到可视区域
            x, y = self._get_cursor_pos(xOffset, yOffset)
            self._page.container._driver.click(self._page.container.hashcode, x, y)
    
        def doubleClick(self, xOffset=None, yOffset=None):
            '''鼠标左键双击
            @type xOffset: int
            @param xOffset: 距离控件区域左上角的横向偏移。
            @type yOffset: int
            @param yOffset: 距离控件区域左上角的纵向偏移。
            '''
            # x, y = self._get_cursor_pos(xOffset, yOffset)
            raise NotImplementedError
    
        def rightClick(self, xOffset=None, yOffset=None):
            '''鼠标右键单击
            @type xOffset: int
            @param xOffset: 距离控件区域左上角的横向偏移。
            @type yOffset: int
            @param yOffset: 距离控件区域左上角的纵向偏移。
            '''
            # x, y = self._get_cursor_pos(xOffset, yOffset)
            raise NotImplementedError
    
        def hover(self, xOffset=None, yOffset=None):
            '''鼠标悬停
            @type xOffset: int
            @param xOffset: 距离控件区域左上角的横向偏移。
            @type yOffset: int
            @param yOffset: 距离控件区域左上角的纵向偏移。
            '''
            # x, y = self._get_cursor_pos(xOffset, yOffset)
            raise NotImplementedError
    
        def drag(self, toX, toY):
            '''拖放到指定位置
            @type toX: int:
            @param toX: 拖放终点的屏幕坐标。
            @type toY: int:
            @param toY: 拖放终点的屏幕坐标。
            '''
            x, y = self._get_cursor_pos()
            self._page.container._driver.drag(x, y, toX, toY)
    
        def sendKeys(self, keys):
            '''发送按键命令
            @type keys: str
            @param keys: 要发送的按键
            '''
            self.click()
            self._page.container._driver.send_keys(keys)
        
        def control(self, name):
            '''获取子控件实例
            '''
            if not (name in self._ui_map):
                raise NameError("%s没有名为'%s'的子控件！" % (type(self), name))
            ui_control = self._ui_map[name]
            ui_type = self._page.ui_control_type
            if isinstance(ui_control, dict):
                if 'type' in ui_control: ui_type = ui_control['type']
            else:
                if not isinstance(ui_control, XPath):
                    raise TypeError('控件：%s 定义错误' % name)
                self._ui_map[name] = {'locator': ui_control}
            instance = ui_type(self, self._ui_map[name]['locator'])
            if 'ui_map' in self._ui_map[name]:
                instance._ui_map = self._ui_map[name]['ui_map']
            return instance
        
        def swipe(self, direct):
            '''滑动
            
            :param direct: 方向
            :type direct:  string，只能是“up”、“down”、“left”、“right”中的一个值
            '''
            # 先保证控件在可见范围
            logger.debug('swipe %s' % direct)
            self.scroll_to_visible()
            root_rect = self._page.container.rect
            self_rect = self.BoundingRect
            self_rect = [self_rect.Left, self_rect.Top, self_rect.Width, self_rect.Height]
            # 计算交集,控件可能没有完全在可见区域
            if self_rect[0] < root_rect[0]:
                self_rect[0] = root_rect[0]
            if self_rect[1] < root_rect[1]:
                self_rect[1] = root_rect[1]
            if self_rect[0] + self_rect[2] > root_rect[0] + root_rect[2]:
                self_rect[2] = root_rect[0] + root_rect[2] - self_rect[0]
            if self_rect[1] + self_rect[3] > root_rect[1] + root_rect[3]:
                self_rect[3] = root_rect[1] + root_rect[3] - self_rect[1]
                
            rect = self_rect
            if direct == 'up':
                x1 = x2 = rect[0] + rect[2] / 2
                y1 = rect[1] + rect[3] * 2 / 3
                y2 = rect[1] + rect[3] / 3
            elif direct == 'down':
                x1 = x2 = rect[0] + rect[2] / 2
                y1 = rect[1] + rect[3] / 3
                y2 = rect[1] + rect[3] * 2 / 3
            elif direct == 'left':
                y1 = y2 = rect[1] + rect[3] / 2
                x1 = rect[0] + rect[2] * 2 / 3
                x2 = rect[0] + rect[2] / 3
            elif direct == 'right':
                y1 = y2 = rect[1] + rect[3] / 2
                x1 = rect[0] + rect[2] / 3
                x2 = rect[0] + rect[2] * 2 / 3
            else:
                raise RuntimeError('direct参数只能是：up、down、left、right中的一个')  
    
            self._page._container._driver.drag(x1, y1, x2, y2)
            
    class WebPage(webkit.WebPage):
        '''Web页面
        '''
        ui_control_type = WebElement
        ui_map = {}
        
        def __init__(self, webview, locator=''):
            '''
            :param webview: WebView控件实例
            :type webview:  WebView
            :param locator: WebPage在页面中的xpath定位（iframe使用）
            :type locator:  string
            '''
            self._container = VerticalSwipe(webview)
            driver = WebDriver(webview)
            super(WebPage, self).__init__(driver, locator)
            self._ui_map = {}
            self._update_ui_map()
            
        @property
        def container(self):
            return self._container
        
        def _update_ui_map(self):
            '''从ui_map中更新控件信息
            '''
            import copy
            cls_list = []
            cls = self.__class__
            while cls != WebPage:
                cls_list.insert(0, cls)  # 基类在前，子类在后
                cls = cls.__base__
            last_cls = None
            for cls in cls_list:
                if cls.ui_map and (not last_cls or cls.ui_map != last_cls.ui_map):
                    # 防止某个类未定义ui_map
                    ui_map = copy.deepcopy(cls.ui_map)
                    self._ui_map.update(ui_map)
                last_cls = cls
        
        def update_ui_map(self, ui_map):
            '''从指定的ui_map中更新控件定义
            '''
            self._ui_map.update(ui_map)
            
        def control(self, name):
            '''获取控件实例
            '''
            if '.' in name:
                # 多层结构方式
                name_list = name.split('.')
                obj = self
                for name in name_list:
                    obj = obj.control(name)
                return obj
            
            if not (name in self._ui_map):
                raise NameError("%s没有名为'%s'的子控件！" % (type(self), name))
            ui_control = self._ui_map[name]
            ui_type = self.ui_control_type
            if isinstance(ui_control, dict):
                if 'type' in ui_control: ui_type = ui_control['type']
            else:
                if not isinstance(ui_control, XPath):
                    raise TypeError('控件：%s 定义错误' % name)
                self._ui_map[name] = {'locator': ui_control}
            instance = ui_type(self, self._ui_map[name]['locator'])
            if 'ui_map' in self._ui_map[name]:
                instance._ui_map = self._ui_map[name]['ui_map']
            return instance
        
        def waitForReady(self, timeout=60):
            '''等待页面加载完成
            @type timeout: int或float
            @param timeout: 最长等待的时间
            '''
            import time
            time0 = time.time()
            while time.time() - time0 < timeout:
                url = self.Url
                if url != '' and url != 'about:blank': break
                time.sleep(0.5)
            ret = self._driver.waitForReady(self._locators, timeout)
            return ret
    
        def execScript(self, script):
            '''在页面中执行脚本代码
            @type script: str
            @param script: 要执行的脚本代码
            @rtype: bool
            @return: js返回结果
            '''
            return self._container.eval_script(self._locators, script)
    
        def _get_rect(self):
            '''获取webview的位置
            '''
            from tuia.util import Rectangle
            return Rectangle(self._container.bounding_rect)
    
        def getElement(self, locator):
            '''在页面中查找元素，返回第一个匹配的元素
            @type locator: str或XPath
            @param locator: 查找条件，可以是XPath或元素ID
            @rtype: WebElement
            @return: 查找到的元素
            '''
            # 必须重载，否则始终会得到父类实例
            return WebElement(self, locator)
    
        def enable_remote_debug(self):
            '''启用远程调试
            '''
            import os, sys
            import win32process, win32event
            from tuia._autoweb.webkit import chrome
            weinre_domain = 'weinre.qq.com'  # gz.zat.cc:8081 已挂
            computer = os.popen("hostname").read().strip()
            debug_id = '%s_%s' % (computer, self.__class__.__name__)
            self._driver.enable_remote_debug(debug_id, weinre_domain)
            chrome_path = chrome.WebPage._get_browser_path()
            url = 'http://%s/client/#%s' % (weinre_domain, debug_id)
            cmdline = ['"%s"' % chrome_path, url]
            try:
                processinfo = win32process.CreateProcess(None, ' '.join(cmdline), None, None, 0, 0, None, None, win32process.STARTUPINFO())
                win32event.WaitForInputIdle(processinfo[0], 10000)
            except:
                print >> sys.stderr, '请在Chrome浏览器中打开：%s' % url
                
        def enable_remote_debug2(self):
            '''由于使用weinre不稳定，增加另一种调试方法
            '''
            import os, sys
            import win32process, win32event
            from tuia._autoweb.webkit import chrome
            html_path = os.path.join(os.environ['temp'], 'page.html')
            f = open(html_path, 'w')
            html = self.execScript('document.documentElement.outerHTML;')
            f.write(html)
            f.close()
            chrome_path = chrome.WebPage._get_browser_path()
            cmdline = [chrome_path, html_path]
            try:
                processinfo = win32process.CreateProcess(None, ' '.join(cmdline), None, None, 0, 0, None, None, win32process.STARTUPINFO())
                win32event.WaitForInputIdle(processinfo[0], 10000)
            except:
                print >> sys.stderr, '请在Chrome浏览器中打开：%s' % html_path
    
        def pull_down_refresh(self):
            '''下拉刷新
            '''
            rect = self._container.bounding_rect
            self.execScript('scroll(0, 0);')  # 滑动到顶部 
            self._container._driver.drag(0, rect[1] + 10, 0, rect[3] + rect[1] - 10, 10, 0.1)  # 通过增加滑动次数增加时间，一般下拉时需要暂停一下才会触发刷新操作
    
        def pull_up_refresh(self):
            '''上拉刷新
            '''
            rect = self._container.bounding_rect
            self.execScript('scroll(0,document.body.scrollHeight);')  # 滑动到底部 
            self._container._driver.drag(0, rect[3] + rect[1] - 10, 10, rect[1] + 10, 10, 0.1)
    
    class UIListBase(object):
        '''List控件基类
        '''
        ui_control_type = None
        
        def __init__(self, root, locator):
            self._root = root
            self._locator = locator
            self._ui_map = {}
            self._elements = []
        
        def _get_elements(self):
            '''获取元素列表
            '''
            if self._elements: return self._elements
            result = []
            elements = list(self._root.getElements(self._locator))
            for elem in elements:
                elem._ui_map = self._ui_map
                elem._parent = self._root  # elem._root是WebPage对象
                result.append(elem)
            self._elements = result
            return result
        
        def __len__(self):
            '''list长度
            '''
            return len(self._get_elements())
        
        def __iter__(self):
            '''迭代器
            '''
            for elem in self._get_elements():
                # TODO: 支持子类型
                yield elem
        
        def __getitem__(self, index):
            '''索引方式访问
            '''
            if not isinstance(index, (int, long)):
                raise TypeError('索引值必须为整数：%r' % index)
            if index < 0: index += len(self)
            if index >= len(self): raise IndexError('索引越界，数组长度为：%d，当前索引值为： %d' % (len(self), index))
            elem = self._get_elements()[index]
            return elem
        
        def filter(self, condition):
            '''根据条件过滤，找到满足条件的项即返回，如果找不到则抛出异常
            
            :param condition: 过滤条件
            :type condition:  dict
            '''
            if not condition: raise RuntimeError('过滤条件不能为空')
            pattern = re.compile(r'^(\w+)\[(.+)\]$')
            for elem in self._get_elements():
                equal_flag = True
                for key in condition:
                    if not '.' in key:
                        raise ValueError('过滤条件错误：%s' % key)
                    control_name, attr_name = key.split('.')
                    child_elem = elem.control(control_name)
                    index = ''
                    ret = pattern.match(attr_name)
                    if ret != None:
                        attr_name = ret.group(1)
                        index = ret.group(2)[1:-1]
                    if not hasattr(child_elem, attr_name):
                        raise RuntimeError('控件：%s 没有属性：%s' % (child_elem, attr_name))
                    value = getattr(child_elem, attr_name)
                    if index: value = value.__getitem__(index)
                    if value != condition[key]:
                        equal_flag = False
                        break
                if equal_flag: return elem
            raise RuntimeError('未找到满足条件：%s 的子控件' % condition)
        
    def ui_list(control_cls):
        '''列表类型
        '''
        return type('%sList' % control_cls.__name__, (UIListBase,), {'ui_control_type': control_cls})
    
class ListItemWebPage(WebPage):
    '''为了便于操作List，定义此类型，代表List中的每一项
    '''
    def __init__(self, root):
        super(ListItemWebPage, self).__init__(root._root._container, root._locator)

    def _execute(self, cmd):
        '''重载该方法，防止被作为Frame使用
        '''
        locators = self._locators
        self._locators = []
        ret = super(ListItemWebPage, self)._execute(cmd)
        self._locators = locators
        return ret
