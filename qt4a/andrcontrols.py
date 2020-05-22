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

'''定义Android控件
'''

import io
import os
import tempfile
import time

import six
from testbase.util import LazyInit, Timeout
from tuia.exceptions import ControlNotFoundError

from qt4a.androiddriver.androiddriver import AndroidDriver
from qt4a.androiddriver.util import Deprecated, get_intersection, logger

def lazy_init(func):
    '''调用到此函数时进入延迟初始化逻辑
    '''
    def wrap_func(self, *args, **kwds):
        self._lazy_obj._app  # 调到窗口类的延迟初始化函数
        return func(self, *args, **kwds)
    return wrap_func

class Window(object):
    '''控件容器基类
    '''
    Process = ''  # 所在的进程名，不填表示是主进程
    Activity = ''  # 所在的Activity

    def __init__(self, app_or_driver, wait_activity=True, **kwds):
        self._locators = {}
        self._device = None
        self._app = None
        if hasattr(app_or_driver, '_drivers'):
            # AndroidApp类型
            self._driver = app_or_driver.get_driver(self.Process)
            self._device = app_or_driver.device
            self._app = app_or_driver
        elif hasattr(app_or_driver, '_driver'):
            # Window类型
            self._app = app_or_driver._app
            if self._app:
                self._driver = app_or_driver._app.get_driver(self.Process)
            else:
                self._driver = app_or_driver._driver
            self._device = app_or_driver.device

        else:
            # AndroidDriver类型，一般用于调试
            self._driver = app_or_driver
        
        if not isinstance(self._driver, AndroidDriver):
            raise RuntimeError('参数类型错误：%s' % self._driver.__class__)
        self._wait_activity = wait_activity
        if wait_activity:
            self._wait_timeout = kwds.get('wait_timeout')
            self._wait_interval = kwds.get('wait_interval')
        self._lazy_obj = LazyInit(self, '_lazy_obj', self._init_window)

    def _init_window(self):
        '''延迟初始化时执行
        '''
        self._lazy_obj = self  # 避免多次调用初始化函数
        if self._wait_activity == True:
            wait_timeout = self._wait_timeout
            if not wait_timeout: wait_timeout = 12
            wait_interval = self._wait_interval
            if not wait_interval: wait_interval = 0.5
            self.wait_for_exist(wait_timeout, wait_interval)
        self.post_init()
        return self
    
    def post_init(self):
        '''窗口类自定义的初始化逻辑
        '''
        pass
    
    @property
    def Controls(self):
        '''返回控件集合。使用如foo.Controls['最小化按钮']的形式获取控件
        '''
        return self
    
    def hasControlKey(self, control_key):
        '''是否包含控件control_key
        
        :rtype: boolean
        '''
        return (control_key in self._locators)
    
    @property
    def device(self):
        return self._device

    def __findctrl_recur(self, ctrlkey):
        if not (ctrlkey in self._locators.keys()):
            raise NameError("%s没有名为'%s'的子控件！" % (type(self), ctrlkey))
        params = self._locators[ctrlkey].copy()
        ctrltype = params['type']
        del params['type']
        for key in params:
            value = params[key]
            if isinstance(value, six.string_types) and value.startswith('@'):
                params[key] = self[value[1:]]  # 使用缓存
        if issubclass(ctrltype, View):
            return ctrltype(**params)
        else:
            root = params.pop('root', None)
            if root == None: root = self
            params.pop('driver', None)  # delete unexpected param
            params.pop('activity', None)
            return ctrltype(root, ctrlkey, **params)
            
    @lazy_init
    def __getitem__(self, index):
        '''获取index指定控件
        
        :type index: string
        :param index: 控件索引，如'查找按钮'  
        '''
        if not (index in self._locators.keys()):
            raise NameError("%s没有名为'%s'的子控件！" % (type(self), index))
        if not '_instance' in self._locators[index]:
            instance = self.__findctrl_recur(index)
            self._locators[index]['_instance'] = instance
        return self._locators[index]['_instance']
    
    @Deprecated('update_locator')
    def updateLocator(self, locators):
        self.update_locator(locators)
    
    def update_locator(self, locators):
        '''更新控件定义
        '''
        for key in locators.keys():
            locators[key]['driver'] = self._driver  # 保存driver实例
            locators[key]['activity'] = self.__class__.Activity
        self._locators.update(locators)
        
    def wait_for_exist(self, timeout=10, interval=0.5):
        '''等待窗口出现
        '''
        import re
        time0 = time.time()
        current_activity = ''
        if self.Activity == '': return True
        pattern = re.compile(self.Activity)
        while time.time() - time0 < timeout:
            current_activity = self.device.current_activity
            if current_activity == self.Activity:
                return True
            if current_activity and pattern.match(current_activity):
                return True
            time.sleep(interval)
        raise ControlNotFoundError('窗口：%s 未找到，当前窗口为：%s' % (self.__class__.Activity, current_activity))
    
    @property
    @lazy_init
    def rect(self):
        '''窗口区域
        '''
        root = self._driver.get_control(self.Activity, None, [])
        if root == 0:
            raise RuntimeError('查找根节点失败')
        rect = self._driver.get_control_rect(root)
        return rect['Left'], rect['Top'], rect['Width'], rect['Height']

    @lazy_init
    def close(self):
        '''关闭窗口
        '''
        if self.Activity == '':
            self._driver.send_key('{BACK}')
        else:
            if not self._driver.close_activity(self.Activity):
                self._driver.send_key('{BACK}')

        timeout = 3
        time0 = time.time()
        while time.time() - time0 < timeout:
            if self.device.current_activity != self.Activity: return
            time.sleep(0.5)
    
    def get_metis_view(self):
        '''返回MetisView
        '''
        from qt4a.mtcontrols import MetisView
        return MetisView(self)
    
class Gravity(object):
    '''用于控制控件靠左、居中等位置的属性
    '''
    NO_GRAVITY = 0x0000
    AXIS_SPECIFIED = 0x0001
    AXIS_PULL_BEFORE = 0x0002
    AXIS_PULL_AFTER = 0x0004
    AXIS_CLIP = 0x0008
    AXIS_X_SHIFT = 0
    AXIS_Y_SHIFT = 4

    TOP = (AXIS_PULL_BEFORE | AXIS_SPECIFIED) << AXIS_Y_SHIFT
    BOTTOM = (AXIS_PULL_AFTER | AXIS_SPECIFIED) << AXIS_Y_SHIFT
    LEFT = (AXIS_PULL_BEFORE | AXIS_SPECIFIED) << AXIS_X_SHIFT
    RIGHT = (AXIS_PULL_AFTER | AXIS_SPECIFIED) << AXIS_X_SHIFT
    CENTER_VERTICAL = AXIS_SPECIFIED << AXIS_Y_SHIFT
    FILL_VERTICAL = TOP | BOTTOM
    CENTER_HORIZONTAL = AXIS_SPECIFIED << AXIS_X_SHIFT
    FILL_HORIZONTAL = LEFT | RIGHT
    CENTER = CENTER_VERTICAL | CENTER_HORIZONTAL
    FILL = FILL_VERTICAL | FILL_HORIZONTAL
    CLIP_VERTICAL = AXIS_CLIP << AXIS_Y_SHIFT
    CLIP_HORIZONTAL = AXIS_CLIP << AXIS_X_SHIFT
    RELATIVE_LAYOUT_DIRECTION = 0x00800000
    HORIZONTAL_GRAVITY_MASK = (AXIS_SPECIFIED | AXIS_PULL_BEFORE | AXIS_PULL_AFTER) << AXIS_X_SHIFT
    VERTICAL_GRAVITY_MASK = (AXIS_SPECIFIED | AXIS_PULL_BEFORE | AXIS_PULL_AFTER) << AXIS_Y_SHIFT
    DISPLAY_CLIP_VERTICAL = 0x10000000
    DISPLAY_CLIP_HORIZONTAL = 0x01000000
    START = RELATIVE_LAYOUT_DIRECTION | LEFT
    END = RELATIVE_LAYOUT_DIRECTION | RIGHT
    RELATIVE_HORIZONTAL_GRAVITY_MASK = START | END

    def __init__(self, grav):
        self._gravity = grav

    @property
    def left(self):
        raise NotImplementedError()

    @property
    def right(self):
        raise NotImplementedError()

    @property
    def center(self):
        raise NotImplementedError()


def func_wrap(func):
    '''用于方法包装，主要作用是发现控件失效时能够更新控件
    '''
    def _func(*args, **kwargs):
        from qt4a.androiddriver.util import logger, ControlExpiredError
        try:
            return func(*args, **kwargs)
        except ControlExpiredError as e:
            view = args[0]
            try:
                view._update()
            except RuntimeError:
                logger.exception('update control failed')
                raise e  # 更新失败时直接抛出控件失效异常
            return func(*args, **kwargs)
    return _func

class VerticalSwipe(object):
    '''纵向滑动包装类
    '''
    def __init__(self, view):
        self._view = view
        self._is_class = isinstance(view, type)
        
    def __call__(self, *args, **kwds):
        if not self._is_class:
            raise RuntimeError('对象不支持__call__')
        view = self._view(*args, **kwds)
        return VerticalSwipe(view)
    
    def __str__(self):
        if not self._is_class:
            return '<VerticalSwipe_%s object at 0x%.8X>' % (self._view.__class__.__name__, id(self))
        else:
            return '<class \'VerticalSwipe_%s\'>' % self._view.__name__
        
    @property
    def rect(self):
        '''left, top, width, height
        '''
        self_rect = self._view.rect
        root = self._view._root

        root_list = []
        while not isinstance(root, Window):
            if isinstance(root, ScrollView):
                root_list.append(root)
            root = root._root
            
        if len(root_list) == 0: return self_rect
        root_rect = root_list[-1].rect  # 获取可滚动的最顶层根
        left = self_rect[0] if self_rect[0] > root_rect[0] else root_rect[0]
        top = self_rect[1] if self_rect[1] > root_rect[1] else root_rect[1]
        width = self_rect[0] + self_rect[2] - left if self_rect[0] + self_rect[2] < root_rect[0] + root_rect[2] else root_rect[0] + root_rect[2] - left
        height = self_rect[1] + self_rect[3] - top if self_rect[1] + self_rect[3] < root_rect[1] + root_rect[3] else root_rect[1] + root_rect[3] - top
        return left, top, width, height  # 取交集
        
    def swipe_up(self):
        '''向上滑动
        '''
        rect = self.rect
        x1 = x2 = rect[0] + rect[2] // 2
        y1 = rect[1] + rect[3] * 3 // 4
        y2 = rect[1] + rect[3] // 4
        self._view._driver.drag(x1, y1, x2, y2)
    
    def swipe_down(self):
        '''向下滑动
        '''
        rect = self.rect
        x1 = x2 = rect[0] + rect[2] // 2
        y1 = rect[1] + rect[3] // 4
        y2 = rect[1] + rect[3] * 3 // 4
        self._view._driver.drag(x1, y1, x2, y2)
    
    def __getattr__(self, attr):
        return getattr(self._view, attr)
    
class View(object):
    '''控件基类
    '''
    def __init__(self, activity, root, driver, locator=None, hashcode=0):
        self._root = root
        if locator != None:
            self._qpath = locator
            self._locator = locator._parsed_qpath  # 解析后的list
        else:
            if hashcode == 0:
                raise RuntimeError('参数错误')
            self._locator = []
        self._driver = driver
        self._activity = activity
        self._hashcode = 0  # 每个Java对象实例的hashcode（根据内存地址计算出来）
        if hashcode != 0:
            self._hashcode = hashcode
        self._need_convert_qpath = True  # 是否需要转换QPath的ID为整型ID
        
    def __eq__(self, other):
        '''根据hashcode判断两个控件是否相同
        '''
        if other == None: return False
        if self.hashcode == 0 or other.hashcode == 0:
            raise RuntimeError('hashcode错误')
        return self.hashcode == other.hashcode

    def __str__(self):
        return '<%s(id=0x%X) at 0x%X>' % (self.__class__.__name__, self.hashcode & 0xFFFFFFFF, id(self))
    
    def _handle_qpath(self, qpath):
        '''对qpath进行处理，返回处理过的QPath列表
        '''
        # 将字符串ID改为整型ID
        import copy, itertools
        qpath = copy.deepcopy(qpath)  # 防止qpath被修改
        
        result = []  # 返回的是可能的qpath的列表
        for item in qpath:
            item_list = []
            if 'Id' in item:
                # TODO: 如果有两级ID，其中一级是数字形式的
                id_list = self.container._app._get_view_id(item['Id'][1])  # 可能会有多个整型ID
                if id_list == None: 
                    item_list.append(item)
                    result.append(item_list)
                    continue
                if len(id_list) == 1:
                    item['Id'][1] = str(id_list[0])
                    item_list.append(item)
                else:
                    # 存在多个id
                    for _id in id_list:
                        item['Id'][1] = str(_id)
                        item_list.append(copy.deepcopy(item))
            else:
                item_list.append(item)
            result.append(item_list)
            
        qpath_list = []
        for qpath in itertools.product(*result):
            qpath_list.append(qpath)
        return qpath_list
    
    @property
    def container(self):
        '''获取所在容器类
        '''
        root = self._root
        if isinstance(root, Window):
            return root
        else:
            return root.container

    def _get_hashcode(self, parent=0, locator=None):
        '''找到控件的hashcode值
        '''
        if locator: self._locator = locator
        if not self._locator: raise RuntimeError('控件定位信息缺失')
        if parent == 0 and isinstance(self._root, View):
            # 存在父节点
            if self._root._hashcode != 0:
                parent = self._root._hashcode
            else:
                parent = self._root._get_hashcode()
                if parent == 0: return 0  # 父节点不存在
                self._root._hashcode = parent
        
        idx = 0
        if isinstance(self._locator, list):
            # 先使用原始QPath查询一次
            result = self._driver.get_control(self._activity, parent, self._locator)
            if result != 0: 
                if self._need_convert_qpath: self._need_convert_qpath = False  # 不再需要转换QPath
                return result  # TODO: 处理"控件索引超出范围"情况
            if not self._need_convert_qpath: return 0  # 避免控件消失后还要再去获取整型ID
            if not self.container._app._is_use_int_view_id(): return 0  # 不使用整型ID
            
            import re
            pattern = re.compile('^0x[0-9a-fA-F]+$')
            
            need_convert = False
            for item in self._locator:
                if 'Id' in item:
                    if item['Id'][1].isdigit(): continue
                    if pattern.match(item['Id'][1]): continue  # 16进制的
                    need_convert = True
                    break
            if not need_convert: return 0  # 已经是数字类型的ID了
            
            # 生成整型ID的QPath
            qpath_list = self._handle_qpath(self._locator)  
            if len(qpath_list) == 1:
                self._locator = (self._locator, qpath_list[0])
            elif len(qpath_list) > 1:
                # 有多个QPath
                qpath_list.insert(0, self._locator)
                self._locator = tuple(qpath_list)  # tuple类型
            else:
                raise RuntimeError('QPath解析错误：%s' % self._locator)
            idx = 1  # 第一个不需要检查了
            
        for loc in self._locator[idx:]:
            result = self._driver.get_control(self._activity, parent, loc)
            if result != 0: 
                self._locator = list(loc)  # 如果找到,认为这是正确的QPath,以后只使用该QPath进行查找
                self._need_convert_qpath = False
                return result  # 找到即返回
        return 0
            
    @property
    def hashcode(self):
        '''控件唯一标识，只有真正访问控件信息时才会去获取该标识
        '''
        if self._hashcode == 0:
            # 尚未获取控件的hashcode
            timeout = 10  # 查找控件的超时时间
            interval = 0.1
            time0 = time.time()
            while time.time() - time0 < timeout:
                self._hashcode = self._get_hashcode()
                if self._hashcode == 0:
                    # 等待一段时间再查找
                    time.sleep(interval)
                else:
                    break
            if self._hashcode == 0:
                root = self._root
                root_list = []
                while isinstance(root, View):
                    root_list.append(root)
                    root = root._root
                qpath = self._qpath
                locator = self._locator
                parent = self._root
                if len(root_list) > 0:
                    for i in range(len(root_list) - 1, -1, -1):
                        if root_list[i]._hashcode == 0:
                            qpath = root_list[i]._qpath
                            locator = root_list[i]._locator
                            parent = root_list[i]._root
                            break
                parent = parent._hashcode if isinstance(parent, View) else 0
                pos = self._driver.get_control(self._activity, parent, locator, True)
                qpath = str(qpath)
                split_char = qpath[0]
                qpath_list = qpath[1:].split(split_char)
                err_qpath = split_char.join(qpath_list[pos:])
                if err_qpath: err_qpath = split_char + err_qpath  # 补上前面的分隔符
                err_msg = '进程【%s】中未找到控件：%s \n未找到部分路径为：【%s】' % (self._driver._process_name, qpath, err_qpath)
                current_activity = self.container.device.get_current_activity()
                view_tree = self._driver.get_control_tree(current_activity)
                logger.info('Current acvitiy %s control tree：\n%s' % (current_activity.encode('utf8'), view_tree.encode('utf8')))
                raise ControlNotFoundError(err_msg)
        return self._hashcode

    def _update(self):
        '''更新hashcode
        '''
        if isinstance(self._root, View):
            self._root._update()
        self._hashcode = 0
        return self.hashcode

    @property
    @func_wrap
    def parent(self):
        '''获取父控件
        '''
        if not hasattr(self, '_parent'):
            self._parent = self._driver.get_parent(self.hashcode)
        return View(hashcode=self._parent, activity=self._activity, root=self.container, driver=self._driver)

    @property
    @func_wrap
    def children(self):
        '''获取子节点列表
        '''
        children = self._driver.get_children(self.hashcode)
        return [View(hashcode=child, root=self, activity=self._activity, driver=self._driver) for child in children]

    @property
    @func_wrap
    def rect(self):
        '''left, top, width, height
        '''
        get_rect_interval = 0.1  # 防止频繁获取控件坐标信息
        if not hasattr(self, '_last_get_rect_time') or (time.time() - self._last_get_rect_time) > get_rect_interval:
            rect = self._driver.get_control_rect(self.hashcode)
            result = rect['Left'], rect['Top'], rect['Width'], rect['Height']
            self._last_get_rect_time = time.time()
            self._last_rect = result
        return self._last_rect

    @property
    @func_wrap
    def visible(self):
        '''是否可见
        '''
        return self._driver.get_control_visibility(self.hashcode)

    @property
    @func_wrap
    def _clickable(self):
        '''是否可点击
        '''
        CLICKABLE = 0x00004000
        flags = self._driver.get_object_field_value(self.hashcode, 'mViewFlags')
        return int(flags) & CLICKABLE == CLICKABLE

    @property
    def clickable(self):
        '''是否可点击
        to be deleted
        '''
        return self._clickable

    @property
    @func_wrap
    def enabled(self):
        '''是否可用
        '''
        ENABLE = 0x00000000
        ENABLED_MASK = 0x00000020
        flags = int(self._driver.get_object_field_value(self.hashcode, 'mViewFlags'))
        return flags & ENABLED_MASK == ENABLE

    @property
    @func_wrap
    def background_color(self):
        '''背景色
        '''
        result = self._driver.get_object_field_value(self.hashcode, 'mBackground.mColorState.mUseColor')
        if result == 'null':
            return None
        return int(result)

    @property
    def content_desc(self):
        '''控件描述
        '''
        return self._driver.get_object_field_value(self.hashcode, 'mContentDescription')
    
    def exist(self):
        '''判断控件是否存在
        '''
        from qt4a.androiddriver.util import ControlExpiredError, logger
        try:
            self._hashcode = self._get_hashcode()
            return self._hashcode != 0  # 由于Java端使用int型存储，因此可能为负数
        except ControlExpiredError:
            return False
        except RuntimeError:
            logger.exception('获取控件失败')  # 如果没有获取到控件ID对应的整型ID，认为控件不存在
            return False
        
    def wait_for_exist(self, timeout=10, interval=0.1):
        '''等待控件出现
        '''
        time0 = time.time()
        while time.time() - time0 < timeout:
            if self.exist(): return True
            time.sleep(interval)
        raise ControlNotFoundError('控件：%s 未找到' % self._qpath)

    def wait_for_visible(self, timeout=10, interval=0.2):
        '''等待控件可见
        
        :param timeout:  超时时间，单位：秒
        :type  timeout:  int/float
        :param interval: 重试间隔时间，单位：秒
        :type  interval: int/float
        '''
        time0 = time.time()
        while time.time() - time0 < timeout:
            if self.visible: return
            time.sleep(interval)
        raise RuntimeError('Control is not visible in %s seconds' % timeout)
    
    def wait_for_invisible(self, timeout=10, interval=0.2):
        '''等待控件不可见
        
        :param timeout:  超时时间，单位：秒
        :type  timeout:  int/float
        :param interval: 重试间隔时间，单位：秒
        :type  interval: int/float
        '''
        time0 = time.time()
        while time.time() - time0 < timeout:
            if not self.visible: return
            time.sleep(interval)
        raise RuntimeError('Control is not invisible in %s seconds' % timeout)
    
    def _point_in_view(self, x, y):
        '''判断点(x, y)是否在当前View可视范围内
        '''
        view_rect = self.rect
        if x < view_rect[0] or x >= view_rect[0] + view_rect[2]: return False
        if y < view_rect[1] or y >= view_rect[1] + view_rect[3]: return False
        return True
    
    def _get_scroll_root(self):
        '''获取当前控件可滚动区域的根控件
        '''
        root = self._root
        if isinstance(root, ListItem):
            root = root._root  # 获取ListView视图

        root_list = []
        while not isinstance(root, Window):
            if isinstance(root, (ScrollView, ViewPager)):
                root_list.append(root)
            root = root._root
        if root_list == []: return None
        return root_list[-1]  # 获取可滚动的最顶层根
        
    def scroll_to_visible(self, root_rect=None, self_rect=None):
        '''滚动到可视区域
        '''
        root = self._get_scroll_root()
        if root == None: return 0, 0  # 不需要滚动
        
        if not self_rect: self_rect = self.rect
        if not root_rect: root_rect = root.rect
        visible_rect = get_intersection(self_rect, root_rect)
        min_clickable_area = (20, 10)  # 最小可点击区域的大小
        _, screen_height = self.container.device.screen_size
        if visible_rect[0] >= 0 and visible_rect[1] >= 0 and visible_rect[2] >= min_clickable_area[0] and visible_rect[3] >= min_clickable_area[1] and screen_height - (visible_rect[1] + visible_rect[3]) >= 50: 
            logger.info('intersect area is %s' % (visible_rect,))
            return 0, 0
        
        if self_rect[2] > root_rect[2] or self_rect[3] > root_rect[3]:
            x_visible = True
            y_visible = True
            if self_rect[2] >= root_rect[2]:
                # 控件宽度大于容器宽度
                max_left = self_rect[0] if self_rect[0] > root_rect[0] else root_rect[0]
                min_right = self_rect[0] + self_rect[2] if self_rect[0] + self_rect[2] < root_rect[0] + root_rect[2] else root_rect[0] + root_rect[2]
                visible_width = min_right - max_left
                if visible_width < root_rect[2] // 2:
                    # 由于此时控件不可能完全可见，因此认为一半可见即为可见
                    x_visible = False
            if self_rect[3] >= root_rect[3]:
                # 控件高度大于容器高度
                max_top = self_rect[1] if self_rect[1] > root_rect[1] else root_rect[1]
                min_bottom = self_rect[1] + self_rect[3] if self_rect[1] + self_rect[3] < root_rect[1] + root_rect[3] else root_rect[1] + root_rect[3]
                visible_height = min_bottom - max_top
                if visible_height < root_rect[3] // 2:
                    y_visible = False

            if x_visible and y_visible: return 0, 0
            
        # print (self_rect, root_rect)

        if isinstance(root, ViewPager):
            offset = self_rect[0] - root_rect[0]
            count = offset // root_rect[2]
            root.scroll(count, root_rect)
            return root_rect[2] * count, 0

        x_offset = y_offset = 0
        if self_rect[0] < root_rect[0]:
            # 需要向右滑动
            x_offset = self_rect[0] - root_rect[0]
        elif self_rect[0] + self_rect[2] > root_rect[0] + root_rect[2]:
            # 理论上不会出现左右边界都超出root边界范围的情况
            x_offset = (self_rect[0] + self_rect[2]) - (root_rect[0] + root_rect[2])
        if self_rect[1] < root_rect[1]:
            # 需要向下滑动
            y_offset = self_rect[1] - root_rect[1]
        elif self_rect[1] + self_rect[3] > root_rect[1] + root_rect[3]:
            # print (self_rect[1], self_rect[3], root_rect[1], root_rect[3])
            y_offset = (self_rect[1] + self_rect[3]) - (root_rect[1] + root_rect[3])

        if abs(x_offset) > 5 or abs(y_offset) > 5:
            # 低于5个像素不滚动
            # print (x_offset, y_offset)
            root.scroll(x_offset, y_offset)
            time.sleep(0.5)  # 测试发现，滑动后等待时间过短就点击会无效
        return x_offset, y_offset

    def _pre_click(self, x_offset=None, y_offset=None):
        '''点击前的处理
        
        :param x_offset: 距离控件区域左上角的横向偏移。
        :type x_offset:  int或float
        :param y_offset: 距离控件区域左上角的纵向偏移。
        :type y_offset:  int或float
        
        :return 要点击的坐标
        '''

        visible = False
        rect_valid = False
        old_rect = None
        enable = False
        
        screen_width, screen_height = self.container.device.screen_size
        self.hashcode  # 确保控件存在
        root = self._get_scroll_root()
        root_rect = root.rect if root != None else [0, 0, screen_width, screen_height]
        if root != None:
            timeout = 2
            time0 = time.time()
            while time.time() - time0 < timeout:
                if root_rect[2] == 0 or root_rect[3] == 0 or root_rect[0] < 0 or root_rect[1] < 0 or \
                root_rect[0] + root_rect[2] > screen_width or root_rect[1] + root_rect[3] > screen_height:
                    time.sleep(0.1)
                    root_rect = root.rect
                else:
                    break
            else:
                logger.warn('invalid root rect: %s' % (root_rect,))
                
        timeout = 10
        time0 = time.time()
        while time.time() - time0 < timeout:
            # 尝试操作，会出现由于控件尚未初始化完成导致获取的rect不正确的情况
            if not visible:
                if not self.visible:
                    time.sleep(0.1)
                    continue
                else:
                    visible = True

            if not enable:
                # 检查是否可用
                enable = self.enabled
                if not enable:
                    time.sleep(0.1)
                    continue
            
            if not rect_valid:
                rect = self.rect
                if rect[2] == 0 or rect[3] == 0:  # 进行点击操作的控件长宽不可能为0
                    logger.debug('control %s width or height is 0 [%s]' % (self._hashcode, rect))
                    time.sleep(0.2)  # 间隔时间延长为0.2S
                    continue
                
                if not old_rect or rect != old_rect:
                    # 等待控件坐标稳定
                    old_rect = rect
                    logger.debug('wait for control %s stable' % self._hashcode)
                    time.sleep(0.2)
                    continue
                
                is_scroll = False  # 控件是否滚动
                if root != None:
                    for _ in range(5):
                        x_offset1, y_offset1 = self.scroll_to_visible(root_rect, rect)  # 自动滚动到可视区域
                        if abs(x_offset1) <= 5 and abs(y_offset1) <= 5:
                            break
                        else:
                            is_scroll = True
                            rect = self.rect  # 重新获取滚动后的坐标
                
                visible_rect = get_intersection(rect, root_rect)
                if is_scroll:
                    old_rect = visible_rect
                    time.sleep(0.2)
                else:
                    # 不需要再判断控件是否稳定
                    old_rect = None
                    rect = visible_rect
                rect_valid = True
            
            if old_rect != None:
                rect = get_intersection(self.rect, root_rect)
                if old_rect != rect:
                    # 防止有些控件加载后出现位移
                    old_rect = rect
                    time.sleep(0.2)
                    continue
            
            x = (rect[0] + rect[2] // 2)
            y = (rect[1] + rect[3] // 2)
            if x_offset: x = rect[0] + x_offset
            if y_offset: y = rect[1] + y_offset
            return x, y
        else:
            current_activity = self.container.device.get_current_activity()
            if current_activity != self._activity:
                import re
                ret = re.compile(self._activity)
                if not ret.match(current_activity): raise RuntimeError("当前Activity为%s，不是控件所属的Activity" % current_activity)
            if not visible: raise RuntimeError('控件不可见')
            if not enable: raise RuntimeError('控件不可用')
            if not rect_valid: raise RuntimeError('控件区域错误')
            raise RuntimeError('未知错误')
    
    def _click(self, click_time, x=None, y=None, check_ret=True):
        '''具有重试逻辑的点击
        
        :param click_time: 按住的时长，单位为秒
        :type click_time:  int/float
        :param x: 点击的横坐标
        :type x:  int/float
        :param y: 点击的纵坐标
        :type y:  int/float
        :param check_ret: 是否检查点击成功
        :type check_ret:  bool
        '''
        if not x or not y:
            rect = self.rect
            if not x: x = rect[0] + rect[2] // 2
            if not y: y = rect[1] + rect[3] // 2
        for _ in range(10):
            ret = self._driver.click(self.hashcode, x, y, click_time)
            if not check_ret or ret: return True
            time.sleep(0.5)
        raise RuntimeError('click (%d, %d) 失败' % (x, y))
    
    @func_wrap
    def click(self, x_offset=0, y_offset=0):
        '''单击
        
        :param x_offset: 距离控件区域左上角的横向偏移。
        :type x_offset:  int或float
        :param y_offset: 距离控件区域左上角的纵向偏移。
        :type y_offset:  int或float
        '''
        x, y = self._pre_click(x_offset, y_offset)
        self._click(0, x, y)
    
    def double_click(self, x_offset=0, y_offset=0):
        '''双击
        
        :param x_offset: 距离控件区域左上角的横向偏移。
        :type x_offset:  int或float
        :param y_offset: 距离控件区域左上角的纵向偏移。
        :type y_offset:  int或float
        '''
        x, y = self._pre_click(x_offset, y_offset)
        self._click(0, x, y)
        self._click(0, x, y)
        
    def multiple_click(self, count=3, x_offset=0, y_offset=0):
        '''多次点击
        
        :param count: 点击多少次
        :type count:  int
        :param x_offset: 距离控件区域左上角的横向偏移。
        :type x_offset:  int或float
        :param y_offset: 距离控件区域左上角的纵向偏移。
        :type y_offset:  int或float
        '''
        if count < 1: return
        x, y = self._pre_click(x_offset, y_offset)
        for _ in range(count):
            self._click(0, x, y)
    
    @func_wrap
    def long_click(self, duration=1, x_offset=0, y_offset=0, sync=True):
        '''长按
        
        :param duration: 按住时长，单位为秒
        :type duration:  int/float
        :param x_offset: 距离控件区域左上角的横向偏移。
        :type x_offset:  int/float
        :param y_offset: 距离控件区域左上角的纵向偏移。
        :type y_offset:  int/float
        :param sync:     是否是同步调用，为True表示等到长按结束才返回，False表示立即返回
        :type sync:      bool
        '''
        x, y = self._pre_click(x_offset, y_offset)
        if sync:
            self._click(duration, x, y, False)  # 长按不检查回调
        else:
            import threading
            # 按下后立即返回
            self._driver.drag(x, y, x, y, 0, 0, True, False)
            def _delay_func():
                time.sleep(duration)
                self._driver.drag(x, y, x, y, 0, 0, False, True)
            t = threading.Thread(target=_delay_func, args=())
            t.start()
            
    def wait_for_value(self, prop_name, prop_value, timeout=10, interval=0.5, regularMatch=False):
        """等待控件属性值出现, 如果属性为字符串类型，则使用正则匹配
        
        :param prop_name: 属性名字
        :param prop_value: 等待出现的属性值
        :param timeout: 超时秒数, 默认为10
        :param interval: 等待间隔，默认为0.5
        :param regularMatch: 参数 property_name和waited_value是否采用正则表达式的比较。默认为不采用（False）正则，而是采用恒等比较。
        """
        Timeout(timeout, interval).waitObjectProperty(self, prop_name, prop_value, regularMatch)
    
    def swipe(self, direct):
        '''滑动
        
        :param direct: 方向
        :type direct:  string，只能是“up”、“down”、“left”、“right”中的一个值
        '''
        rect = self.rect
        if direct == 'up':
            x1 = x2 = rect[0] + rect[2] // 2
            y1 = rect[1] + rect[3] * 2 // 3
            y2 = rect[1] + rect[3] // 3
        elif direct == 'down':
            x1 = x2 = rect[0] + rect[2] // 2
            y1 = rect[1] + rect[3] // 3
            y2 = rect[1] + rect[3] * 2 // 3
        elif direct == 'left':
            y1 = y2 = rect[1] + rect[3] // 2
            x1 = rect[0] + rect[2] * 2 // 3
            x2 = rect[0] + rect[2] // 3
        elif direct == 'right':
            y1 = y2 = rect[1] + rect[3] // 2
            x1 = rect[0] + rect[2] // 3
            x2 = rect[0] + rect[2] * 2 // 3
        else:
            raise RuntimeError('direct参数只能是：up、down、left、right中的一个')  
        self._driver.drag(x1, y1, x2, y2)
    
    def get_metis_view(self):
        '''返回MetisView
        '''
        from qt4a.mtcontrols import MetisView
        return MetisView(self)
    
class TextView(View):
    '''包含Text的View 
    '''
    @property
    @func_wrap
    def text(self):
        '''获取文本
        '''
        return self._driver.get_control_text(self.hashcode)
    
    @property
    def html_style_text(self):
        '''HTML格式文本
        '''
        return self._driver.get_control_text(self.hashcode, True)
    
    @text.setter
    def text(self, value):
        '''设置文本
        '''
        if not isinstance(value, six.string_types):
            value = str(value)
        if six.PY2 and not isinstance(value, unicode):
            try:
                value = value.decode('utf8')
            except UnicodeDecodeError:
                raise RuntimeError('参数编码错误：%r' % value)
        self.wait_for_visible()
        self.disable_soft_input()  # 赋值前关闭软键盘
        for _ in range(3):
            if self._driver.set_control_text(self.hashcode, value): return
            self.click()
        raise RuntimeError('设置控件文本失败')
    
    @property
    def text_size(self):
        '''字体大小
        '''
        ret = self._driver.call_object_method(self.hashcode, 'mTextPaint', 'getTextSize')
        return int(ret)
    
    @property
    def text_color(self):
        '''字体颜色
        '''
        import json
        ret = json.loads(self._driver.get_object_field_value(self.hashcode, 'mCurTextColor'))
        ret = int(ret)
        if ret < 0: ret += 0x100000000
        return ret
    
    @func_wrap
    def disable_soft_input(self):
        '''禁用软键盘
        '''
        self._driver.enable_soft_input(self.hashcode, False)
    
    def _get_char_rect(self, start_offset, end_offset):
        '''根据字符偏移量计算区域坐标
        
        :param start_offset: 起始字符偏移
        :type start_offset:  int
        :param end_offset:   结束字符偏移
        :type end_offset:    int
        '''
        rect = self._driver.get_text_rect(self.hashcode, start_offset, end_offset)
        return rect['Left'], rect['Top'], rect['Width'], rect['Height']
    
    @property
    def hint_text(self):
        '''空白提示文本
        '''
        return self._driver.get_object_field_value(self.hashcode, 'mHint')
    
    @property
    def image_resource_name(self):
        '''图像资源名称
        '''
        result = self._driver.get_control_image_resource(self.hashcode)
        for key in result:
            result[key] = self.container._app._get_drawable_resource_origin_name(result[key])
        return result
    
    def click_clickable_span(self):
        '''点击TextView中的ClickableSpan区域
        '''
        import re
        pattern = re.compile(r'^<p.*>(.|\n)*<span onclick>(.+)</span>(.*)</p>\s*$')
        html = self.html_style_text
        ret = pattern.match(html)
        if not ret: raise RuntimeError('HTML文本格式错误: %r' % html)
        text = self.text
        start_offset = text.find(ret.group(2))
        end_offset = start_offset + len(ret.group(2))
        rect = self._get_char_rect(start_offset + 1, end_offset)

        textview_rect = self.rect
        x1 = textview_rect[0]
        y1 = textview_rect[1]
        x2 = rect[0] + rect[2] // 2
        y2 = rect[1] + rect[3] // 2
        self.click(x2 - x1, y2 - y1)
        
class EditText(TextView):
    '''输入文本框
    '''
    def send_text(self, text):
        '''输入按键，此方法不能输入中文和大写字母
        '''
        self.click()  # 先获取焦点
        time.sleep(0.1)
        self._driver.send_keys(text)

    def click(self):
        '''click后自动关闭输入法
        '''
        super(TextView, self).click()
        self.disable_soft_input()
        time.sleep(1)

class Button(TextView):
    '''按钮类
    '''
    pass

class CompoundButton(Button):
    '''可选按钮，一般用于实现Switch
    '''
    @property
    @func_wrap
    def checked(self):
        '''是否已选
        '''
        return self._driver.get_control_checked(self.hashcode)

    @checked.setter
    def checked(self, check=True):
        '''设置是否选择
        '''
        if self.checked == check: return
        self.click()

class RadioButton(CompoundButton):
    '''单选按钮
    '''
    pass

class CheckBox(CompoundButton):
    '''选择按钮
    '''
    pass

class CheckedTextView(TextView):
    '''可选文本框
    '''
    @property
    def checked(self):
        '''是否已选
        '''
        return self._driver.get_object_field_value(self.hashcode, 'mChecked') == 'true'

class ImageView(View):
    '''显示图片控件
    '''
    @property
    @func_wrap
    def resource_name(self):
        '''当前使用的图片资源名称
        '''
        ret = self._driver.get_control_background(self.hashcode)
        if ret: return self.container._app._get_drawable_resource_origin_name(ret)
        res_name = self._driver.get_control_image_resource(self.hashcode)
        return self.container._app._get_drawable_resource_origin_name(res_name)
    
    def capture(self, save_path=''):
        '''保存图片到本地
        '''
        if not save_path:
            import tempfile, os
            tmp_path = tempfile.mkdtemp()
            save_path = os.path.join(tmp_path, 'tmp.png')
        
        for _ in range(3):
            pic_data = self._driver.capture_control(self.hashcode)
            if len(pic_data) == 0: 
                time.sleep(1)
                continue
            f = open(save_path, 'wb')
            f.write(pic_data)
            f.close()
            return save_path
        
        raise RuntimeError('获取控件截图失败')
    
    def save(self, save_path=''):
        '''保存图片到本地
        to de deleted
        '''
        return self.capture(save_path)
    
class ImageButton(ImageView):
    pass


class DropdownView(View):
    pass


# 布局类
class ViewGroup(View):
    pass

class FrameLayout(ViewGroup):
    pass

class LinearLayout(ViewGroup):
    pass

class RelativeLayout(ViewGroup):
    '''
    '''
    @property
    def gravity(self):
        '''位置属性
        '''
        return Gravity(self._driver.get_control_gravity(self.hashcode))

class ProgressBar(View):
    '''进度条
    '''
    @property
    def progress(self):
        '''进度
        '''
        return self._driver.get_control_progress(self.hashcode)

class SeekBar(ProgressBar):
    '''可修改进度的进度条
    '''
    @property
    def progress(self):
        '''进度
        '''
        return super(SeekBar, self).progress
    
    @progress.setter
    def progress(self, new_progress):
        '''设置新的进度
        
        :param new_progress: 新进度值,取值范围:0-100
        :type new_progress:  float
        '''
        timeout = 10
        time0 = time.time()
        while time.time() - time0 < timeout:
            rect = self.rect
            if rect[2] == 0 or rect[3] == 0:
                time.sleep(0.2)
                continue
            break
        offset_y = rect[3] // 2
        offset_x = rect[2] * new_progress / 100.0
        self.click(offset_x, offset_y)
        
class ScrollView(FrameLayout):
    '''滚动视图
    '''

    @property
    def reach_top(self):
        '''滑动区域达到顶部
        '''
        scroll_rect = self._driver.get_control_scroll_rect(self.hashcode)
        return scroll_rect[1] == 0

    @property
    def reach_bottom(self):
        '''滑动区域达到底部
        '''
        scroll_rect = self._driver.get_control_scroll_rect(self.hashcode)
        return scroll_rect[1] + scroll_rect[3] >= scroll_rect[5]
    
    def _scroll(self, x, y, count=5, interval=0.04):
        '''横向或纵向滚动
        
        :param x: x > 0 时向左滑动，x = x1 - x2，滚动条向右
        :type x:  int
        :param y: y > 0 时向上滑动，y = y1 - y2，滚动条向下
        :type y:  int
        :param    count: 分为几次滑动
        :type     count:  int
        '''
        if y != 0: y = y * 100 // abs(y) if abs(y) < 100 else y  # 为防止在某个控件内滚动变成点击,设置最小滑动距离为100
        rect = self.rect
        
        mid_x = rect[0] + rect[2] // 2  # 中点
        mid_y = rect[1] + rect[3] // 2
        
        interval *= 1000  # 秒转换成毫秒
        if x != 0:
            x1 = mid_x + x // 2
            x2 = mid_x - x // 2
        else:
            x1 = x2 = mid_x
        
        if y != 0:
            y1 = mid_y + y // 2
            y2 = mid_y - y // 2
        else:
            y1 = y2 = mid_y
            
        self._driver.drag(x1, y1, x2, y2, count, interval)
        
    def scroll(self, x, y, count=5, interval=0.04):
        '''横向或纵向滚动
        
        :param x: x > 0 时向左滑动，x = x1 - x2，滚动条向右
        :type x:  int
        :param y: y > 0时向上滑动，y = y1 - y2，滚动条向下
        :type y:  int
        :param    count: 分为几次滑动
        :type     count:  int
        '''
        # 为避免在不可滑动区域滑动，每次滑动只在可滑动区域3/4处滑动
        time0 = time.time()
        while time.time() - time0 < 10:
            rect = self.rect
            if rect[2] == 0 or rect[3] == 0:
                time.sleep(0.5)
            else:
                break
            
        max_x = rect[2] * 3 // 4
        max_y = rect[3] * 3 // 4
        
        while abs(x) >= max_x:
            self._scroll(max_x * x // abs(x), 0)
            x -= max_x * x // abs(x)
        if x != 0:self._scroll(x, 0)
        
        while abs(y) >= max_y:
            self._scroll(0, max_y * y // abs(y))
            y -= max_y * y // abs(y)
        if y != 0:self._scroll(0, y)
        
    def on_scroll(self, x, y):
        time.sleep(0.5)

    def scroll_up_one_page(self):
        '''向上滑动一页
        '''
        if self.reach_top: return False
        rect = self.rect
        scroll_y = rect[3]
#        scroll_rect = self.driver.get_control_scroll_rect(self.hashcode)
#        if scroll_y > scroll_rect[1]:
#            scroll_y = scroll_rect[1]
        self.scroll(0, -scroll_y)
        self.on_scroll(0, -scroll_y)
        return True

    def scroll_down_one_page(self):
        '''向下滑动一页
        '''
        if self.reach_bottom: return False
        rect = self.rect
        scroll_y = rect[3]
#        scroll_rect = self.driver.get_control_scroll_rect(self.hashcode)
#        offset = scroll_rect[5] - scroll_rect[1] + scroll_rect[3]
#        if scroll_y > offset:
#            scroll_y = offset
        self.scroll(0, scroll_y)
        self.on_scroll(0, scroll_y)
        return True

    def scroll_to_top(self):
        '''滑动到顶部
        '''
        if self.reach_top: return
        rect = self.rect
        while not self.reach_top:
            self.scroll(0, -rect[3])
            self.on_scroll(0, -rect[3])
        self._wait_for_refresh_complete()  # 可能会出现刷新操作

    def scroll_to_bottom(self):
        '''滑动到底部
        '''
        if self.reach_bottom: return
        rect = self.rect
        while not self.reach_bottom:
            self.scroll(0, rect[3])
            self.on_scroll(0, rect[3])

    def _wait_for_refresh_complete(self, timeout=20):
        '''等待刷新完成
        '''
        outer_top = self.rect[1]
        if len(self.children) > 0:
            time0 = time.time()
            while time.time() - time0 < timeout:
                children = self.children
                if len(children) > 0:  # 没有子节点时等待
                    try:
                        inner_top = children[0].rect[1]
                    except RuntimeError as e:
                        logger.warn('_wait_for_refresh_complete error: %s' % e)
                        time.sleep(0.5)
                        continue
                    if inner_top <= outer_top: return True
                time.sleep(0.5)
        return False

    def pull_down_refresh(self):
        '''下拉刷新
        '''
        rect = self.rect
        while rect[2] == 0 or rect[3] == 0:
            time.sleep(0.1)
            rect = self.rect
        self.scroll_to_top()
        # self.scroll(0, -rect[3], 10, 0.1)  # 通过增加滑动次数增加时间，一般下拉时需要暂停一下才会触发刷新操作
        x = rect[0] + rect[2] // 2
        y1 = rect[1] + rect[3] // 4
        y2 = rect[1] + rect[3] * 3 // 4
        
        self._driver.drag(x, y1, x, y2, send_down_event=True, send_up_event=False)
        time.sleep(1)  # 按住不动
        self._driver.drag(x, y2, x, y2, send_down_event=False, send_up_event=True)
        
        self._wait_for_refresh_complete()
        time.sleep(1.5)  # 有些控件刷新完立即操作会不成功
        
class AbsListView(ScrollView):
    '''ListView和GridView基类
    '''
    def __init__(self, *args, **kwds):
        super(AbsListView, self).__init__(*args, **kwds)
        self._first_visible_position = 0  # 可见的第一个控件索引
        self._last_visible_position = 0  # 可见的最后一个索引
        self._item_count = 0  # 所有子节点个数
        self._children = []
        self._first_update = True  # 第一次更新时需要多做些操作

    def __iter__(self):
        '''迭代器
        '''
        self.update()
        for i in range(self.item_count):
            if i < self.first_position:
                # 需要往上滑动
                while i < self.first_position:
                    self.scroll_up_one_page()
                if i > self.last_position:  # 防止滚过
                    self.scroll(0, 100 * (i - self.last_position + 1))
                    self.update()
            elif i > self.last_position:
                # 需要往下滑动
                while i > self.last_position:
                    if i >= self.item_count: return
                    self.scroll_down_one_page()
                if i < self.first_position:
                    self.scroll(0, -100 * (self.first_position - i + 1))
                    self.update()

            idx = i - self.first_position
            if idx >= len(self._children):
                # 可能之前拉到的数据不正确
                self.update()
            if idx < 0 or idx >= len(self._children):
                raise IndexError('%d 不在范围[0, %d]中' % (idx, len(self._children) - 1))
            yield ListItem(self._children[idx])

    def __len__(self):
        self.update()
        return self.item_count

    def __getitem__(self, key):
        '''支持listview[i]方式访问子控件
        '''
        if isinstance(key, int):
            return self.get_child(key)
        else:
            raise TypeError('只支持整型索引')

    def __str__(self):
        return '<%s(Count=%d) at 0x%X>' % (self.__class__.__name__, len(self), id(self))

    @property
    def item_count(self):
        return self._item_count

    @property
    def first_position(self):
        return self._first_visible_position

    @property
    def last_position(self):
        return self._last_visible_position

    def on_scroll(self, x, y):
        super(AbsListView, self).on_scroll(x, y)
        self.update()
        if self.reach_top:
            self._wait_for_refresh_complete()

    @func_wrap
    def _update_list(self):
        listview_info = self._driver.get_listview_info(self.hashcode)
        self._item_count = listview_info['Count']
        self._first_visible_position = listview_info['FirstPosition']
        self._last_visible_position = listview_info['LastPosition']
        if self._item_count > 0:
            self._children = self.children  # 防止每次都访问

    def update(self):
        for _ in range(20):
            show_count = self._last_visible_position - self._first_visible_position + 1
            self._update_list()
            if self._first_visible_position >= 0 and self._last_visible_position >= 0 and len(self._children) == self._last_visible_position - self._first_visible_position + 1:
                # 防止控件树还在构建过程
                if not self._first_update:
                    show_count_now = self._last_visible_position - self._first_visible_position + 1
                    if show_count_now == show_count: return  # 刷新前后显示的节点数目不变才是稳定状态
                self.wait_for_complete()
                self._first_update = False
                return
            time.sleep(0.1)

    def get_child(self, idx):
        '''提供使用索引访问子元素的方法
        '''
        self.update()
        item_count = self.item_count
        if idx < 0:
            # 允许使用负数索引
            idx += item_count
        if idx < 0 or idx >= item_count:
            raise IndexError('index=%d超出list范围' % idx)
        if idx < self.first_position:
            # 需要往上滑动
            while idx < self.first_position:
                self.scroll_up_one_page()
        elif idx > self.last_position:
            # 需要往下滑动
            while idx > self.last_position:
                self.scroll_down_one_page()
        idx = idx - self.first_position
        if idx < 0 or idx >= len(self._children):
            raise IndexError('index=%d错误，不在范围[0, %d]中' % (idx, len(self._children) - 1))
        return ListItem(self._children[idx], idx)
    
    @property
    def reach_top(self):
        return self.reached_top
    
    @property
    def reached_top(self):
        '''滑动区域达到顶部
        '''
        for _ in range(3):
            self.update()
            if self.first_position > 0: return False
            if self.item_count == 0: return True
            if len(self._children) == 0: return True
            # 此时第一个子节点肯定可见
            rect = View.rect.fget(self)  # 子类可能会重载rect以修改滑动范围，此时不能根据子类的实现来计算
            try:
                crect = self._children[0].rect
            except RuntimeError as e:
                from qt4a.androiddriver.util import logger
                # logger.warn('reach_top error: %s' % e)
                logger.exception(e)
                continue
            return crect[1] >= rect[1]
    
    @property
    def reach_bottom(self):
        return self.reached_bottom
    
    @property
    def reached_bottom(self):
        '''滑动区域达到底部
        '''
        if self.item_count == 0: self.update()
        return self.last_position == self.item_count - 1

#    def scroll_to_top(self):
#        '''滑动到顶部
#        '''
#        if self.reach_top: return
#        rect = self.bounding_rect
#        scroll_total = 0
#        while not self.reach_top:
#            scroll_y = self.first_position * 100  # 以每一项100的高度计算
#            if scroll_y > rect[3]: scroll_y = rect[3]
#            print ('scroll', -scroll_y)
#            self.scroll(0, -scroll_y)
#            scroll_total += scroll_y
#        self.on_scroll(0, -scroll_total)
#    
    def scroll_up_one_page(self):
        '''向上滑动一页
        '''
        if self.reached_top: return False
        rect = self.rect
        scroll_y = rect[3]
        if scroll_y > self.first_position * 100:
            scroll_y = self.first_position * 100
        if scroll_y < 100: scroll_y = 100
        self.scroll(0, -scroll_y)
        self.on_scroll(0, -scroll_y)
        return True

    def scroll_down_one_page(self):
        '''向下滑动一页
        '''
        if self.reached_bottom: return False
        rect = self.rect
        scroll_y = rect[3]
        offset = (self.item_count - self.last_position) * 100
        if scroll_y > offset:
            scroll_y = offset
        self.scroll(0, scroll_y)
        self.on_scroll(0, scroll_y)
        return True

    def wait_for_complete(self, timeout=2):
        '''等待ListView控件变化，比如需要读取本地数据
        '''
        count0 = self.item_count
        first_position0 = self.first_position
        last_position0 = self.last_position

        time0 = time.time()
        while time.time() - time0 < timeout:
            time.sleep(0.2)
            self._update_list()
            if self._first_visible_position >= 0 and self._last_visible_position >= 0 and len(self._children) == self._last_visible_position - self._first_visible_position + 1:
                count = self.item_count
                first_position = self.first_position
                last_position = self.last_position
                if count == count0 and first_position == first_position0 and last_position == last_position0: return True
                count0 = count
                first_position0 = first_position
                last_position0 = last_position
        return False

class ListItem(View):
    '''为方便遍历AbsListView，表示AbsListView的直接子孩子
    '''
    def __init__(self, view, idx=None):
        '''
        :param view: AbsListView中每一个子节点
        :type view:  View
        '''
        self._view = view
        self._control_dict = {}  # 用于缓存
        self._idx = idx  # 项索引，用于重新查找控件
        
    def __getitem__(self, key):
        '''支持listitem[key]方式访问子节点
        :param key: 封装时定义的子节点名
        :type key:  string
        '''
        if key in self._control_dict:
            return self._control_dict[key]
        item = self._view.container[key]
        import copy
        result = copy.copy(item)  # 复制一个对象
        result._root = self  # 修改根节点为当前节点
        self._control_dict[key] = result
        return result

    def __getattr__(self, attr):
        '''委托self._view实现
        '''
        return getattr(self._view, attr)
    
    def _update(self):
        '''如果没有索引值直接抛异常
        '''
        from qt4a.androiddriver.util import logger
        logger.debug('ListItem update, idx=%s' % self._idx)
        if self._idx == None:
            raise RuntimeError('ListView无法重新获取控件')
        self._view._root.update()
        self._view = self._view._root._children[self._idx]  # 重新获取Item项
    
    def has(self, key):
        '''是否存在该节点
        
        :param key: 封装时定义的子节点名
        :type  key: string
        '''
        from qt4a.androiddriver.util import ControlExpiredError, logger
        item = self._view.container[key]
        # child = self._driver.get_control(self._activity, self.hashcode, item._locator)
        self._view._need_convert_qpath = True  # 避免判断多个节点存在时不会使用整型ID查找问题
        try:
            hashcode = self._view._get_hashcode(self._view.hashcode, item._locator)
            if hashcode == 0: return False
        except ControlExpiredError:
            logger.info('ControlExpiredError occur in has')
            if self._idx == None: return False
            self._update()
            return self.has(key)
        item._locator = self._locator  # 替换为真正的QPath
        return True

class ListView(AbsListView):
    '''列表视图
    '''
    pass

class GridView(AbsListView):
    '''格子视图
    '''

class TabWidget(View):
    '''Tab控件
    '''
    @property
    def selected_index(self):
        '''当前所选项的索引
        '''
        return self._driver.get_selected_tab_index(self.hashcode)

class WebkitWebView(View):
    '''4.4以下版本中的WebView
    '''
    
    def __init__(self, *args, **kwargs):
        super(WebkitWebView, self).__init__(*args, **kwargs)
    
    def eval_script(self, frame_xpaths, script):
        '''执行JavaScript
        '''
        from qt4a.androiddriver.util import AndroidSpyError, ControlExpiredError
        try:
            return self._driver.eval_script(self.hashcode, frame_xpaths, script)
        except ControlExpiredError as e:
            raise e
        except AndroidSpyError as e:
            try:
                from qt4w.util import JavaScriptError
            except ImportError:
                raise
            else:
                raise JavaScriptError(frame_xpaths, e.args[0])
            
class WebView(View):
    '''Web页面容器
    '''
    title = None
    url = None
    is_chromium = None
    
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        super(WebView, self).__init__(*args, **kwargs)
        self._is_chromium = self.__class__.is_chromium
        if self._is_chromium == None: self._is_chromium = self.container.device.sdk_version >= 19  # Android 4.4以上使用Chromium内核
        self._webview_impl = None
    
    @property
    def webdriver_class(self):
        '''WebView对应的WebDriver类
        '''
        from qt4a.androiddriver.webdriver import AndroidWebDriver
        return AndroidWebDriver
    
    @property
    def webview_impl(self):
        '''
        '''
        if self._webview_impl == None:
            if not self._is_chromium:
                self._webview_impl = WebkitWebView(*self._args, **self._kwargs)
            else:
                try:
                    self._webview_impl = ChromiumWebView(title=self.__class__.title, url=self.__class__.url, *self._args, **self._kwargs)
                except ImportError:
                    # Fallback to custom WebView
                    self._webview_impl = WebkitWebView(*self._args, **self._kwargs)

        return self._webview_impl
    
    def eval_script(self, frame_xpaths, script):
        '''在指定frame中执行JavaScript，并返回执行结果（该实现需要处理js基础库未注入情况的处理）
        
        :param frame_xpaths: frame元素的XPATH路径，如果是顶层页面，怎传入“[]”
        :type frame_xpaths:  list
        :param script:       要执行的JavaScript语句
        :type script:        string
        '''
        return self.webview_impl.eval_script(frame_xpaths, script)
    
    @property
    def visible_rect(self):
        '''WebView控件可见区域的坐标信息
        '''
        return self.rect
            
    def disable_soft_input(self):
        '''禁用软键盘
        '''
        return self._driver.enable_soft_input(self.hashcode, False)
    
    def click(self, x_offset=None, y_offset=None):
        '''点击WebView中的某个坐标
        
        :param x_offset: 与WebView左上角的横向偏移量
        :type x_offset:  int/float
        :param y_offset: 与WebView左上角的纵向偏移量
        :type y_offset:  int/float
        '''
        if x_offset != None or y_offset != None:
            rect = self.rect
            x = (rect[0] + rect[2] // 2) if not x_offset else (rect[0] + x_offset)
            y = (rect[1] + rect[3] // 2) if not y_offset else (rect[1] + y_offset)
            return self._click(0, x, y)
        else:
            return super(WebView, self).click()
    
    def long_click(self, x_offset, y_offset, duration=1):
        '''长按WebView中的某个坐标
        
        :param x_offset: 与WebView左上角的横向偏移量
        :type x_offset:  int/float
        :param y_offset: 与WebView左上角的纵向偏移量
        :type y_offset:  int/float
        :param duration: 按住的持续时间
        :type duration:  int/float
        '''
        return super(WebView, self).long_click(duration, x_offset, y_offset)
    
    def send_keys(self, keys):
        '''向WebView中的输入框发送按键
        
        :param keys: 要发送的按键
        :type keys:  string
        '''
        self.container.device.send_text(keys)
        #self._driver.send_keys(keys)
    
    def drag(self, x1, y1, x2, y2):
        '''从(x1, y1)点滑动到(x2, y2)点
        
        :param x1: 起点横坐标
        :type x1:  int/float
        :param y1: 起点纵坐标
        :type y1:  int/float
        :param x2: 终点横坐标
        :type x2:  int/float
        :param y2: 终点纵坐标
        :type y2:  int/float
        '''
        self._driver.drag(x1, y1, x2, y2, 10, 0.1)
    
    def screenshot(self):
        '''当前WebView的截图
        :return: PIL.Image
        '''
        from PIL import Image
        temp_path = tempfile.mktemp('.jpg')
        self.container.device.take_screen_shot(temp_path)
        with open(temp_path, 'rb') as fp:
            image_data = fp.read()
        os.remove(temp_path)
        image = Image.open(io.BytesIO(image_data))
        left, top, width, height = self.rect
        image = image.crop((left, top, left + width, top + height))
        return image


class ChromiumWebView(WebkitWebView):
    '''Chromium内核的WebView
    '''
    debugger_instances = {}
    
    def __init__(self, url=None, title=None, *args, **kwargs):
        import chrome_master
        super(ChromiumWebView, self).__init__(*args, **kwargs)
        self._is_system_webview = False
        webview_types = self._driver.get_control_type(self.hashcode)
        for webview_type in webview_types:
            if webview_type == 'android.webkit.WebView':
                self._is_system_webview = True
                break
        self._url = url
        self._title = title
        
        self._device = self.container.device
        self._pid = self._device.adb.get_pid(self._driver._process_name)
        self._service_name = 'webview_devtools_remote_%d' % self._pid

        chrome_master.set_logger(logger)

        self._chrome_master = chrome_master.ChromeMaster(('localhost', self._pid), self.create_socket)  # 高版本Chromium内核必须要使用localhost的Host

        self._page_debugger = self.get_debugger()
        self._page_debugger.register_handler(chrome_master.RuntimeHandler)

    def create_socket(self):
        '''创建socket对象
        '''
        try:
            sock = self._device.adb.create_tunnel(self._service_name, 'localabstract')
            if sock: return sock
        except:
            logger.warn('create socket tunnel %s failed' % self._service_name)
        self._driver.set_webview_debugging_enabled(self.hashcode, True)
        return self.create_socket()
        
    def get_page_url(self):
        '''获取当前WebView页面的url
        '''
        if not self._is_system_webview: return self._url
        timeout = 10
        time0 = time.time()
        while time.time() - time0 < timeout:
            try:
                ret = super(ChromiumWebView, self).eval_script([], 'location.href')
            except:
                logger.exception('Read page url failed')
                return
            if ret != 'about:blank': return ret
            time.sleep(0.5)
        else:
            raise RuntimeError('Get page url failed')
    
    def get_debugger(self, timeout=10):
        '''获取当前页面的RemoteDebugger实例
        '''
        url = self.get_page_url()
        time0 = time.time()
        while time.time() - time0 < timeout:
            try:
                return self._chrome_master.find_page(url=url, title=self._title)  # 获取最后一个页面
            except RuntimeError as e:
                logger.warn('[%s] %s' % (self.__class__.__name__, e))
                time.sleep(0.5)
        else:
            raise RuntimeError('Find page timeout')

    def convert_frame_tree(self, frame_tree, parent=None):
        '''将frame tree转化为Frame对象
        '''
        from qt4w import util
        frame = util.Frame(frame_tree['frame']['id'], frame_tree['frame'].get('name'), frame_tree['frame']['url'])
        if parent: parent.add_child(frame)
        if 'childFrames' in frame_tree:
            for child in frame_tree['childFrames']:
                self.convert_frame_tree(child, frame)
        return frame
        
    def _get_frame_id_by_xpath(self, frame_xpaths, timeout=10):
        '''获取frame id
        '''
        from qt4a.androiddriver.webdriver import AndroidWebDriver
        from qt4w import util
        time0 = time.time()
        while time.time() - time0 < timeout:
            frame_tree = self._page_debugger.page.get_frame_tree()
            frame = self.convert_frame_tree(frame_tree)
            frame_selector = util.FrameSelector(AndroidWebDriver(self), frame)
            try:
                frame = frame_selector.get_frame_by_xpath(frame_xpaths)
            except util.ControlNotFoundError:
                pass
            else:
                return frame.id
            time.sleep(0.5)
        else:
            raise ControlNotFoundError('Find frame %s timeout' % ''.join(frame_xpaths))
        
    def eval_script(self, frame_xpaths, script):
        '''在指定frame中执行JavaScript，并返回执行结果
        
        :param frame_xpaths: frame元素的XPATH路径，如果是顶层页面，怎传入“[]”
        :type frame_xpaths:  list
        :param script:       要执行的JavaScript语句
        :type script:        string
        '''
        from chrome_master import util
        frame_id = None
        if frame_xpaths:
            frame_id = self._get_frame_id_by_xpath(frame_xpaths)
        try:
            return self._page_debugger.runtime.eval_script(frame_id, script)
        except util.JavaScriptError as e:
            from qt4w.util import JavaScriptError
            raise JavaScriptError(frame_xpaths, e.message)
        
class ViewPager(ViewGroup):
    '''横向滚动视图
    '''
    @property
    def current_item_index(self):
        '''当前显示项的索引
        '''
        ret = self._driver.get_object_field_value(self.hashcode, 'mCurItem')
        return int(ret)
    
    @property
    def item_count(self):
        '''总项数
        '''
        ret = self._driver.get_object_field_value(self.hashcode, 'mItems.size')
        return int(ret)
    
    def scroll(self, count=1, rect=None):
        '''左右滚动
        
        :param count: 滑动次数，大于0表示向右滑动，小于0表示向左滑动
        :type  count: int
        '''
        if rect == None: rect = self.rect
        x1 = rect[0] + 5
        x2 = rect[0] + rect[2] - 5
        if count > 0:
            # 交换终点
            x = x1
            x1 = x2
            x2 = x
        y = rect[1] + rect[3] // 2
        for _ in range(abs(count)):
            self._driver.drag(x1, y, x2, y, 1)
    
    def __iter__(self):
        '''迭代器
        '''
        for i in range(self.item_count):
            idx = self.current_item_index
            if idx > i:
                # 向右滑动
                self.scroll(i - idx)
            elif idx < i:
                # 向左滑动
                self.scroll(idx - i)
            yield ListItem(self.children[i])
            
class RadioGroup(LinearLayout):
    '''
    '''
    pass

class RecyclerView(AbsListView):
    '''虽然不是继承自ListView，但是可以复用其部分代码，所以从ListView继承过来
    '''
    @func_wrap
    def _update_list(self):
        self._item_count = self._driver.call_object_method(self.hashcode, 'mAdapter', 'getItemCount')
        self._first_visible_position = -1
        self._last_visible_position = -1
        if self._item_count > 0:
            self._children = self.children  # 防止每次都访问
        if len(self._children) > 0:
            # 获取第一个子节点的索引值
            self._first_visible_position = self._get_first_visible_position()
            self._last_visible_position = self._first_visible_position + len(self._children) - 1
    
    def _get_first_visible_position(self):
        '''获取第一个可见节点的位置
        ('mLayoutParams', 'getViewLayoutPosition')
        '''
        if hasattr(self, '_get_first_visible_position_args'):
            return self._driver.call_object_method(self._children[0].hashcode, *self._get_first_visible_position_args)
        
        for args in (('mLayoutParams.mViewHolder', 'getPosition'),
                     ('mLayoutParams.mViewHolder', 'getLayoutPosition')):
            try:
                result = self._driver.call_object_method(self._children[0].hashcode, *args)
                self._get_first_visible_position_args = args
                return result
            except:
                logger.exception('get first visible position by %r failed' % args)
        
    def _is_horizontal(self):
        '''是否横向滑动
        '''
        if not hasattr(self, '__horizontal'):
            if self.item_count >= 2:
                self.__horizontal = self.children[0].rect[0] != self.children[1].rect[0]
            elif self.item_count == 1:
                x_ratio = 1.0 * self.children[0].rect[2] / self.rect[2]
                y_ratio = 1.0 * self.children[0].rect[3] / self.rect[3]
                self.__horizontal = x_ratio < y_ratio
            else:
                return False
        return self.__horizontal
    
    @property
    def reached_left(self):
        '''滑动区域达到最左边
        '''
        for _ in range(3):
            self.update()
            if self.first_position > 0: return False
            if self.item_count == 0: return True
            if len(self._children) == 0: return True
            # 此时第一个子节点肯定可见
            rect = View.rect.fget(self)  # 子类可能会重载rect以修改滑动范围，此时不能根据子类的实现来计算
            try:
                crect = self._children[0].rect
            except RuntimeError as e:
                logger.exception(e)
                continue
            return crect[0] >= rect[0]

    @property
    def reached_right(self):
        '''滑动区域达到最右边
        '''
        if self.item_count == 0: self.update()
        return self.last_position == self.item_count - 1
        
    def scroll_left_one_page(self):
        '''向左滑动一页
        '''
        if self.reached_left: return False
        rect = self.rect
        scroll_x = rect[2]
        item_rect = self._children[0].rect
        if scroll_x > self.first_position * item_rect[2]:
            scroll_x = self.first_position * item_rect[2]
        if scroll_x < 100: scroll_x = 100
        self.scroll(-scroll_x, 0)
        self.on_scroll(-scroll_x, 0)
        return True

    def scroll_right_one_page(self):
        '''向右滑动一页
        '''
        if self.reached_right: return False
        rect = self.rect
        scroll_x = rect[2]
        item_rect = self._children[0].rect
        offset = (self.item_count - self.last_position) * item_rect[2]
        if scroll_x > offset:
            scroll_x = offset
        self.scroll(scroll_x, 0)
        self.on_scroll(scroll_x, 0)
        return True
    
    def scroll_up_one_page(self):
        '''向上滑动一页
        '''
        if self.reached_top: return False
        rect = self.rect
        scroll_y = rect[3]
        child_rect = self._children[0].rect
        if scroll_y > self.first_position * child_rect[3]:
            scroll_y = self.first_position * child_rect[3]
        if scroll_y < child_rect[3]: scroll_y = child_rect[3]
        self.scroll(0, -scroll_y)
        self.on_scroll(0, -scroll_y)
        return True

    def scroll_down_one_page(self):
        '''向下滑动一页
        '''
        if self.reached_bottom: return False
        rect = self.rect
        scroll_y = rect[3]
        child_rect = self._children[0].rect
        offset = (self.item_count - self.last_position) * child_rect[3]
        if scroll_y > offset:
            scroll_y = offset
        elif scroll_y < child_rect[3]:
            scroll_y = child_rect[3]
        self.scroll(0, scroll_y)
        self.on_scroll(0, scroll_y)
        return True
    
    def _scroll_child_to_visible(self, child_idx):
        '''将子节点滚动到可见区域
        '''
        if child_idx < self.first_position:
            # 需要往左/上滑动
            while child_idx < self.first_position:
                if self._is_horizontal():
                    self.scroll_left_one_page()
                else:
                    self.scroll_up_one_page()
                self._update_list()
        elif child_idx > self.last_position:
            # 需要往右/下滑动
            while child_idx > self.last_position:
                if self._is_horizontal():
                    self.scroll_right_one_page()
                else:
                    self.scroll_down_one_page()
                self._update_list()
                
        child = self.children[child_idx - self.first_position]
        self_rect = self.rect
        child_rect = child.rect
        
        # 保证当前项完全可见
        
        if child_rect[0] < self_rect[0]: 
            # 向左滑动
            scroll_x = self_rect[0] - child_rect[0]
            self.scroll(-scroll_x, 0)
        elif child_rect[0] + child_rect[2] > self_rect[0] + self_rect[2]: 
            # 向右滑动
            scroll_x = child_rect[0] + child_rect[2] - (self_rect[0] + self_rect[2])
            self.scroll(scroll_x, 0)
        elif child_rect[1] < self_rect[1]: 
            # 向上滑动
            scroll_y = self_rect[1] - child_rect[1]
            self.scroll(0, -scroll_y)
        elif child_rect[1] + child_rect[3] > self_rect[1] + self_rect[3]:
            # 向下滑动
            scroll_y = child_rect[1] + child_rect[3] - (self_rect[1] + self_rect[3])
            self.scroll(0, scroll_y)
        else:
            return
        self._update_list()
        
    def get_child(self, idx):
        '''提供使用索引访问子元素的方法
        '''
        self.update()
        item_count = self.item_count
        if idx < 0:
            # 允许使用负数索引
            idx += item_count
        if idx < 0 or idx >= item_count:
            raise IndexError('index=%d超出list范围' % idx)
        self._scroll_child_to_visible(idx)
        idx = idx - self.first_position
        if idx < 0 or idx >= len(self._children):
            raise IndexError('index=%d错误，不在范围[0, %d]中' % (idx, len(self._children) - 1))
        return ListItem(self._children[idx], idx)
    
    def __iter__(self):
        '''迭代器
        '''
        self.update()
        for i in range(self.item_count):
            self._scroll_child_to_visible(i)

            idx = i - self.first_position
            if idx >= len(self._children):
                # 可能之前拉到的数据不正确
                self.update()
            if idx < 0 or idx >= len(self._children):
                raise IndexError('%d 不在范围[0, %d]中' % (idx, len(self._children) - 1))
            yield ListItem(self._children[idx])

class DatePicker(FrameLayout):
    '''时间选择器
    '''
    def set_date(self, year, month, day): 
        if year < 0 or month < 1 or month > 12 or day < 1 or day > 31:
            raise RuntimeError('参数传入不符合时间要求')

        if self._driver._adb.get_sdk_version() < 21:  # 5.0以下用如下方法
            self._driver.call_object_method(self.hashcode, 'mCurrentDate', 'set', 'void', year, month - 1, day)
        else:
            self._driver.call_object_method(self.hashcode, 'mDelegate.mCurrentDate', 'set', 'void', year, month - 1, day)

class ActionMenuItemView(TextView):
    '''android.support.v7.internal.view.menu.ActionMenuItemView
    '''
    pass

class AppCompatEditText(EditText):
    '''android.support.v7.widget.AppCompatEditText
    '''
    pass

class AppCompatImageView(ImageView):
    '''android.support.v7.widget.AppCompatImageView
    '''
    pass

if __name__ == '__main__':
    pass
