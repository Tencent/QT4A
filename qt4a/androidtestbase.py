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
import shutil
import tempfile
import traceback

import testbase.testcase as tc
from testbase import logger as qta_logger
from testbase.testresult import EnumLogLevel
from testbase.conf import settings
from tuia.env import run_env, EnumEnvType

from qt4a.androiddriver import util
from qt4a.device import Device, DeviceProviderManager
from qt4a.androidapp import AndroidApp

util.set_default_encoding('utf8')  # 修改默认编码
 
class EnumCrashType(object):
    '''枚举crash类型
    '''
    NATIVE_SYSTEM_CRASH = "Native系统Crash"
    NATIVE_NONE_SYSTEM_CRASH = "Native非系统Crash" 
    JAVA_CRASH = "Java Crash"
    OTHER_CRASH = "其他类型Crash"

def get_valid_file_name(file_name):
    '''过滤掉文件名中的非法字符
    '''
    for c in (':', '?'):
        file_name = file_name.replace(c, '_')
    return file_name

class AndroidTestBase(tc.TestCase):
    '''QT4A测试基类
    '''
    
    def init_test(self, testresult):
        '''初始化测试环境。慎用此函数，尽量将初始化放到preTest里。
        '''
        super(AndroidTestBase, self).init_test(testresult)
        self._run_device = None
        self._target_crash_proc_list = []
        self._check_log_called = False

    initTest = init_test   
    
    def post_test(self):
        '''清理测试用例
        '''
        self._run_test_complete = True
        if hasattr(self, '_record_thread_status_dict') and self._record_thread_status_dict:
            timeout = 30
            time0 = time.time()
            while time.time() - time0 < timeout:
                for key in self._record_thread_status_dict:
                    if not self._record_thread_status_dict[key]: break
                else:
                    break
                time.sleep(0.1)
            else:
                qta_logger.warn('wait for record screen thread exit timeout')
            
        self._save_logcat()
        self._save_qt4a_log()
        if hasattr(self, '_logcat_debug_level_list'):
            for device in Device.device_list:
                device_name = '%s' % device.device_id
                if device_name not in self._logcat_debug_level_list:
                    msg = '设备:%s中的logcat没有debug级别的日志，请检查手机日志级别设置 ' % device_name
                    if self._check_log_called:
                        qta_logger.error(msg)
                    else:
                        qta_logger.warn(msg)

        if hasattr(settings, 'QT4A_DEVICE_HOSTS'):
            for device in Device.device_list:
                self.log_info('恢复设备: %s hosts环境' % device.device_id)
                device.modify_hosts()

 
    postTest = post_test
 
    def clean_test(self):
        '''清理测试环境。慎用此函数，尽量将清理放到postTest里。
        '''
        super(AndroidTestBase, self).clean_test()
        Device.release_all_device()  # 释放所有设备

    cleanTest = clean_test

    def acquire_device(self, device_id=None, **kwargs):
        '''申请设备接口
        
        :param device_id: 设备ID，用于本地调试
        :type device_id:  string
        '''
        if device_id:
            kwargs['id'] = device_id
        resource = self.test_resources.acquire_resource('android', condition=kwargs)
        device = DeviceProviderManager().connect_device(resource)
        if not device: raise RuntimeError('Connect device %s failed' % resource)

        try:    
            self.test_result.log_record(EnumLogLevel.Environment, '申请 %s 设备成功：%s(%s)' % ('Android', device.model, device.device_id), {"device":device.imei})
        except Exception as e:
            qta_logger.warn('GetDeviceImei error:%s' % e)

        if hasattr(settings, 'QT4A_DEVICE_HOSTS'):
            device_hosts = settings.QT4A_DEVICE_HOSTS
            if device_hosts:
                self.logInfo('设置设备hosts为：\n%s' % device_hosts)
                host_list = []
                pattern = re.compile(r'\s*(\S+)\s+(\S+)\s*')
                for line in device_hosts.split('\n'):
                    line = line.strip()
                    if not line: continue
                    ret = pattern.match(line)
                    if not ret: raise RuntimeError('hosts格式错误: %r' % line)
                    host_list.append((ret.group(1), ret.group(2)))
                device.modify_hosts(host_list)
            
        self.add_logcat_callback(device)
        
        if hasattr(settings, 'QT4A_RECORD_SCREEN') and settings.QT4A_RECORD_SCREEN == True:
            if not hasattr(self, '_record_thread_status_dict'):
                self._record_thread_status_dict = {}
            self._record_thread_status_dict[device.device_id] = False
            qta_logger.info('%s start record screen thread' % device.device_id)
            t = util.ThreadEx(target=self._record_screen_thread, args=(device,), name='Device Record Screen Thread')
            t.setDaemon(True)
            t.start()
        device.adb.start_logcat()
        return device

    def get_extra_fail_record(self):
        '''用例执行失败时，用于获取用例相关的错误记录和附件信息
        '''
        from qt4a.androiddriver.util import logger as qt4a_logger
        pic_attachments = {}
        for device in Device.device_list:
            pic_path = "%s_%s_%s.png" % (self.__class__.__name__, get_valid_file_name(device.device_id), time.time())
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
        
        device = app_or_device
        if isinstance(app_or_device, AndroidApp):
            device = app_or_device.device
        path = self.__class__.__name__ + '_' + get_valid_file_name(device.device_id) + '_' + str(int(time.time())) + '.jpg'
        device.take_screen_shot(path)
        self.test_result.info(info, attachments={'截图':path})
    
    def _record_screen_thread(self, device):
        '''录屏线程
        '''
        from qt4a.androiddriver.devicedriver import qt4a_path
        record_time = 4 * 1000  # 每次录制的时间
        framerate = 8
        quality = 20
        remote_tmp_path_tmpl = '%s/screen.record.%%d' % qt4a_path
        max_record_file_count = 4  # 最大临时存储的录屏文件数目
        index = 0
        device.delete_file('%s/screen.record.*' % qt4a_path)
        
        while not hasattr(self, '_run_test_complete') or self._run_test_complete == False:
            # 尚未结束
            remote_tmp_path = remote_tmp_path_tmpl % (index % max_record_file_count)
            device.run_shell_cmd('%s/screenshot record -p %s -t %d -f %d -q %d' % (qt4a_path, remote_tmp_path, record_time, framerate, quality))
            index += 1
            if index >= max_record_file_count: index -= max_record_file_count
            
        if not self.test_result.passed:
            merge_file_list = []
            for i in range(max_record_file_count):
                merge_file_list.append(remote_tmp_path_tmpl % ((i + index) % max_record_file_count))
            device.run_shell_cmd('cat %s > %s' % (' '.join(merge_file_list), remote_tmp_path_tmpl % max_record_file_count))
            local_tmp_path = tempfile.mktemp('.record')
            device.pull_file(remote_tmp_path_tmpl % max_record_file_count, local_tmp_path)
            save_dir = tempfile.mkdtemp('.screenshot')
            frame_list = Device.extract_record_frame(local_tmp_path, save_dir)
            video_path = self.__class__.__name__ + '_' + get_valid_file_name(device.device_id) + '_' + str(int(time.time())) + '.mp4'
            result = Device.screen_frame_to_video(frame_list, framerate, video_path)
            if result == None:
                qta_logger.warn('opencv not installed')
            else:
                self.test_result.info('最近15秒录屏', attachments={video_path: video_path})
            shutil.rmtree(save_dir)
        
        self._record_thread_status_dict[device.device_id] = True
        
    def _save_qt4a_log(self):
        '''保存QT4A日志
        '''
        if run_env == EnumEnvType.Lab or (hasattr(settings, 'QT4A_UPLOAD_QT4A_LOG') and settings.QT4A_UPLOAD_QT4A_LOG == True):
            filename = 'qt4a_%s_%s.log' % (self.__class__.__name__, int(time.time()))
            shutil.copyfile(util.logger_path, filename)
            self.test_result.info('QT4A日志', attachments={filename: filename})
            util.clear_logger_file()
            
    def _save_logcat(self):
        '''保存logcat日志
        '''
        crash_files = {}
        logcat_files = {}
        crash_type = ''
        for device in Device.device_list:
            device.adb.stop_logcat()
            ret_type, crash_path = self.extract_crash_from_logcat(device.adb.get_log(False))
            devicename = '设备:%s' % device.device_id
            if crash_path:
                crash_type = ret_type
                crash_files[devicename] = crash_path
            log_path = '%s_%s_%s.log' % (self.__class__.__name__, get_valid_file_name(device.device_id), int(time.time()))
            device.adb.save_log(log_path)
            if os.path.isfile(log_path):
                logcat_files[devicename] = log_path
            else:
                self.test_result.warning('保存logcat文件: %s失败' % log_path)
                      
        if logcat_files: 
            if not self.test_result.passed or crash_files or (hasattr(settings, 'UPLOAD_LOGCAT_WHEN_PASS') and settings.UPLOAD_LOGCAT_WHEN_PASS):
                try:
                    self.test_result.info('logcat日志', attachments=logcat_files)
                except:
                    qta_logger.exception('上传logcat文件[%s]失败' % logcat_files)

        if crash_files:
            crash_title = "系统Crash(可不提单)：" if crash_type == EnumCrashType.NATIVE_SYSTEM_CRASH else "App Crash错误报告："
            self.test_result.log_record(EnumLogLevel.APPCRASH, crash_title, attachments=crash_files)

    def extract_crash_from_logcat(self, log_list):
        '''检测logcat日志中是否有crash发生并萃取出相关日志
        '''
        from qt4a.androiddriver.util import logger as qt4a_logger
        pattern_list = self.extract_crash_by_patterns()
        if self._target_crash_proc_list == []:  # 表示用户不关心任何进程的crash问题，则不对crash进行提取
            return None, None
        
        if not isinstance(pattern_list, list) and not isinstance(pattern_list, tuple) and not len(pattern_list) == 2:
            raise RuntimeError('传入的pattern_list不是列表或二元组')
        if isinstance(pattern_list, tuple):
            pattern_list = [pattern_list]
        
        new_pattern_list = []
        for proc in self._target_crash_proc_list:
            if not isinstance(proc, str):
                qt4a_logger.warn('传入的process不是字符串类型')
                continue
            for pattern in pattern_list:
                if not isinstance(pattern, tuple) or not len(pattern) == 2:
                    qt4a_logger.warn('传入的pattern不是二元组')
                else:
                    new_pattern_list.append((proc,) + pattern)  
            new_pattern_list.append((proc,) + (r'AndroidRuntime', r'FATAL EXCEPTION:.*'))  # system crash1:java crash
            # new_pattern_list.append((proc,) + (r'dalvikvm', r'threadid=.*: thread exiting with uncaught exception .*')) #与system crash1重复，暂时注释掉,优先取system crash1   
            native_crash_pattern = r'pid: \d+, tid: \d+, name: .*>>> ' + '(' + proc + ')' + r' <<<'
            new_pattern_list.append((r'/system/bin/debuggerd', r'DEBUG', native_crash_pattern))  # system crash2:native crash
        # new_pattern_list.append((r'/system/bin/debuggerd', r'DEBUG', r'signal \d+ \(.*\), code \d+ \(.*\), fault addr.*')) #fault addr crash与上一行的system crash2重复，优先取system crash2
        
        if new_pattern_list == []:  # 因为可能随着需求变更，没有规则写入
            return None, None
        
        crash_info = ''
        pattern = r'\[(.*)\(\d+\)\] \[.*\] (.)/(.*)\((\d+)\): (.*)'
        form_log_dict = {}
        regex = re.compile(pattern)        
        for log in log_list:
            res = regex.match(log)
            if res:
                cur_line = {'process_name': res.group(1), 'level': res.group(2), 'tag':res.group(3), 'part_log': res.group(5), 'line_log': log}  # res.group(1)是进程名process_name的正则表达式，res.group(2)是错误级别level的正则表达式，res.group(3)是标签tag的正则表达式，res.group(4)是线程id的正则表达式，res.group(5)是线程id后的冒号后开始到本行结尾内容的正则表达式，line_log存储整行日志log。
                if res.group(4) in form_log_dict:
                    form_log_dict[res.group(4)].append(cur_line)
                else:
                    form_log_dict[res.group(4)] = [cur_line]
            else:
                qt4a_logger.warn("提取crash日志时，log:%s无法按格式%s解析" % (log, pattern))
        crash_list = []
        for tlog_list in form_log_dict.values():
            is_crashed = False
            tag = ''
            last_pattern_list = []
            for tlog_dict in tlog_list:
                if is_crashed == True and tag == tlog_dict['tag']:
                    crash_info += tlog_dict['line_log'] + '\n'  
                    crash_list.append(tlog_dict)
                    continue
                if not last_pattern_list:
                    for pat_tuple in new_pattern_list:
                        process_name_reg = re.compile(pat_tuple[0])
                        if not process_name_reg.match(tlog_list[0]['process_name']):
                            continue
                        last_pattern_list.append(pat_tuple)
                    if len(last_pattern_list) == 0:
                        break
                is_crashed = False    
                for pat_tuple in last_pattern_list:
                    tag_reg = re.compile(pat_tuple[1])
                    tag = tlog_dict['tag']
                    if not tag_reg.match(tag):
                        continue
                    part_log_reg = re.compile(pat_tuple[2])
                    if not part_log_reg.match(tlog_dict['part_log']):
                        continue
                    is_crashed = True
                    crash_list.append(tlog_dict)
                    crash_info += tlog_dict['line_log'] + '\n'  
                    break
        if crash_info:
            crash_type = self.check_crash_type(crash_list)
            crash_path = '%s_%s.crash.log' % (self.__class__.__name__, int(time.time()))
            with open(crash_path, 'w') as fd:
                fd.write(crash_info)
            return crash_type, crash_path
        return None, None
    
    def check_crash_type(self, crash_list): 
        system_so_cnt = 3
        match_backtrace_begin = False
        # system_crash_demo:#01  pc 0002eed0  /system/lib/libgui.so (_ZN7android7Surface11queueBufferEP19ANativeWindowBufferi)
        system_crash_pattern = r'#\d{2}  pc \w{8}  (/system/lib/.*\.so|/system/vendor/.*\.so)($| \(.*\))'
        system_crash_reg = re.compile(system_crash_pattern)
        system_so_set = set([])
        for tlog_dict in crash_list:
            if tlog_dict['tag'] == 'native_eup':
                res = system_crash_reg.match(tlog_dict['part_log'])
                if match_backtrace_begin and res:
                    system_so_set.add(res.group(1))
                    if len(system_so_set) == system_so_cnt:
                        return EnumCrashType.NATIVE_SYSTEM_CRASH                    
                elif tlog_dict['part_log'] == 'unwind_backtrace_with_ptrace start':
                    match_backtrace_begin = True
                elif 'unwinded end stack_depth' in tlog_dict['part_log']:
                    match_backtrace_begin = False  
                    system_so_set = set([])              
        return EnumCrashType.OTHER_CRASH

    def extract_crash_by_patterns(self):
        return None
    
    def add_logcat_callback(self, device):
        '''判断logcat日志中是否包含debug级别的日志，如果没有，很有可能该手机可以设置日志级别，且本身已设置了过滤debug级别的日志,可尝试操作手机设置
        '''
        if not hasattr(self, '_logcat_debug_level_list'):self._logcat_debug_level_list = []
        def wrap_func(pid, process_name, date, timestamp, level, tag, tid, content):
            device_name = '%s' % device.device_id
            if device_name in self._logcat_debug_level_list:
                return
            if level in ['D', 'V']:
                self._logcat_debug_level_list.append(device_name)
        device.adb.add_logcat_callback(wrap_func)

if __name__ == '__main__':
    pass
