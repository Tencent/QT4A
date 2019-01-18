# -*- coding: utf-8 -*-
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

'''AI控件库
'''

from io import BytesIO
import os
import tempfile
from qt4a.andrcontrols import Window, View

class MtWindow(Window):
    # TODO: to be deleted
    pass
    
try:
    from metislib.controls import *
except ImportError as e:
    class MtControl(View):
        pass
else:
    class MetisView(object):
        '''实现IMetisView接口
        '''
        def __init__(self, view_or_window):
            if not isinstance(view_or_window, Window) and not isinstance(view_or_window, View):
                raise TypeError('view_or_window must be Window or View object')
            self._view_or_window = view_or_window
            if isinstance(self._view_or_window, View):
                self._device = self._view_or_window.container.device
            else:
                self._device = self._view_or_window.device
                
        @property
        def rect(self):
            '''元素相对坐标(x, y, w, h)
            '''
            if isinstance(self._view_or_window, View):
                return self._view_or_window.rect
            else:
                screen_size = self._device.screen_size
                return (0, 0, screen_size[0], screen_size[1])
            
        @property
        def os_type(self):
            '''系统类型，例如"android"，"ios"，"pc"
            '''
            return 'android'
    
        def screenshot(self):
            '''当前容器的区域截图
            :return: PIL.image
            '''
            from PIL import Image
            clip = False
            if isinstance(self._view_or_window, View): clip = True
            temp_path = tempfile.mktemp('.jpg')
            self._device.take_screen_shot(temp_path)
            with open(temp_path, 'rb') as fp:
                image_data = fp.read()
            os.remove(temp_path)
            image = Image.open(BytesIO(image_data))
            if clip:
                x, y, w, h = self.rect
                image = image.crop((x, y, x + w, y + h))
            return image
        
        def _get_position(self, offset_x=None, offset_y=None):
            '''
            '''
            if offset_x == None: offset_x = 0.5
            if offset_y == None: offset_y = 0.5
            rect = self.rect
            x = rect[0] + int(rect[2] * offset_x)
            y = rect[1] + int(rect[3] * offset_y)
            return x, y
        
        def click(self, offset_x=None, offset_y=None):
            '''点击
            :param offset_x: 相对于该控件的坐标offset_x，百分比( 0 -> 1 )，不传入则默认该控件的中央
            :type offset_x: float|None
            :param offset_y: 相对于该控件的坐标offset_y，百分比( 0 -> 1 )，不传入则默认该控件的中央
            :type offset_y: float|None
            '''
            x, y = self._get_position(offset_x, offset_y)
            self._device.run_shell_cmd('input tap %d %d' % (x, y))

        def send_keys(self, text):
            '''
            '''
            self._device.send_text(text)
    
        def double_click(self, offset_x=None, offset_y=None):
            '''
            '''
            x, y = self._get_position(offset_x, offset_y)
            self._device.run_shell_cmd('input tap %s %s' % (x, y))
            self._device.run_shell_cmd('input tap %s %s' % (x, y))
    
        def long_click(self, duration, offset_x=None, offset_y=None):
            '''
            '''
            x, y = self._get_position(offset_x, offset_y)
            self._device.run_shell_cmd('input swipe %s %s %s %s %d' % (x, y, x, y, int(duration * 1000)))
            
        def drag(self, from_x=0.5, from_y=0.5, to_x=0.5, to_y=0.1, duration=0.5):
            '''拖拽
            
            :param from_x: 起点 x偏移百分比（从左至右为0.0至1.0）
            :type from_x: float
            :param from_y: 起点 y偏移百分比（从上至下为0.0至1.0）
            :type from_y: float
            :param to_x: 终点 x偏移百分比（从左至右为0.0至1.0）
            :type to_x: float
            :param to_y: 终点 y偏移百分比（从上至下为0.0至1.0）
            :type to_y: float
            :param duration: 持续时间（秒）
            :type duration: float
            '''
            from_x, from_y = self._get_position(from_x, from_y)
            to_x, to_y = self._get_position(to_x, to_y)
            return self._device.drag(from_x, from_y, to_x, to_y, count=5, wait_time=100, send_down_event=True, send_up_event=True)
    
        
if __name__ == '__main__':
    pass
