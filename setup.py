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
"""
打包脚本
"""

# 2015/06/09 banana 新建

import os
from setuptools import setup, find_packages


NAME = "qt4a"
VERSION = "1.0.0"
PACKAGES = ["qt4a"]
DATA_PACKAGES = ["qt4a.androiddriver.tools"]
# MODULES     = ["__main__"]

try:
    import _qt4a_version_stub
    VERSION = _qt4a_version_stub.VERSION
except:
    pass

def list_sub_pkgs(packages):
    '''查找全部的子包
    
    :returns: list
    '''
    pkgs = packages[:]
    for pkg in packages:
        subpkgs = find_packages(pkg)
        for subpkg in subpkgs:
            pkgs.append("%s.%s" % (pkg, subpkg))
    return pkgs
    
def list_data_files(packages):
    '''遍历package中的文件并查找所有资源文件
    
    :returns: list
    '''
    basedir = os.path.dirname(__file__)
    data_files = []
    for package in packages:
        file_path = os.path.join(basedir, *package.split('.'))
        if os.path.isdir(file_path):
            for dirpath, dirnames, filenames in os.walk(file_path):
                if os.path.basename(dirpath) == '.svn':
                    continue
                if '.svn' in dirnames:
                    dirnames.remove('.svn')
                dirname = '/'.join(os.path.relpath(dirpath, basedir).split(os.path.sep))
                child_data_files = []
                for filename in filenames:
                    if not filename.endswith('.py'):
                        child_data_files.append(dirname + '/' + filename)
                if child_data_files:
                    data_files.append((dirname, child_data_files))
        else:
            dirname = '/'.join(package.split('.')[0:-1])    
            data_files.append(dirname + '/' + package.split('.')[-1])
    return data_files
    
if __name__ == "__main__":
    
    setup(
      version=VERSION,
      name=NAME,
      packages=list_sub_pkgs(PACKAGES),
      # py_modules=MODULES,
      data_files=list_data_files(DATA_PACKAGES),
      author="Tencent",
      author_email="",
      license="Copyright(c)2010-2015 Tencent All Rights Reserved. ",
      requires=["qtaf"],
        )
