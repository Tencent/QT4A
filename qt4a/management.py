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

'''管理命令
'''

from __future__ import print_function

import argparse
import os
import sys
import time

try:
    raw_input
except:
    raw_input = input
    
def install_qt4a_driver(args):
    from qt4a.androiddriver.adb import ADB
    from qt4a.androiddriver.androiddriver import copy_android_driver
    
    device_list = ADB.list_device()
    if len(device_list) == 0:
        raise RuntimeError('No Android device found')
    elif len(device_list) == 1:
        device_id = device_list[0]
    elif len(device_list) > 1:
        text = '\nCurrent Android device list:\n'
        for i, dev in enumerate(device_list):
            text += '%d. %s\n' % ((i + 1), dev)

        while True:
            print(text)
            result = raw_input('Please input the index of device to install driver:\n')
            if result.isdigit():
                if int(result) > len(device_list):
                    sys.stderr.write('\nIndex %s out of range\nValid index range: [1, %d]\n' % (result, len(device_list)))
                    time.sleep(0.1)
                    continue
                device_id = device_list[int(result) - 1]
            else:
                if not result in device_list:
                    sys.stderr.write('\nDevice id %r not exist\n' % result)
                    time.sleep(0.1)
                    continue
                device_id = result
            break
        
    print('Device "%s" will install driver...' % device_id)
    copy_android_driver(device_id, args.force)
    print('Install QT4A driver to %s completely.' % device_id)


def qt4a_repack_apk(apk_path_or_list, debuggable=True):
    '''重打包apk
    
    :param apk_path_or_list: apk路径或apk路径列表
    :type  apk_path_or_list: string/list
    :param debuggable: 重打包后的apk是否是调试版本：
                           True - 是
                           False - 否
                           None - 与原apk保持一致
    :type debuggable:  bool/None
    '''
    from qt4a.apktool import repack
    cur_path = os.path.dirname(os.path.abspath(__file__))
    activity_list = [{
        'name': 'com.test.androidspy.inject.CmdExecuteActivity',
        'exported': True,
        'process': 'qt4a_cmd'
    }]

    # 添加QT4A测试桩文件
    file_path_list = []
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
    tools_path = os.path.join(cur_path, 'androiddriver', 'tools')
    for it in file_list:
        file_path = os.path.join(tools_path, it)
        file_path_list.append((file_path, 'assets/qt4a/%s' % it))

    return repack.repack_apk(apk_path_or_list, 
        'com.test.androidspy.inject.DexLoaderContentProvider',
        os.path.join(cur_path, 'apktool', 'tools', 'dexloader.dex'),
        activity_list,
        file_path_list,
        debuggable
        )

def repack_apk(args):
    print('Repacking apk %s...' % (' '.join(args.path)))
    outpath = qt4a_repack_apk(args.path, args.debuggable)
    print('Repack apk completely.\nOutput apk path is: ')
    if isinstance(outpath, list):
        for it in outpath:
            print(it)
    else:
        print(outpath)
    
def qt4a_manage_main():
    from qt4a.androiddriver.util import OutStream
    sys.stdout = OutStream(sys.stdout)
    sys.stderr = OutStream(sys.stderr)
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='subcommand')
    install_driver_parser = subparsers.add_parser('install-driver', help='install qt4a driver')
    install_driver_parser.add_argument('-f', '--force', action='store_true', help='force install qt4a driver')
    install_driver_parser.set_defaults(func=install_qt4a_driver)
    
    repack_parser = subparsers.add_parser('repack-apk', help='repack apk file')
    repack_parser.add_argument('-p', '--path', nargs='*', required=True, help='path of apks to repack')
    repack_parser.add_argument('-d', '--debuggable', type=bool, default=True, help='whether apk debuggable after repack')
    repack_parser.set_defaults(func=repack_apk)
    
    args = parser.parse_args()

    if hasattr(args, 'func'): 
        args.func(args)
    else:
        parser.print_help()
        print('\n%s: error: too few arguments' % os.path.split(sys.argv[0])[-1], file=sys.stderr) # show error info in python3
        
        
if __name__ == '__main__':
    qt4a_manage_main()
    
    
    

