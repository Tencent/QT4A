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

'''操作AndroidManifest.xml文件
'''


from qt4a.apktool.__init__ import APKError
from qt4a.apktool.axml import AXMLFile
from qt4a.apktool.apkfile import APKFile


class AndroidManifest(object):
    '''
    '''
    def __init__(self, apk_fp_or_path):
        if isinstance(apk_fp_or_path, APKFile):
            self._apk_file = apk_fp_or_path
        else:
            self._apk_file = APKFile(apk_fp_or_path)
        self._dom = self.get_dom()
        
    def get_dom(self):
        '''获取AndroidManifest.xml文件的dom树
        '''
        fp = self._apk_file.get_file('AndroidManifest.xml')
        if fp == None: raise RuntimeError('apk %s is invalid' % self._apk_path)
        axf = AXMLFile(fp)
        return axf.to_xml()
    
    @property
    def package_name(self):
        '''包名
        '''
        return self._dom.getElementsByTagName('manifest')[0].getAttribute('package')
    
    @property
    def version_code(self):
        '''versionCode
        '''
        return int(self._dom.getElementsByTagName('manifest')[0].getAttribute('android:versionCode'))
    
    @property
    def version_name(self):
        '''versionName
        '''
        return self._dom.getElementsByTagName('manifest')[0].getAttribute('android:versionName')
    
    @property
    def min_sdk_version(self):
        '''最低SDK版本
        '''
        return int(self._dom.getElementsByTagName('uses-sdk')[0].getAttribute('android:minSdkVersion'))
    
    @min_sdk_version.setter
    def min_sdk_version(self, version):
        '''设置最低SDK版本
        '''
        self._dom.getElementsByTagName('uses-sdk')[0].setAttribute('android:minSdkVersion', str(version))

    @property
    def target_sdk_version(self):
        '''目标SDK版本
        '''
        return int(self._dom.getElementsByTagName('uses-sdk')[0].getAttribute('android:targetSdkVersion'))
    
    @target_sdk_version.setter
    def target_sdk_version(self, version):
        '''设置目标SDK版本
        '''
        self._dom.getElementsByTagName('uses-sdk')[0].setAttribute('android:targetSdkVersion', str(version))

    @property
    def application_name(self):
        '''
        '''
        return self._dom.getElementsByTagName('application')[0].getAttribute('android:name')
    
    @property
    def debuggable(self):
        '''是否是调试版本
        '''
        return self._dom.getElementsByTagName('application')[0].getAttribute('android:debuggable') == 'true'
    
    @debuggable.setter
    def debuggable(self, value):
        '''设置调试标志位
        '''
        self._dom.getElementsByTagName('application')[0].setAttribute('android:debuggable', 'true' if value else 'false')
    
    @property
    def vm_safe_mode(self):
        '''虚拟机安全模式
        '''
        return self._dom.getElementsByTagName('application')[0].getAttribute('android:vmSafeMode') == 'true'

    @vm_safe_mode.setter
    def vm_safe_mode(self, mode):
        '''设置虚拟机安全模式
        '''
        self._dom.getElementsByTagName('application')[0].setAttribute('android:vmSafeMode', 'true' if mode else 'false')

    @property
    def start_activity(self):
        '''启动Activity
        '''
        for activity in self._dom.getElementsByTagName('activity'):
            for filter in activity.getElementsByTagName('action'):
                if filter.getAttribute('android:name') == 'android.intent.action.MAIN':
                    activity_name = activity.getAttribute('android:name')
                    if activity_name.startswith('.'):
                        activity_name = self.package_name + activity_name
                    return activity_name
        raise APKError('apk %s do not have start activity' % self._apk_path)
    
    def get_process_list(self):
        '''获取进程列表
        '''
        process_list = []
        for tag_name in ('activity', 'service', 'provider', 'receiver'):
            for it in self._dom.getElementsByTagName(tag_name):
                process = it.getAttribute('android:process')
                if process and not process in process_list: 
                    process_list.append(process)
        return process_list
    
    def add_provider(self, name, authorities, process=None):
        '''添加ContentProvider
        '''
        elem = self._dom.createElement('provider')
        elem.setAttribute('android:name', name)
        elem.setAttribute('android:authorities', authorities)
        if process: elem.setAttribute('android:process', process)
        self._dom.getElementsByTagName('application')[0].appendChild(elem)
    
    def add_activity(self, activity, exported=True, process=None):
        elem = self._dom.createElement('activity')
        elem.setAttribute('android:name', activity)
        elem.setAttribute('android:exported', 'true' if exported else 'false')
        if process: 
            if not process.startswith(':'): process = ':' + process
            elem.setAttribute('android:process', process)
        self._dom.getElementsByTagName('application')[0].appendChild(elem)
        
    def save(self):
        '''保存修改到apk文件
        '''
        axml = AXMLFile.from_xml(self._dom)
        self._apk_file.add_file('AndroidManifest.xml', axml.serialize())
        
if __name__ == '__main__':
    pass
