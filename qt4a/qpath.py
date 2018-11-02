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


from tuia.qpathparser import QPathParser
QPathParser.INT_TYPE_PROPNAMES = ['MAXDEPTH']

class QPath(object):
    '''QPath
    '''
    def __init__(self, qpath_str):
        self._qpath_str = qpath_str
    
    def __str__(self):
        return self._qpath_str
    
    @property
    def parsed_qpath(self):
        '''解析后的内容
        '''
        result = QPathParser().parse(self._qpath_str)[0]
        for it in result:
            for key in it:
                if not key in ['Id', 'Text', 'Type', 'Visible', 'Desc', 'MaxDepth', 'Instance']:
                    if not key.startswith('Field_') and not key.startswith('Method_'):
                        raise RuntimeError('QPath(%s) keyword error: %s' % (self._qpath_str, key))
        return result
    
    @property
    def _parsed_qpath(self):
        return self.parsed_qpath

if __name__ == '__main__':
    pass
