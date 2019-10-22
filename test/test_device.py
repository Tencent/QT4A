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

'''device模块单元测试
'''

try:
    from unittest import mock
except:
    import mock
import unittest

import os
from qt4a.androiddriver.adb import ADB, LocalADBBackend
from qt4a.device import Device, LocalDeviceProvider
from test.test_androiddriver.test_adb import mock_run_shell_cmd as mock_run_shell_cmd_adb
from test.test_androiddriver.test_devicedriver import mock_run_shell_cmd as mock_run_shell_cmd_dev

def mock_run_shell_cmd(cmd_line, root=False, **kwds):
    try:
        return mock_run_shell_cmd_adb(cmd_line, root=root, **kwds)
    except NotImplementedError:
        return mock_run_shell_cmd_dev(cmd_line, root=root, **kwds)
    
class TestDevice(unittest.TestCase):
    '''Device类测试用例
    '''
    
    def _get_device(self):
        ADB.is_rooted = mock.Mock(return_value=False)
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        adb_backend = LocalADBBackend('127.0.0.1', 'test')
        adb = ADB(adb_backend)
        return Device(adb)
    
    def test_device_id(self):
        device = self._get_device()
        self.assertEqual(device.device_id, 'test')
    
    def test_device_host(self):
        device = self._get_device()
        self.assertEqual(device.device_host, '127.0.0.1')
    
    def test_cpu_type(self):
        device = self._get_device()
        self.assertEqual(device.cpu_type, 'armeabi-v7a')
    
    def test_imei(self):
        device = self._get_device()
        ADB.is_rooted = mock.Mock(return_value=True)
        self.assertEqual(device.imei, '180322023834592')
    
    def test_model(self):
        device = self._get_device()
        self.assertEqual(device.model, 'Xiaomi MI 4C')
    
    def test_system_version(self):
        device = self._get_device()
        self.assertEqual(device.system_version, '5.0.2')
    
    def test_sdk_version(self):
        device = self._get_device()
        self.assertEqual(device.sdk_version, 21)
    
    def test_screen_size(self):
        device = self._get_device()
        self.assertEqual(device.screen_size, (800, 1280))
    
    def test_screen_scale(self):
        device = self._get_device()
        self.assertEqual(device.screen_scale, 2.0)
    
    def test_language(self):
        device = self._get_device()
        self.assertEqual(device.language, 'zh')
    
    def test_country(self):
        device = self._get_device()
        self.assertEqual(device.country, 'CN')
    
    def test_debuggable(self):
        device = self._get_device()
        self.assertEqual(device.debuggable, False)
    
    def test_is_rooted(self):
        device = self._get_device()
        self.assertEqual(device.is_rooted(), False)
    
    def test_is_emulator_device(self):
        device = self._get_device()
        self.assertEqual(device.is_emulator_device(), False)
    
    def test_list_dir(self):
        device = self._get_device()
        ADB.is_rooted = mock.Mock(return_value=True)
        dir_list, file_list = device.list_dir('/data/data')
        self.assertEqual(len(dir_list), 89)
        self.assertEqual(len(file_list), 0)
        self.assertEqual(dir_list[0]['name'], 'com.android.apps.tag')
        self.assertEqual(dir_list[0]['attr'], 'rwxr-x--x')
    
    def test_is_file_exists(self):
        device = self._get_device()
        ADB.is_rooted = mock.Mock(return_value=True)
        self.assertEqual(device.is_file_exists('/data/local/tmp/1.txt'), True)


class TestLocalDeviceProvider(unittest.TestCase):
    '''LocalDeviceProvider类测试用例
    '''

    def test_list_device(self):
        res_device_list = ['8776fads', 'afsddsf']
        LocalADBBackend.list_device = mock.Mock(return_value=res_device_list)
        device_list = LocalDeviceProvider.list()
        self.assertEqual(len(device_list), len(res_device_list))
        self.assertEqual(set(device_list), set(res_device_list))


    def test_list_device_env(self):
        res_device_list = ['8776fads', 'afsddsf']
        os.environ['QT4A_AVAILABLE_DEVICES'] = 'afsddsf'
        LocalADBBackend.list_device = mock.Mock(return_value=res_device_list)
        device_list = LocalDeviceProvider.list()
        self.assertEqual(device_list, ['afsddsf'])

        
if __name__ == '__main__':
    unittest.main()
    