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

import six
import json
import logging
import os
import shutil
import sys
import subprocess
import tempfile
from qt4a.apktool.apkfile import APKFile
from qt4a.apktool.manifest import AndroidManifest


class MergeDexError(RuntimeError):
    '''合并dex失败错误
    '''
    pass


class TooManyMethodsError(MergeDexError):
    '''方法数超标
    '''
    pass


class OutOfMemoryError(RuntimeError):
    '''内存超标
    '''
    pass


def general_decode(s):
    if not isinstance(s, bytes):
        return s
    try:
        return s.decode('utf8')
    except:
        return s.decode('gbk')


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
    proc = subprocess.Popen(
        cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = proc.communicate()[1]
    if not b'->' in result:
        raise RuntimeError('convert dex %s to jar failed: %s' %
                           (dex_path, result))


def jar2dex(jar_path, dex_path, max_heap_size=0):
    '''jar转换为dex
    '''
    if not os.path.exists(jar_path):
        raise RuntimeError('jar %s not exist' % jar_path)
    cur_path = os.path.dirname(os.path.abspath(__file__))
    dx_path = os.path.join(cur_path, 'tools', 'dx.jar')
    # cmdline = 'java -Xmx1024m -cp "%s" com.android.dx.command.Main --dex --force-jumbo --output="%s" "%s"' % (dx_path, dex_path, jar_path)
    memory = 1024
    if max_heap_size:
        memory = max_heap_size
    elif os.path.getsize(jar_path) >= 8 * 1024 * 1024:
        memory = 2048  # 此时必须用64位java
    cmdline = ['java', '-Xmx%dm' % memory, '-cp', dx_path, 'com.android.dx.command.Main',
               '--dex', '--force-jumbo', '--output=%s' % dex_path, jar_path]
    logging.info(' '.join(cmdline))

    proc = subprocess.Popen(
        cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = proc.communicate()[1]
    if result:
        err_msg = result
        if sys.platform == 'win32':
            err_msg = err_msg.decode('gbk')
        else:
            err_msg = err_msg.decode('utf8')
        if proc.returncode:
            if 'java.lang.OutOfMemoryError' in err_msg:
                raise OutOfMemoryError(err_msg)
            else:
                raise RuntimeError(
                    'Convert jar %s to dex failed: %s' % (jar_path, err_msg))
        else:
            logging.warning(err_msg)


def rebuild_dex_with_jumbo(dex_path, max_heap_size=0):
    '''使用jumbo模式重新编译dex
    '''
    jar_path = tempfile.mktemp('.jar')
    dex2jar(dex_path, jar_path)
    jar2dex(jar_path, dex_path, max_heap_size)
    os.remove(jar_path)


def merge_dex(dst_dex, src_dexs, max_heap_size=0):
    '''合并dex
    '''
    cur_path = os.path.dirname(os.path.abspath(__file__))
    jar_path = os.path.join(cur_path, 'tools', 'apkhelper.jar')
    cmdline = ['java', '-jar', jar_path, 'mergeDex', dst_dex]
    cmdline.extend(src_dexs)
    logging.info(' '.join(cmdline))
    proc = subprocess.Popen(
        cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = proc.communicate()
    if not b'Took' in result[0]:
        if b'non-jumbo instruction' in result[1]:
            # 应用未使用jumbo模式编译，这里做一次转换
            logging.warn('change dex to jumbo mode')
            rebuild_dex_with_jumbo(src_dexs[0], max_heap_size)
            return merge_dex(dst_dex, src_dexs, max_heap_size)
        elif b'DexIndexOverflowException' in result[1]:
            raise TooManyMethodsError('Merge dex failed: %s' % result[1])
        else:
            raise MergeDexError('Merge dex failed: %s' % result[1])


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
    proc = subprocess.Popen(cmdline, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate(b'test@123')
    if out:
        logging.info('jarsigner: ' + general_decode(out))
    if err:
        logging.warn('jarsigner: ' + general_decode(err))
    return save_path


def repack_apk(apk_path_or_list, provider_name, merge_dex_path, activity_list=None, res_file_list=None, debuggable=None, vm_safe_mode=None, max_heap_size=0, force_append=False):
    '''
    '''
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
        if debuggable != None:
            manifest.debuggable = debuggable  # 修改debuggable属性
        if vm_safe_mode != None:
            manifest.vm_safe_mode = vm_safe_mode  # 修改安全模式
        process_list = manifest.get_process_list()
        authorities = manifest.package_name + '.authorities'
        print('Add provider %s' % provider_name)
        manifest.add_provider(provider_name, authorities)  # 主进程
        for i, process in enumerate(process_list):
            sub_provider_name = provider_name + '$InnerClass' + str(i + 1)
            print('Add provider %s in process %s' %
                  (sub_provider_name, process))
            manifest.add_provider(
                sub_provider_name, authorities + str(i), process)

        if activity_list:
            for activity in activity_list:
                print('Add activity %s' % activity['name'])
                manifest.add_activity(
                    activity['name'], activity['exported'], activity['process'])

        # 合并dex文件
        print('Merge dex %s' % merge_dex_path)
        classes_dex_path = tempfile.mktemp('.dex')

        dex_index = 1
        low_memory = False
        while True:
            dex_file = 'classes%s.dex' % (dex_index if dex_index > 1 else '')
            if not apk_file.get_file(dex_file):
                # 作为最后一个classes.dex
                with open(merge_dex_path, 'rb') as f:
                    apk_file.add_file(dex_file, f.read())
                print('Save dex %s to %s' % (merge_dex_path, dex_file))
                break

            if force_append or low_memory:
                # 低内存下直接跳过已有dex，进行加速
                dex_index += 1
                continue

            if os.path.exists(classes_dex_path):
                os.remove(classes_dex_path)
            apk_file.extract_file(dex_file, classes_dex_path)
            try:
                merge_dex(classes_dex_path, [
                          classes_dex_path, merge_dex_path], max_heap_size)
            except TooManyMethodsError:
                print('Merge dex into %s failed due to methods number' % dex_file)
                dex_index += 1
            except OutOfMemoryError:
                print('Merge dex into %s failed due to out of memory error' % dex_file)
                low_memory = True
                dex_index += 1
            else:
                print('Merge dex into %s success' % dex_file)
                with open(classes_dex_path, 'rb') as f:
                    apk_file.add_file(dex_file, f.read())
                break

        if dex_index > 1:
            # 合并进非主dex只支持5.0以上系统
            print('WARNING: APK can only be installed in android above 5.0')
            manifest.min_sdk_version = 21

        manifest.save()

        if res_file_list:
            for src_path, dst_path in res_file_list:
                with open(src_path, 'rb') as f:
                    print('Copy file %s => %s' % (src_path, dst_path))
                    data = f.read()
                    apk_file.add_file(dst_path, data)

        for it in apk_file.list_dir('META-INF'):
            if it.lower().endswith('.rsa'):
                print('Signature file is %s' % it)
                tmp_rsa_path = tempfile.mktemp('.rsa')
                apk_file.extract_file('META-INF/%s' % it, tmp_rsa_path)
                orig_signature = get_apk_signature(tmp_rsa_path).strip()
                os.remove(tmp_rsa_path)
                logging.info('%s signature is %s' %
                             (manifest.package_name, orig_signature))
                signature_dict[manifest.package_name] = orig_signature
                break
        else:
            raise RuntimeError('Can not find .sf file in META-INF dir')

        for it in apk_file.list_dir('META-INF'):
            apk_file.delete_file('META-INF/%s' % it)

    out_apk_list = []

    # 写入原始签名信息
    print('Write original signatures: %s' % json.dumps(signature_dict))
    temp_dir = tempfile.mkdtemp('-repack')
    for i, apk_file in enumerate(apk_file_list):
        apk_file.add_file('assets/qt4a_package_signatures.txt',
                          json.dumps(signature_dict))
        file_name = os.path.split(apk_path_or_list[i])[-1][:-4] + '-repack.apk'
        tmp_apk_path = os.path.join(temp_dir, file_name)
        apk_file.save(tmp_apk_path)
        new_path = resign_apk(tmp_apk_path)
        os.remove(tmp_apk_path)
        out_apk_list.append(new_path)
    if len(out_apk_list) == 1:
        return out_apk_list[0]
    else:
        return out_apk_list


if __name__ == '__main__':
    pass
