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

'''
通用功能模块
'''

import os, sys
import time
import logging
import threading

class Deprecated(object):
    '''废弃函数包装
    '''
    def __init__(self, new_func):
        self._new_func = new_func
    
    def __call__(self, func):
        def warp_func(*args, **kwargs):
            frame = sys._getframe(1)
            code = frame.f_code
            file_name = os.path.split(code.co_filename)[-1]
            print >> sys.stderr, 'method %s is deprecated, called in [%s:%s], pls use %s instead' % (func.__name__, file_name, code.co_name, self._new_func)
            return func(*args, **kwargs)
        return warp_func
    
class TimeoutError(RuntimeError):
    '''超时错误
    '''
    pass

class SocketError(RuntimeError): 
    '''Socket连接错误
    '''
    pass

class AndroidSpyError(RuntimeError):
    '''测试桩返回错误
    ''' 
    pass

class ControlExpiredError(AndroidSpyError):
    '''控件失效错误
    '''
    pass

class InstallPackageFailedError(RuntimeError):
    '''应用安装失败错误
    '''
    pass

class PackageError(RuntimeError):
    '''安装包错误
    '''
    pass

def mkdir(dir_path):
    '''创建目录
    '''
    if os.path.exists(dir_path): return
    try:
        os.mkdir(dir_path)
    except WindowsError, e:
        if e.args[0] == 183:
            # 文件已经存在
            return
        raise e

def gen_log_path():
    '''生成log存放路径
    '''
    dir_root = os.environ['APPDATA']  # 为防止log文件被svn强制删除，故放在此处
    dir_root = os.path.join(dir_root, 'qt4a')
    mkdir(dir_root)
    from datetime import datetime, date
    dir_root = os.path.join(dir_root, str(date.today()))
    mkdir(dir_root)
    dt = datetime.now()
    log_name = '%s_%d.log' % (dt.strftime('%H-%M-%S'), threading.current_thread().ident)
    return os.path.join(dir_root, log_name)

logger = logging.getLogger('qt4a')
logger.setLevel(logging.DEBUG)
# logger.setLevel(logging.INFO)
# logger.setLevel(logging.WARNING)
logger.addHandler(logging.StreamHandler(sys.stdout))
fmt = logging.Formatter('%(asctime)s %(thread)d %(message)s')  # %(filename)s %(funcName)s
logger.handlers[0].setFormatter(fmt)
logger.handlers[0].setLevel(logging.WARNING)  # 屏幕日志级别为WARNING
# logger.addHandler(logging.StreamHandler(sys.stderr))

logger_path = None
try:
    logger_path = gen_log_path()
    file_handler = logging.FileHandler(logger_path)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(thread)d %(message)s')  # %(filename)s %(funcName)s
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
except KeyError:
    pass


def clear_logger_file():
    '''清空log文件
    '''
    if logger_path:
        try:
            f = open(logger_path, 'w')
            f.write('')
            f.close()
        except:
            pass

def get_default_encoding():
    import locale
    import codecs
    return codecs.lookup(locale.getpreferredencoding()).name

def set_default_encoding(code='utf8'):
    import sys
    if sys.getdefaultencoding() == code: return
    reload(sys)
    sys.setdefaultencoding(code)

def get_file_md5(file_path):
    '''计算文件md5
    '''
    import hashlib
    if not isinstance(file_path, unicode):
        file_path = file_path.decode('utf8')
    if not os.path.exists(file_path):
        raise RuntimeError('文件：%s 不存在' % file_path)
    with open(file_path, 'rb') as f:
        content = f.read()
        md5 = hashlib.md5()   
        md5.update(content)   
        return md5.hexdigest() 

class AndroidPackage(object):
    '''APK文件处理类
    '''
    def __init__(self, package_path):
        self._package_path = package_path
        if not os.path.exists(package_path):
            raise RuntimeError('安装包: %s 不存在' % package_path)
        self._file = None
    
    def _get_file(self):
        if not self._file:
            import zipfile, StringIO
            with open(self._package_path, 'rb') as f:
                apk_data = f.read()
                self._file = zipfile.ZipFile(StringIO.StringIO(apk_data), mode='r')
        return self._file
    
    def _get_manifest_xml(self):
        from _axmlparser import AXMLPrinter
        f = self._get_file()
        for i in f.namelist():
            if i == "AndroidManifest.xml":
                return AXMLPrinter(f.read(i)).get_xml_obj()
        raise PackageError('找不到AndroidManifest.xml文件')
    
    @property
    def package_name(self):
        '''包名
        '''
        manifest = self._get_manifest_xml()
        return manifest.getElementsByTagName('manifest')[0].getAttribute('package')
    
    @property
    def application_name(self):
        '''应用名
        '''
        manifest = self._get_manifest_xml()
        return manifest.getElementsByTagName('application')[0].getAttribute('android:label')
                
    @property
    def start_activity(self):
        '''启动Activity
        '''
        manifest = self._get_manifest_xml()
        for activity in manifest.getElementsByTagName('activity'):
            for filter in activity.getElementsByTagName('action'):
                if filter.getAttribute('android:name') == 'android.intent.action.MAIN':
                    return activity.getAttribute('android:name')
        raise PackageError('未找到启动Activity')
    
    @property
    def permissions(self):
        '''应用申请的权限
        ''' 
        result = []
        manifest = self._get_manifest_xml()  
        for item in manifest.getElementsByTagName('uses-permission'):
            result.append(item.getAttribute('android:name'))
        return result
    
class KeyCode(object):
    '''按键对应关系
    '''
    KEYCODE_SOFT_LEFT = 1
    KEYCODE_SOFT_RIGHT = 2
    KEYCODE_HOME = 3
    KEYCODE_BACK = 4
    KEYCODE_CALL = 5
    KEYCODE_ENDCALL = 6
    KEYCODE_0 = 7
    KEYCODE_VOLUME_UP = 24
    KEYCODE_VOLUME_DOWN = 25
    KEYCODE_POWER = 26
    KEYCODE_CAMERA = 27
    KEYCODE_CLEAR = 28
    KEYCODE_A = 29

    KEYCODE_ALT_LEFT = 57
    KEYCODE_ALT_RIGHT = 58
    KEYCODE_SHIFT_LEFT = 59  # 用于大写字母
    KEYCODE_SHIFT_RIGHT = 60

    KEYCODE_TAB = 61
    KEYCODE_SPACE = 62
    KEYCODE_SYM = 63  # 显示输入法选择框
    KEYCODE_ENTER = 66
    KEYCODE_DEL = 67
    KEYCODE_GRAVE = 68  # `
    KEYCODE_MINUS = 69  # -
    KEYCODE_EQUALS = 70  # =
    KEYCODE_LEFT_BRACKET = 71  # [
    KEYCODE_RIGHT_BRACKET = 72  # ]
    KEYCODE_BACKSLASH = 73  # \
    KEYCODE_SEMICOLON = 74  # ;
    KEYCODE_APOSTROPHE = 75  # '
    KEYCODE_SLASH = 76  # /
    KEYCODE_AT = 77  # @

    KEYCODE_FOCUS = 80  # focus the camera
    KEYCODE_PLUS = 81  # +
    KEYCODE_MENU = 82
    KEYCODE_NOTIFICATION = 83

    KEYCODE_PAGE_UP = 92
    KEYCODE_PAGE_DOWN = 93

    KEYCODE_FORWARD_DEL = 112

    KEYCODE_LANGUAGE_SWITCH = 204

    keys_map = {'{LEFT}': KEYCODE_SOFT_LEFT,
                '{RIGHT}': KEYCODE_SOFT_RIGHT,
                '{HOME}': KEYCODE_HOME,
                '{BACK}': KEYCODE_BACK,
                '{MENU}': KEYCODE_MENU,
                '{VOLUME_UP}': KEYCODE_VOLUME_UP,
                '{VOLUME_DOWN}': KEYCODE_VOLUME_DOWN,
                '{ENTER}': KEYCODE_ENTER,
                '{DEL}': KEYCODE_DEL,
                '`': KEYCODE_GRAVE,
                '-': KEYCODE_MINUS,
                '=': KEYCODE_EQUALS,
                '[': KEYCODE_LEFT_BRACKET,
                ']': KEYCODE_RIGHT_BRACKET,
                '\\': KEYCODE_BACKSLASH,
                ';': KEYCODE_SEMICOLON,
                '\'': KEYCODE_APOSTROPHE,
                '/': KEYCODE_SLASH,
                '@': KEYCODE_AT,
                '+': KEYCODE_PLUS,
                ' ': KEYCODE_SPACE,
                '\t': KEYCODE_TAB
                }

    @staticmethod
    def get_key_list(text):
        '''将字符串转换为按键列表
        '''
        i = 0
        result = []
        while i < len(text):
            asc = ord(text[i])
            if asc >= ord('0') and asc <= ord('9'):
                # 数字
                result.append(KeyCode.KEYCODE_0 + asc - ord('0'))
            elif asc >= ord('a') and asc <= ord('z'):
                # 小写字母
                result.append(KeyCode.KEYCODE_A + asc - ord('a'))
            elif asc >= ord('A') and asc <= ord('Z'):
                # 大写字母，加上SHIFT键
                result.append([KeyCode.KEYCODE_SHIFT_LEFT, KeyCode.KEYCODE_A + asc - ord('A')])
            elif asc == ord('{'):
                # 自定义按键
                end = text.find('}', i + 1)
                if end < 0:
                    raise RuntimeError('按键错误：%s' % text)
                key = text[i:end + 1]
                if not KeyCode.keys_map.has_key(key):
                    raise RuntimeError('按键错误：%s' % key)
                result.append(KeyCode.keys_map[key])
                i = end
            else:
                if not KeyCode.keys_map.has_key(text[i]):
                    raise NotImplementedError('不支持的按键：%s' % text[i])
                result.append(KeyCode.keys_map[text[i]])
            i += 1
        return result

class EnumThreadPriority(object):
    '''线程优先级
    '''
    LOWEST = 'THREAD_PRIORITY_LOWEST'  # = 19
    BACKGROUND = 'THREAD_PRIORITY_BACKGROUND'  # = 10
    LESS_FAVORABLE = 'THREAD_PRIORITY_LESS_FAVORABLE'  # = +1
    DEFAULT = 'THREAD_PRIORITY_DEFAULT'  # = 0
    MORE_FAVORABLE = 'THREAD_PRIORITY_MORE_FAVORABLE'  # = -1
    FOREGROUND = 'THREAD_PRIORITY_FOREGROUND'  # = -2
    DISPLAY = 'THREAD_PRIORITY_DISPLAY'  # = -4
    URGENT_DISPLAY = 'THREAD_PRIORITY_URGENT_DISPLAY'  # = -8
    AUDIO = 'THREAD_PRIORITY_AUDIO'  # = -16
    URGENT_AUDIO = 'THREAD_PRIORITY_URGENT_AUDIO'  # = -19
    
class ClassMethod(object):
    def __init__(self, method):
        self._method = method

    def __get__(self, instance, owner):
        if instance == None:
            self._cls = owner
        else:
            # 使用实例传入
            self._cls = instance
        return self

    def __call__(self, *args, **kws):
        # print self._method.__name__
        return self._method(self._cls, *args, **kws)

class Mutex(object):
    def __init__(self, lock):
        self._lock = lock
        
    def __enter__(self):
        time_start = time.time()
        self._lock.acquire()
        time_delta = time.time() - time_start
        if time_delta >= 0.1: logger.debug('thread %d wait %sS' % (threading.current_thread().ident, time_delta))
        
    def __exit__(self, type, value, traceback):
        self._lock.release()
            
class CrossThreadException(object):
    '''跨线程传递异常信息
    '''
    _instance = None

    def __init__(self):
        self._exception = None

    @staticmethod
    def instance():
        if not CrossThreadException._instance:
            CrossThreadException._instance = CrossThreadException()
        return CrossThreadException._instance

    @property
    def exception(self):
        return self._exception

    @exception.setter
    def exception(self, exception_info):
        self._exception = exception_info

    def check_exception(self, print_stack=True):
        if self._exception:
            if print_stack:
                import traceback
                for line in traceback.format_exception(*self._exception):
                    print >> sys.stderr, line,
            error = self._exception[1]
            self._exception = None
            raise error

class ThreadEx(threading.Thread):
    '''可以捕获异常的线程类
    '''
    def run(self):
        '''重载run方法
        '''
        import platform
        if platform.system() == "Windows":
            import pythoncom
            pythoncom.CoInitialize()
        try:
            return threading.Thread.run(self)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            # sys.excepthook(*sys.exc_info())
            logger.exception('thread %s exit' % self.getName())
            
class SharedMemory(object):
    '''共享内存
    '''
    def __init__(self, name, mem_size=256, reader=True):
        import ctypes
        self._name = name
        self._reader = reader
        PAGE_READWRITE = 0x04
        FILE_MAP_ALL_ACCESS = 0xF001F
        if not reader:
            hMapObject = ctypes.windll.kernel32.CreateFileMappingA(-1, None, PAGE_READWRITE, 0, mem_size, name)
            if hMapObject == 0:
                raise WindowsError('CreateFileMapping Failed: %d' % ctypes.windll.kernel32.GetLastError())
        else:
            hMapObject = ctypes.windll.kernel32.OpenFileMappingA(FILE_MAP_ALL_ACCESS, False, name)
            if hMapObject == 0:
                raise WindowsError('OpenFileMapping Failed: %d' % ctypes.windll.kernel32.GetLastError())
        self._hMapObject = hMapObject
        self._mmap = ctypes.windll.kernel32.MapViewOfFile(hMapObject, FILE_MAP_ALL_ACCESS, 0, 0, mem_size)
        if self._mmap == 0:
            raise WindowsError('MapViewOfFile Failed: %d' % ctypes.windll.kernel32.GetLastError())

    def write(self, msg=''):
        import ctypes
        memcpy = ctypes.cdll.msvcrt.memcpy
        memcpy(self._mmap, msg, len(msg))

    def read(self):
        import ctypes
        pBuf_str = ctypes.cast(self._mmap, ctypes.c_char_p)
        return pBuf_str.value

    def close(self):
        import ctypes
        ctypes.windll.kernel32.UnmapViewOfFile(self._mmap)
        ctypes.windll.kernel32.CloseHandle(self._hMapObject)
        self._mmap = 0
        self._hMapObject = 0

def get_root_path():
    '''获取根目录，支持py2exe打包后
    '''
    if hasattr(sys, "frozen"):
        # py2exe打包的
        return os.path.join(os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding())), 'library.zip')
    return os.path.dirname(unicode(eval('__file__'), sys.getfilesystemencoding()))

def is_mutibyte_string(data):
    '''判断是否是多字节字符串
    '''
    if not isinstance(data, unicode):
        data = data.decode('utf8')
    for c in data:
        if ord(c) > 256: return True
    return False

def get_string_hashcode(s):
    '''计算java中String的hashcode值
     * Returns a hash code for this string. The hash code for a 
     * <code>String</code> object is computed as 
     * <blockquote><pre> 
     * s[0]*31^(n-1) + s[1]*31^(n-2) + ... + s[n-1] 
     * </pre></blockquote> 
     * using <code>int</code> arithmetic, where <code>s[i]</code> is the 
     * <i>i</i>th character of the string, <code>n</code> is the length of 
     * the string, and <code>^</code> indicates exponentiation. 
     * (The hash value of the empty string is zero.) 
    '''
    if not isinstance(s, unicode):
        s = s.decode('utf8')
    ret = 0
    max_val = 0x80000000
    for c in s:
        ret = ret * 31 + ord(c)
        ret %= max_val * 2
        if ret >= max_val:
            ret -= max_val * 2
    return ret

def get_intersection(rect1, rect2):
    '''计算两个区域的交集
    '''
    rect1 = list(rect1)
    rect2 = list(rect2)
    if rect1[0] < rect2[0]:
        rect1[0] = rect2[0]
        rect1[2] = rect2[0] + rect2[2] - rect1[0]
    if rect1[0] + rect1[2] > rect2[0] + rect2[2]:
        rect1[2] = rect2[0] + rect2[2] - rect1[0]
    if rect1[1] < rect2[1]:
        rect1[1] = rect2[1]
        rect1[3] = rect2[1] + rect2[3] - rect1[1]
    if rect1[1] + rect1[3] > rect2[1] + rect2[3]:
        rect1[3] = rect2[1] + rect2[3] - rect1[1]
    return rect1

if __name__ == '__main__':
    pass
    
