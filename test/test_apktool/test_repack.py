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

'''repack.py unittest
'''


try:
    from unittest import mock
except:
    import mock

import os
import tempfile
import unittest

from qt4a.apktool import apkfile, repack


class TestRepack(unittest.TestCase):

    def test_get_apk_signature(self):
        apk_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'qt4a', 'androiddriver', 'tools', 'QT4AHelper.apk')
        apk_file = apkfile.APKFile(apk_path)
        for it in apk_file.list_dir('META-INF'):
            if it.lower().endswith('.rsa'):
                tmp_rsa_path = tempfile.mkstemp('.rsa')[1]
                apk_file.extract_file('META-INF/%s' % it, tmp_rsa_path)
                orig_signature = repack.get_apk_signature(tmp_rsa_path).strip()
                self.assertEqual(orig_signature, '3082036f30820257a00302010202046d23394e300d06092a864886f70d01010b05003067310b300906035504061302383631123010060355040813094775616e67646f6e673111300f060355040713085368656e7a68656e3110300e060355040a130754656e63656e743110300e060355040b130754656e63656e74310d300b06035504031304515434413020170d3137303731383038303130335a180f32313136303632343038303130335a3067310b300906035504061302383631123010060355040813094775616e67646f6e673111300f060355040713085368656e7a68656e3110300e060355040a130754656e63656e743110300e060355040b130754656e63656e74310d300b060355040313045154344130820122300d06092a864886f70d01010105000382010f003082010a0282010100a05d7ca7768dd6a16098236ee3d670d139abbda479557bee2ce62e0a5ee9f825c986e8ba875decb4dec3fb13a933bbfc9434a70442b6cccc8d6d12db6e510cf915cc25c71bb4670876ddf15de880340a3af3d656e76cef452ccd2192879e4eef67aca9b203124dc5c978f57533c707e49abf0ca3f5691d3de9048587c7aa22ecf703d589236edcf1a0cadb26fbbb126326f200ce9b5573e36dd2d63363ad1c518df2a9550b7aede75bc74e44484fcb177c8c6515e7f2011af1a987c1bc11ddef1303bcaf04f7ea186ce66d96921021e3ebf7141801a7abe09663caae7386785b144a358b3bb877c190ee9ac0a8f313a48794ca2a3fb8c0e7e38afac4f0956cc50203010001a321301f301d0603551d0e041604144d974cc4e8bd5b5116ff0ef2676c4556ca4aa727300d06092a864886f70d01010b050003820101000fd165541ad15e729549fa497eae037893032f565fc55ceea2fbb8e77a283fbf23dab00afe1f6943056cbc62a567400879418abc6a3646bdc7bbf51f84741173d7f8386a07e89d7cd1228e387fbd727af8402231bf5834450799ba79251f3673c45fb523301a3791a279523c78af98c0932e17a365b3a28c59701a123e0b3df49ec9d1ef6203b4b92ce67b100d2f493c4de0376103b4b2f4b1f40ba09e5bc3329f184646af0d046968b3af2af7786fc060f3c0bfd757bf2d4a32d222fb701a7032fd19271bb6cffc06f37cc2921bec1e2f6ff5a58b4010e54b5c8d18a6394dd6ed715800fcc7fc47436345294e6eb791cf585bee38ab6079559d3a40802f9802')
                return
        else:
            raise RuntimeError('No signature file found in QT4AHelper.apk')


if __name__ == '__main__':
    unittest.main()