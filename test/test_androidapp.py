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

'''androidapp模块单元测试
'''

try:
    from unittest import mock
except:
    import mock
import unittest

from qt4a.androidapp import AndroidApp
from qt4a.androiddriver.adb import ADB, LocalADBBackend
from qt4a.androiddriver.androiddriver import AndroidDriver
from qt4a.androiddriver.devicedriver import DeviceDriver
from qt4a.device import Device

from test.test_androiddriver.test_adb import mock_run_shell_cmd as mock_run_shell_cmd_adb
from test.test_androiddriver.test_devicedriver import mock_run_shell_cmd as mock_run_shell_cmd_dev
from test.test_androiddriver.test_androiddriver import mock_send_command

def mock_run_shell_cmd(cmd_line, root=False, **kwds):
    try:
        return mock_run_shell_cmd_adb(cmd_line, root=root, **kwds)
    except NotImplementedError:
        return mock_run_shell_cmd_dev(cmd_line, root=root, **kwds)

class AndroidDemoApp(AndroidApp):
    '''demo应用类
    '''
    package_name = 'com.tencent.demo'
    
    def __init__(self, device):
        super(AndroidDemoApp, self).__init__(self.package_name, device, False)
    
    def get_driver(self, process_name=None):
        driver = AndroidDriver(self._device._device_driver, None)
        AndroidDriver.send_command = mock.Mock(side_effect=mock_send_command)
        return driver
    
class TestAndroidApp(unittest.TestCase):
    '''AndroidApp类测试用例
    '''
    
    def _get_app(self):
        ADB.is_rooted = mock.Mock(return_value=False)
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        adb_backend = LocalADBBackend('127.0.0.1', 'test')
        adb = ADB(adb_backend)
        device = Device(adb)
        return AndroidDemoApp(device)
    
    def test_process_name(self):
        app = self._get_app()
        self.assertEqual(app.process_name, 'com.tencent.demo')
    
    def test_send_back_key(self):
        app = self._get_app()
        self.assertEqual(app.send_back_key(), None)
    
    def test_send_home_key(self):
        app = self._get_app()
        self.assertEqual(app.send_home_key(), None)
     
    def test_run_shell_cmd(self):
        app = self._get_app()
        items = app.run_shell_cmd('id').split(' ')
        self.assertEqual(items[0], 'uid=10059(u0_a59)')
    
    def test_is_debug(self):
        app = self._get_app()
        self.assertEqual(app.is_debug(), True)
    
    def test_set_activity_popup(self):
        app = self._get_app()
        self.assertEqual(app.set_activity_popup('com.tencent.demo.activity.MainActivity', False, 'com.tencent.demo'), True)
    
    def test_close(self):
        app = self._get_app()
        app.close()

if __name__ == '__main__':
    unittest.main()
    