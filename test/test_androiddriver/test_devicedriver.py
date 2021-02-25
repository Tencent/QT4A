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

"""devicedriver模块单元测试
"""

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
    if args[0] == "sh":
        if args[1] == "/data/local/tmp/qt4a/SpyHelper.sh":
            if args[2] == "getLanguage":
                return "zh"
            elif args[2] == "getCountry":
                return "CN"
            elif args[2] == "getExternalStorageDirectory":
                return "/storage/sdcard"
            elif args[2] == "getScreenSize":
                return "800, 1280"
            elif args[2] == "getClipboardText":
                return "1234"
            elif args[2] == "isScreenLockEnabled":
                return "true"
            elif args[2] == "setScreenLockEnable":
                return "true"
            elif args[2] == "isScreenOn":
                return "true"
            elif args[2] == "isKeyguardLocked":
                return "true"
            elif args[2] == "getWlanMac":
                return "52:54:00:12:34:57"
            elif args[2] == "hasGPS":
                return "true"
            elif args[2] == "getCameraNumber":
                return "2"
            elif args[2] == "getDeviceImei":
                return "180322023834592"
            elif args[2] == "sendKey":
                return "true"
            elif args[2] == "isDebugPackage":
                return "true"
            else:
                raise NotImplementedError(args[2])
    elif args[0] == "am":
        if args[1] == "start":
            activity = ""
            if args[2] == "-n":
                activity = args[3]
            if not "-w" in args:
                return "Starting: Intent { cmp=%s }" % activity
    elif args[0] == "getprop":
        if args[1] == "ro.build.version.sdk":
            return 25
    elif args[0] == "dumpsys":
        if args[1] == "window":
            return """WINDOW MANAGER POLICY STATE (dumpsys window policy)
    mSafeMode=false mSystemReady=true mSystemBooted=true
    mLidState=-1 mLidOpenRotation=-1 mCameraLensCoverState=-1 mHdmiPlugged=false
    mLastSystemUiFlags=0x8708 mResettingSystemUiFlags=0x0 mForceClearedSystemUiFlags=0x0
    mWakeGestureEnabledSetting=true
    mSupportAutoRotation=true
    mUiMode=1 mDockMode=0 mEnableCarDockHomeCapture=true mCarDockRotation=-1 mDeskDockRotation=-1
    mUserRotationMode=1 mUserRotation=0 mAllowAllRotations=-1
    mCurrentAppOrientation=5
    mCarDockEnablesAccelerometer=true mDeskDockEnablesAccelerometer=true
    mLidKeyboardAccessibility=0 mLidNavigationAccessibility=0 mLidControlsScreenLock=false
 mLidControlsSleep=false
     mLongPressOnBackBehavior=0
    mShortPressOnPowerBehavior=1 mLongPressOnPowerBehavior=1
    mDoublePressOnPowerBehavior=103 mTriplePressOnPowerBehavior=102
    mHasSoftInput=true
    mAwake=true
    mScreenOnEarly=true mScreenOnFully=true
    mKeyguardDrawComplete=true mWindowManagerDrawComplete=true
    mOrientationSensorEnabled=false
    mOverscanScreen=(0,0) 1080x2220
    mRestrictedOverscanScreen=(0,0) 1080x2094
    mUnrestrictedScreen=(0,0) 1080x2220
    mRestrictedScreen=(0,0) 1080x2094
    mStableFullscreen=(0,0)-(1080,2094)
    mStable=(0,63)-(1080,2094)
    mSystem=(0,0)-(1080,2220)
    mCur=(0,63)-(1080,2094)
    mContent=(0,63)-(1080,2094)
    mVoiceContent=(0,63)-(1080,2094)
    mDock=(0,63)-(1080,2094)
    mDockLayer=268435456 mStatusBarLayer=181000
    mShowingDream=false mDreamingLockscreen=false mDreamingSleepToken=null
    mDismissImeOnBackKeyPressed=false
    mStatusBar=Window{b4b1c0a u0 StatusBar} isStatusBarKeyguard=false
    mNavigationBar=Window{664e3be u0 NavigationBar}
    mFocusedWindow=Window{f38bf69 u0 com.sec.android.app.launcher/com.sec.android.app.launcher.activities.LauncherActivity}
    mFocusedApp=Token{34a5839 ActivityRecord{6f9c800 u0 com.sec.android.app.launcher/.activities.LauncherActivity t63038}}
    mTopFullscreenOpaqueWindowState=Window{f38bf69 u0 com.sec.android.app.launcher/com.sec.android.app.launcher.activities.LauncherActivity}
    mTopFullscreenOpaqueOrDimmingWindowState=Window{f38bf69 u0 com.sec.android.app.launcher/com.sec.android.app.launcher.activities.LauncherActivity}
    mTopIsFullscreen=false mKeyguardOccluded=false
 mKeyguardOccludedChanged=false
 mPendingKeyguardOccluded=false"""
    raise NotImplementedError(args)


class TestDeviceDriver(unittest.TestCase):
    """DeviceDriver类测试用例
    """

    def _get_device_driver(self):
        ADB.run_shell_cmd = mock.Mock(side_effect=mock_run_shell_cmd)
        adb_backend = LocalADBBackend("127.0.0.1", "")
        adb = ADB(adb_backend)
        return DeviceDriver(adb)

    def test_get_language(self):
        driver = self._get_device_driver()
        self.assertEqual(driver.get_language(), "zh")

    def test_get_country(self):
        driver = self._get_device_driver()
        self.assertEqual(driver.get_country(), "CN")

    def test_get_external_sdcard_path(self):
        ADB.is_rooted = mock.Mock(return_value=False)
        driver = self._get_device_driver()
        self.assertEqual(driver.get_external_sdcard_path(), "/storage/sdcard")

    def test_get_screen_size(self):
        ADB.is_rooted = mock.Mock(return_value=False)
        driver = self._get_device_driver()
        self.assertEqual(driver.get_screen_size(), (800, 1280))

    def test_get_clipboard_text(self):
        ADB.is_rooted = mock.Mock(return_value=False)
        driver = self._get_device_driver()
        self.assertEqual(driver.get_clipboard_text(), "1234")

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
        self.assertEqual(driver.get_mac_address(), "525400123457")

    def test_has_gps(self):
        driver = self._get_device_driver()
        self.assertEqual(driver.has_gps(), True)

    def test_get_camera_number(self):
        ADB.is_rooted = mock.Mock(return_value=True)
        driver = self._get_device_driver()
        self.assertEqual(driver.get_camera_number(), 2)

    def test_is_debug_package(self):
        driver = self._get_device_driver()
        self.assertEqual(driver.is_debug_package("com.tencent.demo"), True)

    def test__unlock_keyguard_ge_16(self):
        driver = self._get_device_driver()
        self.assertEqual(driver._unlock_keyguard_ge_16(), True)

    def test__get_current_window(self):
        driver = self._get_device_driver()
        self.assertEqual(
            driver._get_current_window(),
            "com.sec.android.app.launcher.activities.LauncherActivity",
        )


if __name__ == "__main__":
    unittest.main()

