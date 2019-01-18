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

'''qpath模块单元测试
'''

try:
    from unittest import mock
except:
    import mock
import unittest

from qt4a.qpath import QPath

class TestQPath(unittest.TestCase):
    '''QPath类测试用例
    '''
    
    def test_id(self):
        self.assertEqual(QPath('/Id="webview"').parsed_qpath, [{'Id': ['=', 'webview']}])
    
    def test_type(self):
        self.assertEqual(QPath('/Type="WebView"').parsed_qpath, [{'Type': ['=', 'WebView']}])
    
    def test_text(self):
        self.assertEqual(QPath('/Text="标题"').parsed_qpath, [{'Text': ['=', '标题']}])
    
    def test_desc(self):
        self.assertEqual(QPath('/Desc="文本"').parsed_qpath, [{'Desc': ['=', '文本']}])
        
    def test_instance(self):
        self.assertEqual(QPath('/Text="标题" /Instance=1').parsed_qpath, [{'Text': ['=', '标题']}, {'Instance': ['=', 1]}])
    
    def test_maxdepth(self):
        self.assertEqual(QPath('/Type="TextView" /Text="消息" && MaxDepth=3').parsed_qpath, [{'Type': ['=', 'TextView']}, {'MaxDepth': ['=', 3], 'Text': ['=', '消息']}])
        
if __name__ == '__main__':
    unittest.main()