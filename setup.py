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

import os
from setuptools import setup, find_packages
  
BASE_DIR = os.path.realpath(os.path.dirname(__file__))
  
def generate_version():
    version = "2.2.0"
    if os.path.isfile(os.path.join(BASE_DIR, "version.txt")):
        with open("version.txt", "r") as fd:
            content = fd.read().strip()
            if content:
                version = content
    return version
  
def parse_requirements():
    reqs = []
    if os.path.isfile(os.path.join(BASE_DIR, "requirements.txt")):
        with open(os.path.join(BASE_DIR, "requirements.txt"), 'r') as fd:
            for line in fd.readlines():
                line = line.strip()
                if line:
                    reqs.append(line)
    return reqs

def list_data_files(packages):
    '''遍历package中的文件并查找所有资源文件
    
    :returns: list
    '''
    data_files = []
    for package in packages:
        file_path = os.path.join(BASE_DIR, *package.split('.'))
        if os.path.isdir(file_path):
            for dirpath, dirnames, filenames in os.walk(file_path):
                dirname = '/'.join(os.path.relpath(dirpath, BASE_DIR).split(os.path.sep))
                child_data_files = []
                for filename in filenames:
                    if not filename.endswith('.py') and not filename.endswith('.pyc'):
                        child_data_files.append(dirname+'/'+filename)
                if child_data_files:
                    data_files.append((dirname, child_data_files))
        else:
            dirname = '/'.join(package.split('.')[0:-1])    
            data_files.append(dirname+'/'+package.split('.')[-1])
    return data_files 

def get_description():
    with open(os.path.join(BASE_DIR, "README.md"), "rb") as fh:
        return fh.read().decode('utf8')
     
if __name__ == "__main__":  
    setup(
        zip_safe=False,
        version=generate_version(),
        name="qt4a",
        cmdclass={},
        packages=find_packages(exclude=("test", "test.*",)),
        include_package_data=True,
        description="QTA driver for Android app",
        long_description=get_description(),
        long_description_content_type="text/markdown",
        author="Tencent",
        license="Copyright(c)2010-2018 Tencent All Rights Reserved. ",
        install_requires=parse_requirements(),
        entry_points={'console_scripts': ['qt4a-manage = qt4a.management:qt4a_manage_main'], },        
        classifiers=[
          "Programming Language :: Python :: 2.7",
          "Operating System :: OS Independent",
        ],
        url="https://github.com/Tencent/QT4A",
        project_urls={"QT4A Documentation":"https://qt4a.readthedocs.io/zh_CN/latest/",},
    )