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

'''andrcontrols模块单元测试
'''

try:
    from unittest import mock
except:
    import mock
import unittest

from qt4a.andrcontrols import Window, TextView, EditText
from qt4a.qpath import QPath

class MyWindow(Window):
    '''demo窗口
    '''
    Activity = 'com.tencent.demo.activity.MainActivity'
    Process = 'com.tencent.demo'
    
    def __init__(self, app, wait_activity=False):
        super(MyWindow, self).__init__(app, wait_activity=wait_activity)
        self.update_locator({'标题': {'type': TextView, 'root': self, 'locator': QPath('/Id="title"')},
                            '输入框': {'type': EditText, 'root': self, 'locator': QPath('/Id="edit"')},
                            })
        
class TestWindow(unittest.TestCase):
    '''Window类测试用例
    '''
    
    def _get_device(self):
        ADB.is_rooted = mock.Mock(return_value=False)
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        adb_backend = LocalADBBackend('127.0.0.1', 'test')
        adb = ADB(adb_backend)
        return Device(adb)
    
    def test_wait_for_exist(self):
        pass
