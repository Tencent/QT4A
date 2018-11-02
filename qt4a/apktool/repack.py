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

'''重打包
'''


import json
import logging
import os, sys
import subprocess
import tempfile
from apkfile import APKFile
from manifest import AndroidManifest

def get_apk_signature(rsa_file_path):
    '''获取应用签名
    '''
    if not os.path.exists(rsa_file_path):
        raise RuntimeError('Rsa file %s not exist' % rsa_file_path)
    cur_path = os.path.dirname(os.path.abspath(__file__))
    jar_path = os.path.join(cur_path, 'tools', 'apkhelper.jar')
    return os.popen('java -jar %s getSignature %s' % (jar_path, rsa_file_path)).read()

def dex2jar(dex_path, jar_path):
    '''将dex转换为jar
    '''
    if not os.path.exists(dex_path):
        raise RuntimeError('dex %s not exist' % dex_path)
    cur_path = os.path.dirname(os.path.abspath(__file__))
    tools_path = os.path.join(cur_path, 'tools')
    class_paths = []
    for it in os.listdir(tools_path):
        if it.endswith('.jar'):
            class_paths.append(os.path.join(tools_path, it))
    # -Xms512m -Xmx1024m
    sep = ';' if sys.platform == 'win32' else ':'
    cmdline = ['java', '-Xmx1024m', '-cp', sep.join(class_paths), 'com.googlecode.dex2jar.tools.Dex2jarCmd',
               '-f', '-o', jar_path, dex_path]
    logging.info(' '.join(cmdline))
    proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = proc.communicate()[1]
    if not '->' in result:
        raise RuntimeError('convert dex %s to jar failed: %s' % (dex_path, result))

def jar2dex(jar_path, dex_path):
    '''jar转换为dex
    '''
    if not os.path.exists(jar_path):
        raise RuntimeError('jar %s not exist' % jar_path)
    cur_path = os.path.dirname(os.path.abspath(__file__))
    dx_path = os.path.join(cur_path, 'tools', 'dx.jar')
    # cmdline = 'java -Xmx1024m -cp "%s" com.android.dx.command.Main --dex --force-jumbo --output="%s" "%s"' % (dx_path, dex_path, jar_path)
    memory = 1024
    if os.path.getsize(jar_path) > 10000 * 1014: memory = 2048  # 此时必须用64位java
    cmdline = ['java', '-Xmx%dm' % memory, '-cp', dx_path, 'com.android.dx.command.Main',
               '--dex', '--force-jumbo', '--output=%s' % dex_path, jar_path]
    logging.info(' '.join(cmdline))
    proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = proc.communicate()[1]
    if result:
        err_msg = result
        if sys.platform == 'win32': err_msg = err_msg.decode('gbk')
        raise RuntimeError('convert jar %s to dex failed: %s' % (jar_path, err_msg))
    
def rebuild_dex_with_jumbo(dex_path):
    '''使用jumbo模式重新编译dex
    '''
    jar_path = tempfile.mktemp('.jar')
    dex2jar(dex_path, jar_path)
    jar2dex(jar_path, dex_path)
    os.remove(jar_path)
    
def merge_dex(dst_dex, src_dexs):
    '''合并dex
    '''
    cur_path = os.path.dirname(os.path.abspath(__file__))
    jar_path = os.path.join(cur_path, 'tools', 'apkhelper.jar')
    cmdline = ['java', '-jar', jar_path, 'mergeDex', dst_dex]
    cmdline.extend(src_dexs)
    logging.info(' '.join(cmdline))
    proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = proc.communicate()
    if not 'Took' in result[0]:
        if 'non-jumbo instruction' in result[1]:
            # 应用未使用jumbo模式编译，这里做一次转换
            logging.warn('change dex to jumbo mode')
            rebuild_dex_with_jumbo(src_dexs[0])
            return merge_dex(dst_dex, src_dexs)
        raise RuntimeError('merge dex failed: %s' % result[1])
    
def resign_apk(apk_path):
    '''重签名应用
    '''
    if not os.path.exists(apk_path):
        raise RuntimeError('apk %s not exist' % apk_path)
    cur_path = os.path.dirname(os.path.abspath(__file__))
    key_file_path = os.path.join(cur_path, 'tools', 'qt4a.keystore')
    save_path = apk_path[:-4] + '-signed.apk'
    # 'jarsigner -digestalg SHA1 -sigalg MD5withRSA -keystore %s -signedjar %s %s qt4a' % (key_file_path, save_path, apk_path)
    cmdline = ['jarsigner', '-digestalg', 'SHA1', '-sigalg', 'MD5withRSA', '-keystore',
               key_file_path, '-signedjar', save_path, apk_path, 'qt4a']
    logging.info(' '.join(cmdline))
    proc = subprocess.Popen(cmdline, stdin=subprocess.PIPE)
    out, err = proc.communicate('test@123')
    if out: logging.info('jarsigner: ' + out)
    if err: logging.warn('jarsigner: ' + err)
    return save_path

def repack_apk(apk_path_or_list, debuggable=True):
    '''重打包apk
    
    :param apk_path_or_list: apk路径或apk路径列表
    :type  apk_path_or_list: string/list
    :param debuggable: 重打包后的apk是否是调试版本：
                           True - 是
                           False - 否
                           None - 与原apk保持一致
    :type debuggable:  bool/None
    '''
    cur_path = os.path.dirname(os.path.abspath(__file__))
    if not isinstance(apk_path_or_list, list):
        apk_path_or_list = [apk_path_or_list]
    elif len(apk_path_or_list) == 0:
        raise ValueError('apk path not specified')
    
    apk_file_list = []
    signature_dict = {}
    for it in apk_path_or_list:
        apk_file = APKFile(it)
        apk_file_list.append(apk_file)
        manifest = AndroidManifest(apk_file)
        if debuggable != None: manifest.debuggable = debuggable  # 修改debuggable属性
        process_list = manifest.get_process_list()
        provider_name = 'com.test.androidspy.inject.DexLoaderContentProvider'
        authorities = manifest.package_name + '.authorities'
        manifest.add_provider(provider_name, authorities)  # 主进程
        manifest.add_activity('com.test.androidspy.inject.CmdExecuteActivity', "true", ':qt4a_cmd')
        for i, process in enumerate(process_list):
            manifest.add_provider(provider_name + '$InnerClass' + str(i + 1), authorities + str(i), process)
        manifest.save()
            
        # 合并dex文件
        dexloader_path = os.path.join(cur_path, 'tools', 'dexloader.dex')
        classes_dex_path = tempfile.mktemp('.dex')
        apk_file.extract_file('classes.dex', classes_dex_path)  
        merge_dex(classes_dex_path, [classes_dex_path, dexloader_path])
        with open(classes_dex_path, 'rb') as f:
            apk_file.add_file('classes.dex', f.read())
        
        # 添加QT4A测试桩文件
        file_list = ['AndroidSpy.jar',
                     'arm64-v8a/libdexloader.so',
                     'arm64-v8a/libdexloader64.so',
                     'arm64-v8a/libandroidhook.so',
                     'armeabi/libdexloader.so',
                     'armeabi/libandroidhook.so',
                     'armeabi-v7a/libdexloader.so',
                     'armeabi-v7a/libandroidhook.so',
                     'x86/libdexloader.so',
                     'x86/libandroidhook.so'
                     ]
        tools_path = os.path.join(os.path.dirname(cur_path), 'androiddriver', 'tools')
        for it in file_list:
            file_path = os.path.join(tools_path, it)
            with open(file_path, 'rb') as f:
                data = f.read()
                apk_file.add_file('assets/qt4a/%s' % it, data)
            
        for it in apk_file.list_dir('META-INF'):
            if it.lower().endswith('.rsa'):
                print('Signature file is %s' % it)
                tmp_rsa_path = tempfile.mktemp('.rsa')
                apk_file.extract_file('META-INF/%s' % it, tmp_rsa_path)            
                orig_signature = get_apk_signature(tmp_rsa_path).strip()
                os.remove(tmp_rsa_path)
                logging.info('%s signature is %s' % (manifest.package_name, orig_signature))
                signature_dict[manifest.package_name] = orig_signature
                break
        else:
            raise RuntimeError('Can not find .sf file in META-INF dir')
    
        for it in apk_file.list_dir('META-INF'):
            apk_file.delete_file('META-INF/%s' % it)
    
    out_apk_list = []
    
    # 写入原始签名信息
    temp_dir = tempfile.mkdtemp('-repack')
    for i, apk_file in enumerate(apk_file_list):  
        apk_file.add_file('assets/qt4a_package_signatures.txt', json.dumps(signature_dict))
        file_name = os.path.split(apk_path_or_list[i])[-1][:-4] + '-repack.apk'
        tmp_apk_path = os.path.join(temp_dir, file_name)
        apk_file.save(tmp_apk_path)
        new_path = resign_apk(tmp_apk_path)
        os.remove(tmp_apk_path)
        out_apk_list.append(new_path)
    if len(out_apk_list) == 1: return out_apk_list[0]
    else: return out_apk_list
    
if __name__ == '__main__': 
    pass
