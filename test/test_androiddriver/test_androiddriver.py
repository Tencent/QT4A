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

'''androiddriver模块单元测试
'''

import mock
import unittest

from qt4a.androiddriver.devicedriver import DeviceDriver
from qt4a.androiddriver.androiddriver import AndroidDriver
from qt4a.androiddriver.adb import LocalADBBackend, ADB

def mock_send_command(cmd_type, **kwds):
    control = 0x12345678
    if cmd_type == 'GetControl':
        return {'Result': control}
    elif cmd_type == 'GetControlType':
        return {'Result': 'android.widget.TextView'}
    elif cmd_type == 'GetControlRect':
        return {'Result': [0, 0, 100, 200]}
    elif cmd_type == 'GetControlVisibility':
        return {'Result': True}
    elif cmd_type == 'SetActivityPopup':
        return {'Result': True}
    
class TestAndroidDriver(unittest.TestCase):
    '''AndroidDriver类测试用例
    '''
    
    def _create_driver(self):
        adb_backend = LocalADBBackend('127.0.0.1', '')
        adb = ADB(adb_backend)
        return AndroidDriver(DeviceDriver(adb), None)
    
    def test_get_control(self):
        AndroidDriver.send_command = mock.Mock(side_effect=mock_send_command)
        driver = self._create_driver()
        control = driver.get_control('com.tencent.mobileqq.activity.SplashActivity', None, [{'Id': ['=', 'title']}])
        self.assertEqual(control, 0x12345678)
    
    def test_get_control_type(self):
        AndroidDriver.send_command = mock.Mock(side_effect=mock_send_command)
        driver = self._create_driver()
        self.assertEqual(driver.get_control_type(0x12345678, False), 'android.widget.TextView')
    
    def test_get_control_rect(self):
        AndroidDriver.send_command = mock.Mock(side_effect=mock_send_command)
        driver = self._create_driver()
        self.assertEqual(driver.get_control_rect(0x12345678), [0, 0, 100, 200])
    
    def test_get_control_visibility(self):
        AndroidDriver.send_command = mock.Mock(side_effect=mock_send_command)
        driver = self._create_driver()
        self.assertEqual(driver.get_control_visibility(0x12345678), True)
        
if __name__ == '__main__':
    unittest.main()
    