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

'''devicedriver模块单元测试
'''

try:
    from unittest import mock
except:
    import mock
import shlex
import unittest

from qt4a.androiddriver.adb import ADB, LocalADBBackend
from qt4a.androiddriver.devicedriver import DeviceDriver

def mock_run_shell_cmd(cmd_line, root=False, **kwds):
    args = shlex.split(cmd_line)
    if args[0] == 'sh':
        if args[1] == '/data/local/tmp/qt4a/SpyHelper.sh':
            if args[2] == 'getLanguage':
                return 'zh'
            elif args[2] == 'getCountry':
                return 'CN'
            elif args[2] == 'getExternalStorageDirectory':
                return '/storage/sdcard'
            elif args[2] == 'getScreenSize':
                return '800, 1280'
            elif args[2] == 'getClipboardText':
                return '1234'
            elif args[2] == 'isScreenLockEnabled':
                return 'true'
            elif args[2] == 'setScreenLockEnable':
                return 'true'
            elif args[2] == 'isScreenOn':
                return 'true'
            elif args[2] == 'isKeyguardLocked':
                return 'true'
            elif args[2] == 'getWlanMac':
                return '52:54:00:12:34:57'
            elif args[2] == 'hasGPS':
                return 'true'
            elif args[2] == 'getCameraNumber':
                return '2'
            elif args[2] == 'getDeviceImei':
                return '180322023834592'
            elif args[2] == 'sendKey':
                return 'true'
            elif args[2] == 'isDebugPackage':
                return 'true'
            else:
                raise NotImplementedError(args[2])
    elif args[0] == 'am':
        if args[1] == 'start':
            activity = ''
            if args[2] == '-n':
                activity = args[3]
            if not '-w' in args:
                return 'Starting: Intent { cmp=%s }' % activity
    raise NotImplementedError(args)

class TestDeviceDriver(unittest.TestCase):
    '''DeviceDriver类测试用例
    '''
    
    def _get_device_driver(self):
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        adb_backend = LocalADBBackend('127.0.0.1', '')
        adb = ADB(adb_backend)
        return DeviceDriver(adb)
    
    def test_get_language(self):
        driver = self._get_device_driver()
        self.assertEqual(driver.get_language(), 'zh')
    
    def test_get_country(self):
        driver = self._get_device_driver()
        self.assertEqual(driver.get_country(), 'CN')
    
    def test_get_external_sdcard_path(self):
        ADB.is_rooted = mock.Mock(return_value=False)
        driver = self._get_device_driver()
        self.assertEqual(driver.get_external_sdcard_path(), '/storage/sdcard')
    
    def test_get_screen_size(self):
        ADB.is_rooted = mock.Mock(return_value=False)
        driver = self._get_device_driver()
        self.assertEqual(driver.get_screen_size(), (800, 1280))
    
    def test_get_clipboard_text(self):
        ADB.is_rooted = mock.Mock(return_value=False)
        driver = self._get_device_driver()
        self.assertEqual(driver.get_clipboard_text(), '1234')
    
    def test_is_screen_lock_enabled(self):
        ADB.is_rooted = mock.Mock(return_value=True)
        driver = self._get_device_driver()
        self.assertEqual(driver.is_screen_lock_enabled(), True)
    
    def test_set_screen_lock_enable(self):
        ADB.is_rooted = mock.Mock(return_value=True)
        driver = self._get_device_driver()
        self.assertEqual(driver.set_screen_lock_enable(True), True)
    
    def test_is_screen_on(self):
        driver = self._get_device_driver()
        self.assertEqual(driver.is_screen_on(), True)
        
    def test_is_keyguard_locked(self):
        driver = self._get_device_driver()
        self.assertEqual(driver.is_keyguard_locked(), True)
    
    def test_get_mac_address(self):
        driver = self._get_device_driver()
        self.assertEqual(driver.get_mac_address(), '525400123457')
    
    def test_has_gps(self):
        driver = self._get_device_driver()
        self.assertEqual(driver.has_gps(), True)
    
    def test_get_camera_number(self):
        ADB.is_rooted = mock.Mock(return_value=True)
        driver = self._get_device_driver()
        self.assertEqual(driver.get_camera_number(), 2)
    
    def test_is_debug_package(self):
        driver = self._get_device_driver()
        self.assertEqual(driver.is_debug_package('com.tencent.demo'), True)
    
    def test__unlock_keyguard_ge_16(self):
        driver = self._get_device_driver()
        self.assertEqual(driver._unlock_keyguard_ge_16(), True)
        
if __name__ == '__main__':
    unittest.main()
    
        