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

from __future__ import print_function
import six
import logging
import os
import sys
import threading
import time


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
            print('method %s is deprecated, called in [%s:%s], pls use %s instead' % (func.__name__, file_name, code.co_name, self._new_func), file=sys.stderr)
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


class ProcessExitError(RuntimeError):
    '''进程退出错误
    '''
    pass


class ControlExpiredError(AndroidSpyError):
    '''控件失效错误
    '''
    pass


class ControlAmbiguousError(AndroidSpyError):
    '''控件重复错误
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


class PermissionError(RuntimeError):
    '''权限错误
    '''
    pass


class QT4ADriverNotInstalled(Exception):
    '''QT4A驱动错误
    '''
    pass


class OutStream(object):
    '''重载输出流，以便在cmd中显示中文
    '''

    def __init__(self, stdout):
        self._stdout = stdout

    @property
    def encoding(self):
        return 'utf8'

    def write(self, s):
        if six.PY2 and (not isinstance(s, unicode)):
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


def mkdir(dir_path):
    '''创建目录
    '''
    if os.path.exists(dir_path): return
    try:
        os.makedirs(dir_path)
    except OSError as e:
        if e.args[0] == 183 or e.args[0] == 17:
            # 文件已经存在
            return
        raise e


def gen_log_path():
    '''生成log存放路径
        优先使用环境变量[LOG_PATH_PREFIX], 若不存在则使用[APPDATA] / [HOME]
    '''
    dir_root = os.environ.get('LOG_PATH_PREFIX', os.environ['APPDATA' if sys.platform == 'win32' else 'HOME'])

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
logger.addHandler(logging.StreamHandler(OutStream(sys.stdout)))
fmt = logging.Formatter('%(asctime)s %(thread)d %(message)s')  # %(filename)s %(funcName)s
logger.handlers[0].setFormatter(fmt)
logger.handlers[0].setLevel(logging.WARNING)  # 屏幕日志级别为WARNING
# logger.addHandler(logging.StreamHandler(sys.stderr))

logger_path = gen_log_path()
file_handler = logging.FileHandler(logger_path)
fmt = logging.Formatter('%(asctime)s %(levelname)s %(thread)d %(message)s')  # %(filename)s %(funcName)s
file_handler.setFormatter(fmt)
logger.addHandler(file_handler)


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
    if six.PY2: 
        if sys.getdefaultencoding() == code: return
        reload(sys)
        sys.setdefaultencoding(code)


def get_file_md5(file_path):
    '''计算文件md5
    '''
    import hashlib
    if six.PY2 and (not isinstance(file_path, unicode)):
        file_path = file_path.decode('utf8')
    if not os.path.exists(file_path):
        raise RuntimeError('文件：%s 不存在' % file_path)
    with open(file_path, 'rb') as f:
        content = f.read()
        md5 = hashlib.md5()
        md5.update(content)
        return md5.hexdigest()


class static_property(property):
    '''静态属性
    '''

    def __init__(self, *args, **kwargs):
        super(static_property, self).__init__(*args, **kwargs)
        self._value_dict = {}

    def __get__(self, obj, cls):
        if not id(obj) in self._value_dict:
            self._value_dict[id(obj)] = super(static_property, self).__get__(obj, cls)
        return self._value_dict[id(obj)]


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
            import zipfile
            from io import BytesIO
            with open(self._package_path, 'rb') as f:
                apk_data = f.read()
                self._file = zipfile.ZipFile(BytesIO(apk_data), mode='r')
        return self._file

    def _get_manifest_xml(self):
        from qt4a.androiddriver._axmlparser import AXMLPrinter
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
    def version(self):
        '''应用版本
        '''
        manifest = self._get_manifest_xml()
        return manifest.getElementsByTagName('manifest')[0].getAttribute('android:versionName')

    @property
    def start_activity(self):
        '''启动Activity
        '''
        manifest = self._get_manifest_xml()
        for activity in manifest.getElementsByTagName('activity'):
            for filter in activity.getElementsByTagName('action'):
                if filter.getAttribute('android:name') == 'android.intent.action.MAIN':
                    return activity.getAttribute('android:name')
        for activity in manifest.getElementsByTagName('activity-alias'):
            for filter in activity.getElementsByTagName('action'):
                if filter.getAttribute('android:name') == 'android.intent.action.MAIN':
                    return activity.getAttribute('android:targetActivity')
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

    KEYCODE_DPAD_UP = 19
    KEYCODE_DPAD_DOWN = 20
    KEYCODE_DPAD_LEFT = 21
    KEYCODE_DPAD_RIGHT = 22

    KEYCODE_VOLUME_UP = 24
    KEYCODE_VOLUME_DOWN = 25
    KEYCODE_POWER = 26
    KEYCODE_CAMERA = 27
    KEYCODE_CLEAR = 28
    KEYCODE_A = 29

    KEYCODE_COMMA = 55
    KEYCODE_PERIOD = 56
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

    KEYCODE_ESCAPE = 111
    KEYCODE_FORWARD_DEL = 112
    KEYCODE_CTRL_LEFT = 113
    KEYCODE_CTRL_RIGHT = 114

    KEYCODE_MOVE_HOME = 122
    KEYCODE_MOVE_END = 123

    KEYCODE_ZOOM_IN = 168
    KEYCODE_ZOOM_OUT = 169

    KEYCODE_LANGUAGE_SWITCH = 204

    KEYCODE_SLEEP = 223
    KEYCODE_WAKEUP = 224

    keys_map = {
        '{LEFT}': KEYCODE_SOFT_LEFT,
        '{RIGHT}': KEYCODE_SOFT_RIGHT,
        '{HOME}': KEYCODE_HOME,
        '{BACK}': KEYCODE_BACK,
        '{MENU}': KEYCODE_MENU,
        '{VOLUME_UP}': KEYCODE_VOLUME_UP,
        '{VOLUME_DOWN}': KEYCODE_VOLUME_DOWN,
        '{ENTER}': KEYCODE_ENTER,
        '{BACKSPACE}': KEYCODE_DEL,
        '{LEFT}': KEYCODE_DPAD_LEFT,
        '{RIGHT}': KEYCODE_DPAD_RIGHT,
        '{UP}': KEYCODE_DPAD_UP,
        '{DOWN}': KEYCODE_DPAD_DOWN,
        '{DEL}': KEYCODE_FORWARD_DEL,
        '{DELETE}': KEYCODE_FORWARD_DEL,
        '{POWER}': KEYCODE_POWER,
        '{ESC}': KEYCODE_ESCAPE,
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
        '\t': KEYCODE_TAB,
        ',': KEYCODE_COMMA,
        '.': KEYCODE_PERIOD
    }

    shift_chars = {
        '~': '`',
        '!': '1',
        '#': '3',
        '$': '4',
        '%': '5',
        '^': '6',
        '&': '7',
        '*': '8',
        '(': '9',
        ')': '0',
        '_': '-',
        '=': '+',
        ':': ';',
        '"': "'",
        '<': ',',
        '>': '.',
        '?': '/'
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
                if key not in KeyCode.keys_map:
                    raise RuntimeError('按键错误：%s' % key)
                result.append(KeyCode.keys_map[key])
                i = end
            elif text[i] in KeyCode.keys_map:
                result.append(KeyCode.keys_map[text[i]])
            elif text[i] in KeyCode.shift_chars:
                keys = KeyCode.get_key_list(KeyCode.shift_chars[text[i]])
                keys.insert(0, KeyCode.KEYCODE_SHIFT_LEFT)
                result.append(keys)
            else:
                raise NotImplementedError('不支持的按键：%s' % text[i])

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
        if instance is None:
            self._cls = owner
        else:
            # 使用实例传入
            self._cls = instance
        return self

    def __call__(self, *args, **kws):
        # print (self._method.__name__)
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


class ThreadEx(threading.Thread):
    '''可以捕获异常的线程类
    '''

    def run(self):
        '''重载run方法
        '''
        import platform
        if platform.system() == "Windows":
            try:
                import pythoncom
            except ImportError:
                pass
            else:
                pythoncom.CoInitialize()
        try:
            return threading.Thread.run(self)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            # sys.excepthook(*sys.exc_info())
            logger.exception('thread %s exit' % self.getName())


class Singleton(object):
    '''单例基类
    '''
    instance = None

    def __new__(cls, *args, **kwargs):
        if not cls.instance:
            cls.instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
        return cls.instance


def get_root_path():
    '''获取根目录，支持py2exe打包后
    '''
    if hasattr(sys, "frozen"):
        # py2exe打包的
        python_path = unicode(sys.executable, sys.getfilesystemencoding()) if six.PY2 else sys.executable
        return os.path.join(os.path.dirname(python_path), 'library.zip')
    file_path = unicode(eval('__file__'), sys.getfilesystemencoding()) if six.PY2 else eval('__file__')
    return os.path.dirname(file_path)


def is_mutibyte_string(data):
    '''判断是否是多字节字符串
    '''
    if six.PY2 and (not isinstance(data, unicode)):
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
    if six.PY2 and (not isinstance(s, unicode)):
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
    left = max(rect1[0], rect2[0])
    right = min(rect1[0] + rect1[2], rect2[0] + rect2[2])
    top = max(rect1[1], rect2[1])
    bottom = min(rect1[1] + rect1[3], rect2[1] + rect2[3])
    return (left, top, right - left, bottom - top)


def get_process_name_hash(process_name, device_id):
    '''根据进程名和设备id计算端口值
            结果范围：[5100, 5200)
    TODO: hash冲突的解决
    '''
    result = 0
    start_port = 15000
    port_range = 1000
    text = device_id + process_name
    for i in range(len(text)):
        c = text[i]
        asc = ord(c)
        result = 31 * result + asc

    if result > port_range:
        result %= port_range
    return result + start_port


def version_cmp(ver1, ver2):
    '''版本比较
    '''
    if ver1 == ver2: return 0
    ver1 = ver1.split('.')
    ver2 = ver2.split('.')
    i = 0
    while True:
        if i >= len(ver1) and i >= len(ver2): return 0
        if i >= len(ver1) and i < len(ver2): return -1
        if i >= len(ver2) and i < len(ver1): return 1
        if ver1[i].isdigit() and ver2[i].isdigit():
            c1 = int(ver1[i])
            c2 = int(ver2[i])
            if c1 > c2: return 1
            elif c1 < c2: return -1
        elif ver1[i].isdigit():
            return 1
        elif ver2[i].isdigit():
            return -1
        else:
            return 0
        i += 1


def list_zipfile_dir(zipfile_path, dir_path):
    '''获取zip文件中指定目录的子目录和文件列表
    '''
    import zipfile
    with zipfile.ZipFile(zipfile_path, "r") as z:
        result = []
        for it in z.namelist():
            if it.startswith('%s/' % dir_path):
                result.append(it[len(dir_path) + 1:])
        return result


def extract_from_zipfile(zipfile_path, relative_path, save_path):
    '''从zip文件中提取文件
    '''
    logger.info('extract_from_zipfile %s %s' % (relative_path, save_path))
    import zipfile
    with zipfile.ZipFile(zipfile_path, "r") as z:
        try:
            z.getinfo(relative_path)
        except KeyError:
            for it in list_zipfile_dir(zipfile_path, relative_path):
                extract_from_zipfile(zipfile_path, relative_path + '/' + it, os.path.join(save_path, it))
        else:
            content = z.read(relative_path)
            save_dir = os.path.dirname(save_path)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            with open(save_path, 'wb') as f:
                f.write(content)


def time_clock():
    '''
    '''
    if sys.platform == 'win32':
        try:  # Python 3.4+
            return time.perf_counter()
        except AttributeError:  # Earlier than Python 3.
            return time.clock()
    else:
        return time.time()
    
def is_int(num):
    '''判断整数num是否可以用32位表示
    '''
    return (num <= 2147483647 and num >= -2147483648)

def general_encode(s):
    '''字符串通用编码处理
    python2 => utf8
    python3 => unicode
    '''
    if six.PY2 and isinstance(s, (unicode,)):
        s = s.encode('utf8')
    elif six.PY3 and isinstance(s, (bytes,)):
        s = s.decode('utf8')
    return s

def utf8_encode(s):
    '''将字符串转换为utf8编码
    '''
    if not isinstance(s, bytes):
        s = s.encode('utf8')
    return s
    
def encode_wrap(func):
    '''处理函数参数编码
    '''
    def wrap_func(*args, **kwargs):
        args = list(args)
        for i, it in enumerate(args):
            args[i] = general_encode(it)
        for key in kwargs:
            kwargs[key] = general_encode(kwargs[key])
        return func(*args, **kwargs)
    return wrap_func

def enforce_utf8_decode(s):
    '''强制utf8解码，对于不合法的字符串，使用\x12的形式
    '''
    if not isinstance(s, bytes):
        return s
    try:
        return s.decode('utf8')
    except UnicodeDecodeError as e:
        start = e.args[2]
        end = e.args[3]
        return enforce_utf8_decode(s[:start]) + repr(s[start: end])[1:-1] + enforce_utf8_decode(s[end:])


if __name__ == '__main__':
    pass
