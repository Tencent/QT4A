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

import argparse
import time
import sys
    
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

def repack_apk(args):
    from apktool.repack import repack_apk
    print('Repacking apk %s...' % (' '.join(args.path)))
    outpath = repack_apk(args.path, args.debuggable)
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
    args.func(args)
        
        
if __name__ == '__main__':
    qt4a_manage_main()
    
    
    

