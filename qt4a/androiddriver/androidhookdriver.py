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

'''Android Hook Driver
'''

from androiddriver import AndroidDriver

class AndroidHookDriver(object):
    '''提供Android Framework的Hook接口
    '''
    hook_jar_path = '/data/local/tmp/qt4a/androidhook.jar'
    
    def __init__(self, driver):
        self._driver = driver
    
    def _send_command(self, subcmd, **kwds):
        return self._driver.call_external_method(self.hook_jar_path, 'com.test.androidhook.MainEntry', True, SubCmd=subcmd, **kwds)
        
    def set_location(self, latitude, longitude):
        '''设置Mock的位置信息
        '''
        ret = self._send_command('HookLocation')
        if ret.has_key('Error'): raise RuntimeError('Hook获取位置函数失败: %s' % ret['Error'])
        ret = self._send_command('SetLocation', Latitude=latitude, Longitude=longitude)
        if ret.has_key('Error'): raise RuntimeError('修改位置失败: %s' % ret['Error'])
        return ret['Result']
    
if __name__ == '__main__':
    pass
    
