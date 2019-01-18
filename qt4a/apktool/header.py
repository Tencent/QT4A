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

'''结构体头部基类
'''

from six import string_types, with_metaclass
import os
import struct

class HeaderMetaClass(type):
    '''元类
    '''
    
    def __init__(cls, name, bases, attrd):
        header_format = '>' if cls.big_ending else '<'
        for _, fmt in cls.__header__:
            if not isinstance(fmt, string_types) and issubclass(fmt, StructHeaderBase): 
                fmt = fmt.header_format[1:]
            header_format += fmt

        header_size = struct.calcsize(header_format)
        cls.header_format = header_format
        cls.header_size = header_size
        total_header_size = 0
        c = cls
        while c != object:
            if c.__base__ != object and c.__header__ != c.__base__.__header__:
                total_header_size += c.header_size
            c = c.__base__
        cls.total_header_size = total_header_size
        super(HeaderMetaClass, cls).__init__(name, bases, attrd)
        
class StructHeaderBase(with_metaclass(HeaderMetaClass, object)):
    '''结构体头基类
    '''
    big_ending = False
    __header__ = []
    
    def __init__(self, path_or_fp=None):
        self._auto_close = False
        if path_or_fp == None:
            self._file_path = None
            self._file_size = 0
            self._fp = None
        elif hasattr(path_or_fp, 'tell') and hasattr(path_or_fp, 'seek'):
            # File like object
            self._file_path = None
            self._fp = path_or_fp
            pos = self._fp.tell()
            self._fp.seek(0, 2)
            self._file_size = self._fp.tell() - pos
            self._fp.seek(pos, 0)
        else:
            self._file_path = path_or_fp
            self._file_size = os.path.getsize(self._file_path)
            self._fp = open(self._file_path, 'rb')
            self._auto_close = True
            
        if self._fp: self.parse()
        
    def __del__(self):
        if not self._auto_close: return
        if not hasattr(self, '_fp') or not self._fp: return
        self._fp.close()
        del self._fp
    
    def _set_values(self, cls, items):
        '''
        '''
        offset = 0
        for i, (name, fmt) in enumerate(cls.__header__):
            if not isinstance(fmt, string_types) and issubclass(fmt, StructHeaderBase):
                obj = fmt()
                obj._set_values(fmt, items[i + offset:i + offset + fmt.header_size])
                offset += fmt.header_size - 1
                setattr(self, name, obj)
            elif len(fmt) == 1:
                setattr(self, name, items[i + offset])
            else:
                setattr(self, name, items[i + offset:i + offset + len(fmt)])
                offset += len(fmt) - 1
                
    def parse(self):
        '''解析文件头
        '''
        cls_list = []
        cls = self.__class__
        while cls != StructHeaderBase:
            cls_list.insert(0, cls)
            cls = cls.__base__
        
        for cls in cls_list:
            if not cls.__header__ or cls.__header__ == cls.__base__.__header__: continue
            header_data = self._fp.read(cls.header_size)
            items = struct.unpack_from(cls.header_format, header_data)
            assert(len(items) >= len(cls.__header__))
            self._set_values(cls, items)
    
    def get_values(self, cls=None):
        '''
        '''
        values = []
        if cls == None: cls = self.__class__
        for name, _ in cls.__header__:
            val = getattr(self, name)
            if isinstance(val, (list, tuple)):
                values.extend(val)
            elif isinstance(val, StructHeaderBase):
                values.extend(val.get_values())
            else:
                values.append(val)
            
        return values
    
    def serialize_header(self):
        '''序列化文件头
        '''
        result = b''
        cls = self.__class__
        while cls != StructHeaderBase:
            if cls.__header__ != cls.__base__.__header__:
                values = tuple(self.get_values(cls))
                try:
                    result = struct.pack(cls.header_format, *values) + result
                except struct.error:
                    raise RuntimeError('Params not match %s %s' % (cls.header_format, values))
            cls = cls.__base__
        return result
    
    def serialize(self):
        '''序列化
        '''
        return self.serialize_header()
    
    def write_header(self):
        '''写入文件头
        '''
        header = self.serialize_header()
        self._fp.write(header)
        
    def dump_header(self, indent=0):
        '''dump文件头
        '''
        result = []
        for name, fmt in self.__class__.__header__:
            val = getattr(self, name)
            if isinstance(val, StructHeaderBase):
                val = '\n' + val.dump_header(indent + 1)
            elif isinstance(val, list):
                val = ','.join([('0x%.2X' % it) for it in val])
            result.append('%s%s: %s' % (' ' * indent * 4, name, val))
        return '\n'.join(result)
        

