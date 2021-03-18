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
测试任务相关的接口
'''

from qt4a.device import Device, DeviceProviderManager
from qt4a.androiddriver.androiddriver import copy_android_driver
from qt4a.androiddriver.util import logger, TimeoutError
from qt4a.androiddriver.adb import ADB
from qt4a.management import qt4a_repack_apk

import six
import json
import logging
import traceback
import tempfile
try:
    import urllib2
except:
    import urllib.request as urllib2
import os, sys
import time
import shutil
import zipfile
import zlib           

def drun5_env_setup(report, product_path):
    if sys.platform == 'linux2':
        # 临时使用这种方法清理tmp目录
        os.system('rm -r /tmp/*')
        
def func_retry_wrap(func):
    def _wrap_func(*args, **kwargs):
        '''
        '''
        for _ in range(10):
            try:
                return func(*args, **kwargs)
            except:
                logger.exception('run %s error' % func.__name__)
                time.sleep(10)
        else:
            raise
    return _wrap_func

def _download_http_file(url, target_path):
    '''下载http文件 
    :param url: HTTP路径
    :type url: string
    :param target_path: 下载到目标路径
    :type target_path: string
    '''
    request = urllib2.Request(url)
    for _ in range(3):
        try:
            response = urllib2.urlopen(request)
            if target_path is None:
                file_name =  response.info()['Content-Disposition'].split('filename=')[1]
                file_name = file_name.replace('"', '').replace("'", "")
                target_path = os.path.join(tempfile.mkdtemp(), file_name)
            break
        except urllib2.HTTPError:
            raise
        except:
            logger.exception('http request failed')
    else:
        raise

    result = response.read()
    if response.headers.get('Content-Encoding') == 'gzip':
        result = zlib.decompress(result, 16 + zlib.MAX_WBITS)

    with open(target_path, 'wb') as fp:
        fp.write(result)
    return target_path
        
def _get_valid_file_name(file_name):
    '''过滤掉文件名中的非法字符
    '''
    for c in (':', '?', '%', '$', '{', '}'):
        file_name = file_name.replace(c, '_')
    return file_name     

def _download_package(url):
    '''下载安装包到本地
    :param url: NFS或HTTP资源路径
    :type url: string
    :returns string - 本地路径
    '''
    if six.PY2 and not isinstance(url, unicode):
        url = url.decode('utf8')
    if url.startswith('http'):
        logger.info("package path is http")
        pos = url.rfind('/')
        pos_question = url.rfind('?')
        if pos_question > pos:
            tmp_url = url[:pos_question]
            while pos > 0:
                curr_name = tmp_url[pos:]
                if '.' in curr_name:
                    file_name = _get_valid_file_name(tmp_url[pos+1:])
                    break
                tmp_url = tmp_url[:pos]
                pos = tmp_url.rfind('/')
            else:
                raise RuntimeError('无法识别出需要下载的文件名%s' % url)
        else:
            file_name = _get_valid_file_name(url[pos + 1:])
        if not ('.apk' in file_name or '.txt' in file_name or '.java' in file_name):
            tmp_path = None
        else:
            tmp_path = os.path.join(tempfile.mkdtemp(), file_name)
        logger.info('download path: %s' % tmp_path)
        target_path =  _download_http_file(url, tmp_path)
        return target_path
    elif url.startswith('\\\\'):
        logger.info("package path is tfs")
        # TFS
        pos = url.rfind('\\')
        file_name = _get_valid_file_name(url[pos + 1:])
        tmp_path = os.path.join(tempfile.mkdtemp(), file_name)
        for _ in range(10):
            try:
                shutil.copyfile(url, tmp_path)
                if os.path.exists(tmp_path):
                    break
            except:
                logger.exception('copy file error')
                time.sleep(10)
        else:
            raise
        return tmp_path
    else:
        logger.info("package path not http or tfs")
        return url
        
def _handle_mapping_file(file_path):
    '''只保留R$id部分
    '''
    f = open(file_path, 'r')
    text = f.read()
    f.close()
    is_write = False
    file_name = os.path.split(file_path)[-1]
    tmp_path = os.path.join(tempfile.mkdtemp(), file_name)
    f = open(tmp_path, 'w')
    for line in text.split('\n'):
        if is_write and not line.startswith('    '):
            # 结束
            is_write = False
        if '.R$id' in line or '.R$drawable' in line: 
            is_write = True
        if is_write: 
            print (line)
            f.write(line + '\n')
    f.close()
    return tmp_path
    
def _extract_version(apk_path):
    '''获取版本号
    '''
    # 按照安装包名格式解析版本号
    # 例如 qq_4.6.2.2125_android_r80950_YingYongBao_537037597_release.apk
    # 则版本号为4.6.2.2125_r80950
    try:
        import re
        filename = os.path.basename(apk_path)
        ret = re.search(r'qq_([\.|\d]+)_\w*(r\d+)_', filename)
        if ret == None: 
            return 'unknown'
        return '%s_%s' % (ret.group(1), ret.group(2))
    except:
        logging.error('extract version failed:\n' + traceback.format_exc())
        return 'unknown'
           
def extract_package_param(package_param, repack_apk=False):
    '''解析安装包参数
    :param package_param: 安装包参数
    :type package_param: string
    :returns list, list - apk安装包列表，mapping文件列表
    '''
    packages = []
    mapping_files = []
    R_java_files = []
    for pkg_path in package_param.split(';'):
        pkg_path = pkg_path.strip()
        if pkg_path.endswith('.exe') or not pkg_path: continue
        pkg_path = _download_package(pkg_path)
        if pkg_path.endswith('.apk'):
            packages.append(pkg_path)
        elif pkg_path.endswith('.txt'):
            mapping_files.append(pkg_path)
        elif pkg_path.endswith('R.java'):
            R_java_files.append(pkg_path)
#         else:
#             raise RuntimeError('不支持的文件格式：%s' % pkg_path)
    
    repack = False
    try:
        from testbase.conf import settings
        if (hasattr(settings, 'QT4A_REPACK_PACKAGE') and settings.QT4A_REPACK_PACKAGE == True) or repack_apk:  # 有时不重打包会crash，如joox
            repack = True
    except ImportError:
        pass
    # if repack or not device.is_rooted():
    if repack and packages:
        debuggable = True
        if mapping_files:
            debuggable = False
        packages = qt4a_repack_apk(packages, debuggable)
        if not isinstance(packages, list): packages = [packages]
        logger.info(u'repack apk success, new package path: %s' % '|'.join(packages))
        
        
    return packages, mapping_files, R_java_files


def delete_local_file(file_path):
    '''如果是本地文件，则删除
    '''
    if file_path[1:3] == ':\\':
        logger.info('delete file: %s' % file_path)
        try:
            os.remove(file_path)
        except:
            logger.info('delete file error')
            pass

def install_package(device, package_path, mapping_file=None, R_java_file=None):
    '''安装到设备
    :param device: 设备
    :param package_path: 安装包
    :param mapping_file: mapping文件
    :type device: qt4a.Device
    :type package_path: string
    :type mapping_file: string
    '''
    package = _download_package(package_path)
    pkg_name = ADB._get_package_name(package)
    logger.info(u'install package: %s' % package)
    overwrite = False
    from testbase.conf import settings
    if hasattr(settings, 'QT4A_INSTALL_OVERWRITE') and settings.QT4A_INSTALL_OVERWRITE == True:  # 需要覆盖安装，而不是卸载安装
        overwrite = True
    device.install_package(package, pkg_name, overwrite)
    try:
        device.clear_data(pkg_name)
        set_permission(device, pkg_name)
    except:
        logger.exception('set permission failed')
        
    delete_local_file(package)
    if mapping_file:
        mapping_file = _download_package(mapping_file)
        new_path = mapping_file  # _handle_mapping_file(mapping_file)
        device.push_file(new_path, '/data/local/tmp/%s_map.txt' % pkg_name)
        delete_local_file(mapping_file)
    
    if R_java_file:
        R_java_file = _download_package(R_java_file)
        data = parse_R_java(R_java_file)
        data = json.dumps(data)
        with open(R_java_file, 'w') as f:
            f.write(data)
        device.push_file(R_java_file, '/data/local/tmp/%s_R_id.json' % pkg_name)
        delete_local_file(R_java_file)
    return pkg_name

def set_permission(device, package_name):
    '''设置权限
    '''
    brand = device.adb.get_property('ro.product.brand')
    if brand == 'Meizu' or device.adb.get_property('ro.meizu.setupwizard.flyme') == 'true':
        set_meizu_permission(device, package_name)
    
def set_meizu_permission(device, package_name):
    '''设置魅族手机的权限
    '''
    if device.sdk_version < 19: return
    if device.is_file_exists('/data/data/com.lbe.security.meizu'): return
    # 没有使用lbe
    perm_dict = {'PERM_ID_CONTACT': 4,
                 'PERM_ID_WRITE_CONTACT': 5,
                 'PERM_ID_DELETE_CONTACT': 63,
                 'PERM_ID_CALLLOG': 6,
                 'PERM_ID_WRITE_CALLLOG': 7,
                 'PERM_ID_DELETE_CALLLOG': 64,
                 'PERM_ID_SMSDB': 14,
                 'PERM_ID_WRITE_SMSDB': 15,
                 'PERM_ID_DELETE_SMSDB': 61,
                 'PERM_ID_MMSDB': 66,
                 'PERM_ID_WRITE_MMSDB': 60,
                 'PERM_ID_DELETE_MMSDB': 62,
                 'PERM_ID_AUDIO_RECORDER': 27,
                 'PERM_ID_LOCATION': 75,
                 'PERM_ID_VIDEO_RECORDER': 76,
                 'PERM_ID_PHONEINFO': 73,
                 'PERM_ID_SETTINGS': 23
                 }
    for it in perm_dict:
        try:
            device.run_shell_cmd('content insert --uri content://settings/secure --bind name:s:%s_op_%d --bind value:i:4' % (package_name, perm_dict[it]))
        except:
            logger.exception('set %s permission failed' % it)
            
def drun5_device_setup(report, device_info, product_path):
    '''设备初始化
    
    :param report: 测试报告接口
    :type report: OnlineReport
    :param device_info: 设备资源信息
    :type device_info: dict
    :param product_path: 安装包路径
    :type product_path: str
    '''
    logger.handlers[0].setLevel(logging.DEBUG)
    logger.info('start setup')
    android_pkg_paths, mapping_file_paths, R_java_paths = extract_package_param(product_path)
    if len(mapping_file_paths) > 0: 
        logger.info('mapping files: %s' % mapping_file_paths)
    
    # 提前信息上报，避免出错时看不到设备信息
    device_attrs = device_info["properties"]
    if report: 
        devinfo = device_attrs.copy()
        if len(android_pkg_paths) > 0: 
            devinfo['apk_version'] = _extract_version(android_pkg_paths[0])  # 第一个包必须为被测包
        else:
            devinfo['apk_version'] = 'unknown'
        devinfo['device'] = True
        report.info("Environment", "上报设备信息", devinfo)
        # report.info("debug", str(devinfo))
    
    device = DeviceProviderManager().connect_device(device_info)
    if not device: raise RuntimeError('Connect device %s failed' % device_info)
        
    if 'Android SDK' in device_attrs.get('dev_name') and device_attrs.get('dev_mb_support_opengl') == 'True':
        # 开启OpenGL的模拟器需要重启
        logger.info('reboot cloudroid device')
        device.reboot()
    elif 'Android SDK' in device_attrs.get('dev_name') or 'Android AOSP' in device_attrs.get('dev_name'):
        # 3天重启一次
        try:
            boot_time = device._device.get_system_boot_time()
            if boot_time >= 3 * 24 * 3600:
                logger.info('reboot cloudroid device')
                device.reboot()
        except:
            logger.exception('check cloudroid device boot time failed')
    elif 'generic Google Nexus 4' in device_attrs.get('dev_name'):
        # 30天重启一次
        try:
            boot_time = device._device.get_system_boot_time()
            if boot_time >= 30 * 24 * 3600:
                logger.info('reboot cloudroid device')
                device.reboot()
                time.sleep(80)
        except:
            logger.exception('check cloudroid device boot time failed')
    
    device_id = device.device_id
        
    logger.info('install android driver: %s' % device_id)
    copy_android_driver(device.adb)
    logger.info('install complete')
    
    # 暂时通过这种方法避免安装包的变化导致获取控件整型ID错误问题
    device.kill_process('com.test.androidspy:service')

    # 删除所有mapping文件
    device.delete_file('/data/local/tmp/*.java')
    device.delete_file('/data/local/tmp/*.json')
    device.delete_file('/data/local/tmp/*.txt')
    
    if device.sdk_version >= 21:
        # 避免模拟器中wifi出现感叹号
        try:
            device.run_shell_cmd('settings put global captive_portal_detection_enabled 0')
        except:
            logger.exception('set captive_portal_detection_enabled failed')
    if device.sdk_version >= 22:
        # 禁止弹出沉浸模式提示
        try:
            device.run_shell_cmd('settings put secure immersive_mode_confirmations confirmed')
        except:
            logger.exception('set immersive_mode_confirmations failed')
            
    try:
        device.set_screen_off_time(600)
    except:
        logger.exception('set screen off time failed')
    to_return = False
    if not android_pkg_paths:  # 没有安装包，不安装
        to_return = True        
    try:
        package_list = device.run_shell_cmd('pm list packages').strip().replace('\r', '').split('\n')
    except Exception as e:
        print ("pm list packages error:", e)
        package_list = []                     
    new_install_list = []
    for idx, package in enumerate(android_pkg_paths):
        # 用户需要保证传入的安装包顺序和mapping文件顺序一致
        if len(mapping_file_paths) > idx:
            mapping_file = mapping_file_paths[idx]
        else:
            mapping_file = None
        if len(R_java_paths) > idx:
            R_java_file = R_java_paths[idx]
        else:
            R_java_file = None         
        package_name = install_package(device, package, mapping_file, R_java_file)
        new_install_list.append(package_name)
    new_package_list = []
    if new_install_list:
        for package in package_list:
            if package.strip()[8:] not in new_install_list:
                new_package_list.append(package)
    else:
        new_package_list = package_list
    if new_package_list:
        new_packages = '\n'.join(new_package_list)
        file_name = os.path.join(tempfile.mkdtemp(), 'installed_packages.txt')
        print ("file_name=", file_name)
        with open(file_name, 'w') as fd:
            fd.write(new_packages)  
        device.push_file(file_name, '/data/local/tmp/installed_packages.txt')
    if to_return:return device
    try:
        # 将设备从已申请的设备列表中删除
        Device.device_list.pop()
    except Exception as e:
        traceback.print_exc()
    # if cloud_dev: cloud_dev.disconnect()#不能关闭
    return device

def drun5_device_cleanup(report, device_info):
    '''任务结束时的反初始化逻辑
    '''
    print ("drun5_device_cleanup begin")
    logger.info('drun5_device_cleanup')
    device_attrs = device_info["properties"]
    cloudroid_id = device_attrs.get('cloudroid_device_id')
    cloud_dev = None
    try:
        if cloudroid_id: 
            import cloudroid
            device_id = int(cloudroid_id)
            os.environ['CLOUDROID_APPID'] = 'qta'
            os.environ['CLOUDROID_TOKEN'] = '08d66a2383bcbda61fbde018d77317c8'
            cloud_dev = cloudroid.Device(device_id)
            device_id = cloud_dev.connect()
            Device.cloudroid_dev_list.append(cloud_dev)  # 便于后面释放
        else:
            device_id = '%s:%s' % (device_attrs['dev_mb_host'], device_attrs['dev_mb_serialno'])
        logger.info('device_id: %s' % device_id)
        device = Device(device_id)
        new_package_list = []
        try:
            new_package_list = device.run_shell_cmd('pm list packages').strip().replace('\r', '').split('\n')
        except TimeoutError as e:
            logger.error('pm list packages error:%s' % e)
        else:    
            to_uninstall_list = []
            old_package_list = device.run_shell_cmd('cat /data/local/tmp/installed_packages.txt').strip().replace('\r', '').split('\n')
            logger.info(old_package_list)
            if len(old_package_list) > 10:  # 防止/data/local/tmp目录没installed_packages.txt情况下误删app
                for package_name in new_package_list:
                    if package_name not in old_package_list and 'com.test.androidspy' not in package_name:
                        to_uninstall_list.append(package_name.strip()[8:])
                if len(to_uninstall_list) > 0 and len(to_uninstall_list) < 8:  # 防止用户重载drun5_setup没有调用基类，导致installed_packages.txt不是当前设备生成的
                    print ('uninstall list:%s' % to_uninstall_list)
                    for package_name in to_uninstall_list:
                        logger.info('uninstall package:%s' % package_name)
                        device.kill_process(package_name)
                        device.uninstall_package(package_name)
                else:
                    print ('len(to_uninstall_list)=', len(to_uninstall_list))
                for item in to_uninstall_list:
                    print ("uninstall package:", item)
            else:
                print ("len(old_package_list)=%d, old_package_list=%s" % (len(old_package_list), old_package_list))
    except:
        logger.exception('drun5_device_cleanup failed')
        
def drun5_get_product_info(product_path):
    '''获取被测产品信息
    '''
            
    info = {"version": "0.0",
            "build": "0.0",
            "protocol": "unknown"}
    
    pkgname = None
    for it in product_path.split(';'):
        if it.lower().endswith('.apk'):
            pkgname = os.path.basename(it)  # 第一个包必须为被测包
            break
            
    if pkgname:
        import re
        ret = re.search(r'.*_(\d+\.\d+\.\d+).(\d+)_\w*(r\d+)_', pkgname) 
        if ret:
            info = {"version": ret.group(1),
                    "build": ret.group(2),
                    "protocol": ret.group(3)}
    return info

def parse_R_java(R_java_path):
    '''解析R.java，返回dict对象
    '''
    import re
    pattern = re.compile(r'public static final int (\w+)=0x(\w+);')
    result = {}
    with open(R_java_path, 'r') as f:
        id_cls_start = False
        while True:
            line = f.readline()
            if not line: break
            if not id_cls_start and 'public static final class id {' in line:
                id_cls_start = True
            elif id_cls_start and '}' in line:
                break
            elif id_cls_start:
                ret = pattern.search(line)
                if not ret: continue
                result[ret.group(1)] = int(ret.group(2), 16)
    return result

def un_zip(zip_file, filename):  
    """unzip zip file"""  
    zip_file = zipfile.ZipFile(zip_file)  
    for names in zip_file.namelist():  
        zip_file.extract(names, filename)  
    zip_file.close()  
    
def set_java_path():
    '''搜索java路径并设置环境变量
    '''
    if sys.platform != 'win32':
        return
    for d in ('D', 'C'):
        for p in ('Program Files (x86)', 'Program Files'):
            root = os.path.join('%s:\\' % d, p)
            java_root = os.path.join(root, 'Java')
            if not os.path.exists(java_root): continue
            for it in os.listdir(java_root):
                path = os.path.join(java_root, it)
                if not os.path.isdir(path): continue
                if not it.startswith('jdk'): continue
                if os.path.exists(os.path.join(path, 'bin', 'jarsigner.exe')):
                    os.environ["PATH"] += (os.pathsep + os.path.join(path, 'bin'))
                    return os.path.join(path, 'bin')
                else:
                    shutil.rmtree(java_root, True)
                    break
    
    shutil.copy(u'\\\\tencent.com\\tfs\\跨部门项目\\SNG-Test\\QTA\\测试资源\\QT4A\\Java\\Java.zip', root)
    zip_path = os.path.join(root, 'Java.zip')
    try:
        un_zip(zip_path, java_root)
    except Exception as e:
        logger.info('un_zip exception: %s' % e)
    if not os.path.exists(os.path.join(java_root, 'jdk1.7.0_71', 'bin', 'jarsigner.exe')):
        raise RuntimeError('jarsigner.exe安装失败')
    os.remove(zip_path)
    logger.info('install jarsigner finished:%s' % (os.path.join(java_root, 'jdk1.7.0_71', 'bin')))
    os.environ["PATH"] += (os.pathsep + os.path.join(path, 'bin'))
    return os.path.join(java_root, 'jdk1.7.0_71', 'bin')

def wetest_move_files(package_path, mapping_file, R_java_file, save_pkg_to_proj=False):
    pkg_name = ADB._get_package_name(package_path)
    if mapping_file or R_java_file or save_pkg_to_proj:
        proj_root = os.path.realpath(os.path.dirname(__file__))
        proj_local_path = os.path.dirname(proj_root)
        file_path = os.path.join(proj_local_path, 'device_files.dir')
        if not os.path.exists(file_path):
            try:
                os.mkdir(file_path)
            except Exception as e:
                logger.info('创建文件夹device_files.dir失败:%s' % e)
        if not os.path.exists(file_path):
            raise RuntimeError('创建文件夹device_files.dir失败')   
        if mapping_file:
            shutil.copyfile(mapping_file, os.path.join(file_path, ('%s_map.txt' % pkg_name)))
            delete_local_file(mapping_file)
        if R_java_file:
            data = parse_R_java(R_java_file)
            data = json.dumps(data)
            with open(R_java_file, 'w') as f:
                f.write(data)
            shutil.copyfile(R_java_file, os.path.join(file_path, ('%s_R_id.json.txt' % pkg_name)))
            delete_local_file(R_java_file)
        if save_pkg_to_proj:
            shutil.copyfile(package_path, os.path.join(file_path, ('%s.apk' % pkg_name)))
            delete_local_file(package_path)
    print ("package_path to test=", package_path)
    if not save_pkg_to_proj:
        return package_path
    else:
        return None
    
def drun5_run_wetest(job_id, toptype, topnum, maxnum_percase, testcases, excluded_testcases='', notifier_emails='', product_path='', case_priority='', case_status='', fail_retry=0, device_condition=''):
    logger.handlers[0].setLevel(logging.DEBUG)
    logger.info("开始执行drun5_run_wetest")
    if device_condition:
        device_condition = device_condition.strip()
    
    begin = time.time() 
    if not job_id:
        raise RuntimeError('job_id不能为空，请检查')  
    if not (testcases and product_path and case_priority and case_status and fail_retry):
        raise RuntimeError('测试用例集、产品路径、测试用例优先级、测试用例状态、用例失败重跑次数均不能为空，请检查')
    topnum = int(topnum)
    if ';' in testcases or ',' in testcases or '|' in testcases or '/' in testcases:
        raise RuntimeError('测试用例集不能包含;,|/等符号，不同用例集用空格隔开即可')
    if  ';' in testcases or ',' in testcases or '|' in testcases or '/' in excluded_testcases:
        raise RuntimeError('排除测试用例集不能包含;,|/等符号，不同用例集用空格隔开即可')

    android_pkg_paths, mapping_file_paths, R_java_paths = extract_package_param(product_path, True)
    set_java_path()
    package_path = ''
    for idx, package in enumerate(android_pkg_paths):
        # 用户需要保证传入的安装包顺序和mapping文件顺序一致
        if len(mapping_file_paths) > idx:
            mapping_file = mapping_file_paths[idx]
        else:
            mapping_file = None
        if len(R_java_paths) > idx:
            R_java_file = R_java_paths[idx]
        else:
            R_java_file = None         
        rpackage = wetest_move_files(package, mapping_file, R_java_file, idx != 0)
        if rpackage: package_path = rpackage
    if not package_path: raise RuntimeError('error:package_path=%s' % package_path)
    from qt4a_wetest_lib.wetest import run_wetest
    run_wetest(package_path, job_id, toptype, topnum, maxnum_percase, testcases, excluded_testcases, notifier_emails, product_path, case_priority, case_status, fail_retry, device_condition)
    end = time.time()
    logger.info("begin=%s,end=%s,end-begin=%s" % (str(begin), str(end), str(end - begin)))
    
if __name__ == '__main__':
    url = r'http://fileserver.pipeline.ext.wsd.com/file/download?fileId=1726120&fileKey=e34d0c36-ff60-4754-8cb6-7e5dd784588f&rdm_app_id=QTA_test&rdm_app_key=510eafdd-3be1-4085-8b22-91ef55fb50e5'
    url = r'http://10.241.104.82/rdm/file/8200/39555/qq_8.1.8.1048_r7c3f6135_t2019-09-24_vdefault_CheckIn_537062368_cid0_debug.apk'
    target_path = None
    pkg_path = _download_http_file(url, target_path)
    print (pkg_path)
    exit()
    def memory_usage_psutil():
        # return the memory usage in MB
        import psutil, os
        process = psutil.Process(os.getpid())
        mem = process.memory_info()[0] / float(2 ** 20)
        return mem
    
    device_info = {'id': '15003',
 'last_used_time': '2018-11-02 09:32:58',
 'pool_id': '5bdbb9d616089326d57a8d0a',
 'pool_owner': 'job_57267294',
 'prop_count': 15,
 'properties': {'cloudroid_device_id1': '445',
                'dev_mb_has_camera': 'True',
                'dev_mb_has_microphone': 'True',
                'dev_mb_host': '127.0.0.1',
                'dev_mb_resolution': '800 x 1280',
                'dev_mb_serialno': '127.0.0.1:21289',
                'dev_name': 'generic_x86 Android SDK built for x86',
                'owner': 'shadowyang'},
 'res_group': 'Cloudroid_Emulator2',
 'res_type': 'android',
 'status': 'ok'}
    drun5_device_setup(None, device_info, u'http://10.241.104.82/rdm/file/3608/32966/qq_7.9.0.1254_r377089_t2018-11-01_vdefault_CheckIn_537059487_cid0_release.apk;')

#     file_name = r'E:\QT4A\QT4A2\wetest\wetest_gived\task.csv'
#     import csv
#     csvfile = file(file_name, 'wb')
#     writer = csv.writer(csvfile)
#     writer.writerow(['cpu_total', 'manu', 'usernum', 'cpu_ghz', 'num', 'mem_show', 'version', 'freenum', 'model', 'resolution', 'id', 'modelid'])
#     for item in rsp:
#         writer.writerow((item['cpu_total'], item['manu'].encode('utf-8'),item['usernum'],item['cpu_ghz'].encode('utf-8'),item['num'],item['mem_show'],item['version'].encode('utf-8'),item['freenum'],item['model'].encode('utf-8'),item['resolution'].encode('utf-8'),item['id'],item['modelid']))
#     csvfile.close()
#     exit()

    # dev = Device()
    # set_permission(dev, 'com.tencent.mobileqq')
#     print (memory_usage_psutil())
#     _download_http_file('http://10.241.104.82/rdm/file/3608/31292/qq_7.7.5.28554_r360839_t2018-07-27_vdefault_CheckIn_537057310_cid0_release.apk', '1.apk')
#     print (memory_usage_psutil())
    # _download_package('http://10.219.152.155/rdm/file/14600/3840/fortuneplat_dev_3.0.0.3000_r2153_20170407-10:00:10_debug.apk')
#     res = parse_R_java(r'C:\Users\shadowyang\Documents\RTXC File List\Accounts\shadowyang\RTXDownload\R.java')
#     with open('1.txt', 'w') as f:
#         f.write(json.dumps(res))

    # drun5_run_wetest(1853, 'Top机型', '1', '1', 'mqtest.bvt.login_logout', '', 'hqlian;shadowyang', r'http://10.241.104.82/rdm/file/53974/29/qq_7.6.5.29_r349776_t2018-05-25_vdefault_Hongbao_537055299_cid0_release.apk;http://10.241.104.82/rdm/file/53974/29/R.java;http://10.241.104.82/rdm/file/53974/29/db041389-5f26-4986-879c-90aea0314448.txt', 'High|Normal', 'Ready', '1')
