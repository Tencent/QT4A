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

'''util模块单元测试
'''

import unittest

from qt4a.androiddriver import util

class TestUtil(unittest.TestCase):
    '''util测试用例
    '''
    
    def test_general_encode(self):
        self.assertEqual(util.general_encode('中国'), '中国')
        self.assertEqual(util.general_encode(u'中国'), '中国')
        self.assertEqual(util.general_encode(b'China'), 'China')
    
    def test_encode_wrap(self):
        
        @util.encode_wrap
        def test(a, b='456'):
            return a, b
        
        result = test('aaa', u'bbb')
        self.assertEqual(result[0], 'aaa')
        self.assertEqual(result[1], 'bbb')
        
        result = test(u'中国')
        self.assertEqual(result[0], '中国')
        self.assertEqual(result[1], '456')
        
        result = test('中国', b=u'深圳')
        self.assertEqual(result[0], '中国')
        self.assertEqual(result[1], '深圳')
        
if __name__ == '__main__':
    unittest.main()