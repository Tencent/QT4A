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

'''Android自动化测试基类
'''

import sys, os, platform
import time
import re
import traceback
from androiddriver import util
from androiddriver.util import set_default_encoding
from device import Device

set_default_encoding('utf8')  # 修改默认编码
 
class OutStream(object):
    '''重载输出流，以便在cmd中显示中文
    '''
    def __init__(self, stdout):
        self._stdout = stdout
    
    @property
    def encoding(self):
        return 'utf8'
    
    def write(self, s):
        if not isinstance(s, unicode):
            try:
                s = s.decode('utf8')
            except UnicodeDecodeError:
                try:
                    s = s.decode('gbk')  # sys.getdefaultencoding()
                except UnicodeDecodeError:
                    s = 'Decode Error: %r' % s
                    # s = s.encode('raw_unicode_escape') #不能使用GBK编码
        try:
            ret = self._stdout.write(s)
            self.flush()
            return ret
        except UnicodeEncodeError:
            pass
 
    def flush(self):
        return self._stdout.flush()
 
sys.stdout = sys.stderr = OutStream(sys.stdout)  # 重定向输出流

try:
    import testbase
except ImportError:
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    new_egg = os.path.join(root_path, 'exlib', 'qtaf.egg')
    if os.path.exists(new_egg):
        sys.path.insert(0, new_egg)
    else:
        sys.path.insert(0, os.path.join(root_path, 'site', 'qtaf.egg'))

import testbase.testcase as tc
import testbase.logger as logger
from testbase import testresult
from tuia.env import run_env, EnumEnvType

def _get_valid_file_name(file_name):
    '''过滤掉文件名中的非法字符
    '''
    for c in (':', '?'):
        file_name = file_name.replace(c, '_')
    return file_name

def get_valid_file_name(file_name):
    return _get_valid_file_name(file_name)

class AndroidTestBase(tc.TestCase):
    '''QT4A测试基类
    '''
    # 2014/08/07 banana 增加get_used_devices
    # 2015/01/15 banana 增加extract_crash_from_logcat
    # 2015/04/23 banana 改用QTAF5

    def initTest(self, testresult):
        '''初始化测试环境。慎用此函数，尽量将初始化放到preTest里。
        '''
        super(AndroidTestBase, self).initTest(testresult)

    def postTest(self):
        '''清理测试用例
        '''            
        self._save_logcat()
        self._save_qt4a_log()
        if run_env == EnumEnvType.Lab:
            env = self.environ
            if env.has_key('DEVICE_HOSTS'):
                for device in Device.device_list:
                    self.logInfo('恢复设备: %s hosts环境' % device.device_id)
                    device.modify_hosts()
        
    def cleanTest(self):
        '''清理测试环境。慎用此函数，尽量将清理放到postTest里。
        '''
        Device.release_all_device()  # 释放所有设备
        if run_env == EnumEnvType.Lab:
            # 杀掉adb server，防止hold住一些文件
            from androiddriver.adb import ADB
            ADB.close()

    def acquire_device(self, device_id=None, **kwds):
        '''申请设备接口
        
        :param device_id: 设备ID，用于本地调试
        :type device_id:  string
        '''
        from testbase.testresult import EnumLogLevel
        device = Device(device_id, kwds)
        self.test_result.log_record(EnumLogLevel.Environment, '申请 %s 设备成功：%s(%s)' % ('Android', device.module, device.device_id), {"device":device.imei})
        if run_env == EnumEnvType.Lab:
            if self.environ.has_key('DEVICE_HOSTS'):
                self.logInfo('设置设备hosts为：\n%s' % self.environ['DEVICE_HOSTS'])
                host_list = []
                pattern = re.compile(r'\s*(\S+)\s+(\S+)\s*')
                for line in self.environ['DEVICE_HOSTS'].split('\n'):
                    ret = pattern.match(line)
                    if not ret: raise RuntimeError('hosts格式错误: %r' % line)
                    host_list.append((ret.group(1), ret.group(2)))
                device.modify_hosts(host_list)
        return device
    
    def get_extra_fail_record(self):
        '''用例执行失败时，用于获取用例相关的错误记录和附件信息
        '''
        from androiddriver.util import logger as qt4a_logger
        pic_attachments = {}
        for device in Device.device_list:
            pic_path = "%s_%s_%s.png" % (self.__class__.__name__, _get_valid_file_name(device.device_id), time.time())
            try:
                device.take_screen_shot(pic_path)
                if os.path.isfile(pic_path):
                    pic_attachments['%s的截图' % device.device_id] = pic_path
                else:
                    qt4a_logger.error('pic %s not exist' % pic_path)
            except Exception as e:
                qt4a_logger.error('take_screen_shot error: %s' % e)
                qt4a_logger.error(''.join(traceback.format_tb(sys.exc_info()[2])))
        return {}, pic_attachments

    def take_screen_shot(self, app_or_device, info):
        '''生成当前指定设备的屏幕截图
        
        :param app: AndroidApp类或AndroidDevice实例
        :type app:  AndroidApp or AndroidDevice
        :param info: 显示的提示信息
        :type info:  string
        '''
        from androidapp import AndroidApp
        device = app_or_device
        if isinstance(app_or_device, AndroidApp):
            device = app_or_device.device
        path = self.__class__.__name__ + '_' + _get_valid_file_name(device.device_id) + '_' + str(int(time.time())) + '.png'
        device.take_screen_shot(path)
        self.test_result.info(info, attachments={'截图':path})
        
    def _save_qt4a_log(self):
        '''保存QT4A日志
        '''
        if run_env == EnumEnvType.Lab:
            filename = 'qt4a_%s_%s.log' % (self.__class__.__name__, int(time.time()))
            self.test_result.info('QT4A日志', attachments={filename: util.logger_path})
            util.clear_logger_file()
            
    def _save_logcat(self):
        '''保存logcat日志
        '''
        from testbase.testresult import EnumLogLevel
        crash_files = {}
        logcat_files = {}
        for device in Device.device_list:
            device.adb.stop_logcat()
            if run_env == EnumEnvType.Lab:
                log_path = '%s_%s_%s.log' % (self.__class__.__name__, _get_valid_file_name(device.device_id), int(time.time()))
                device.adb.save_log(log_path)
                devicename = '设备:%s' % device.device_id
                if os.path.isfile(log_path):
                    logcat_files[devicename] = log_path
                    crashinfo_log_path = self.extract_crash_from_logcat(log_path)
                    if crashinfo_log_path:
                        crash_files[devicename] = crashinfo_log_path
                else:
                    self.test_result.warning('保存logcat文件: %s失败' % log_path)
        if logcat_files: 
            self.test_result.info('logcat日志', attachments=logcat_files)
        if crash_files:
            self.test_result.log_record(EnumLogLevel.APPCRASH, "App Crash错误报告：", attachments=crash_files)

    def extract_crash_from_logcat(self, logcat_path):
        '''检测logcat中是否有crash发生并萃取出相关日志
        '''
        pass


if __name__ == '__main__':
    pass
