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

'''QPath中间层
'''

# 2015/6/30 apple 创建

class QPath(object):
    '''QPath
    '''
    def __init__(self, qpath_str):
        self._qpath_str = qpath_str
    
    def __str__(self):
        return self._qpath_str
    
    @property
    def _parsed_qpath(self):
        '''解析后的内容
        暂时为兼容旧的QPath而存在
        '''
        import re
        patttern = re.compile(r'''Instance\s*=\s*('|")\d+('|")''')
        if patttern.search(self._qpath_str):
            from tuia.qpath import QPath
            return QPath(self._qpath_str)._parsed_qpath
        else:
            from tuia.qpathparser import QPathParser
            return QPathParser().parse(self._qpath_str)[0]
        
if __name__ == '__main__':
    print QPath('/Id="xxx" /Instance="2"')._parsed_qpath
    