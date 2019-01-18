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

'''APK安装包
'''

import zipfile
from io import BytesIO

class APKFile(object):
    '''
    '''
    def __init__(self, apk_path):
        self._apk_path = apk_path
        self._dir_tree = {}  # 目录树
        with open(self._apk_path, 'rb') as f:
            apk_data = f.read()
            self._fp = zipfile.ZipFile(BytesIO(apk_data), mode='r')
            for it in self._fp.filelist:
                self._dir_tree[it] = None
    
    def _get_item(self, rav_path):
        '''get ZipInfo item
        '''
        for it in self._dir_tree:
            filename = it
            if isinstance(it, zipfile.ZipInfo): filename = it.filename
            if filename == rav_path:
                return it
        return None
            
    def get_file(self, rav_path):
        '''获取apk内部文件的句柄
        
        :param rav_path: 文件在apk内的相对路径
        :type  rav_path: string
        '''
        it = self._get_item(rav_path)
        if it != None:
            data = self._fp.read(it.filename)
            return BytesIO(data)
        return None
    
    def list_dir(self, dir_rav_path):
        '''列举安装包中的文件列表
        
        :param dir_rav_path: 安装包中的目录相对路径
        :type dir_rav_path:  string
        '''
        result = []
        if dir_rav_path[-1] != '/': dir_rav_path += '/'
        for it in self._dir_tree:
            if isinstance(it, zipfile.ZipInfo): it = it.filename
            if it.startswith(dir_rav_path):
                result.append(it.split('/')[-1])
        return result
    
    def add_file(self, rav_path, file_data):
        '''添加文件
        '''
        it = self._get_item(rav_path)
        if not it: it = rav_path
        self._dir_tree[it] = file_data
        
    def delete_file(self, rav_path):
        '''删除安装包内的文件
        
        :param rav_path: 文件在apk内的相对路径
        :type  rav_path: string
        '''
        it = self._get_item(rav_path)
        if it != None: 
            del self._dir_tree[it]
    
    def extract_file(self, rav_path, save_path):
        '''提取文件到本地
        
        :param rav_path: 文件在apk内的相对路径
        :type rav_path:  string
        :param save_path:保存路径
        :type save_path: string
        '''
        it = self._get_item(rav_path)
        if not it: raise RuntimeError('file %s not in apk %s' % (rav_path, self._apk_path))
        data = self._fp.read(rav_path)
        with open(save_path, 'wb') as f:
            f.write(data)
        
    def save(self, save_path):
        '''保存
        '''
        out_fp = zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED)
        for it in self._dir_tree:
            data = self._dir_tree[it]
            if not data: 
                filename = it
                if isinstance(it, zipfile.ZipInfo): filename = it.filename
                data = self._fp.read(filename)
            out_fp.writestr(it, data)
        out_fp.close()
    
if __name__ == '__main__':
    pass
    
