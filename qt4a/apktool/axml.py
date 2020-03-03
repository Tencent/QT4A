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

'''AXML格式处理
'''

import logging
import re
import six
import struct
import xml.dom.minidom
from qt4a.apktool.__init__ import APKError
from qt4a.apktool.header import StructHeaderBase

class EnumAttrType(object):
    '''These are attribute resource constants for the platform, as found in android.R.attr
    '''
    THEME_ATTR = 'theme', 0x1010000
    LABEL_ATTR = 'label', 0x01010001
    ICON_ATTR = 'icon', 0x01010002
    NAME_ATTR = 'name', 0x01010003
    PERMISSION_ATTR = 'permission', 0x01010006
    READ_PERMISSION = 'readPermission', 0x1010007
    WRITE_PERMISSION = 'writePermission', 0x1010008
    PROTECTION_LEVEL_ATTR = 'protectionLevel', 0x1010009
    PERMISSION_GROUP_ATTR = 'permissionGroup', 0x101000a
    PERSISTENT = 'persistent', 0x101000d
    ENABLED_ATTR = 'enabled', 0x101000e
    DEBUGGABLE_ATTR = 'debuggable', 0x0101000f
    EXPORTED_ATTR = 'exported', 0x1010010
    PROCESS_ATTR = 'process', 0x1010011
    TASK_AFFINITY_ATTR = 'taskAffinity', 0x1010012
    MULTI_PROCESS_ATTR = 'multiprocess', 0x1010013
    CLEAR_TASK_ON_LAUNCH_ATTR = 'clearTaskOnLaunch', 0x1010015
    EXCLUDE_FROM_RECENTS_ATTR = 'excludeFromRecents', 0x1010017
    AUTHORITIES_ATTR = 'authorities', 0x1010018
    INIT_ORDER = 'initOrder', 0x101001a
    GRANT_URI_PERMISSIONS_ATTR = 'grantUriPermissions', 0x101001b
    PRIORITY_ATTR = 'priority', 0x101001c
    LAUNCH_MODE_ATTR = 'launchMode', 0x101001d
    SCREEN_ORIENTATION_ATTR = 'screenOrientation', 0x0101001e
    CONFIG_CHANGES_ATTR = 'configChanges', 0x101001f
    VALUE_ATTR = 'value', 0x1010024
    RESOURCE_ATTR = 'resource', 0x01010025
    MIME_TYPE_ATTR = 'mimeType', 0x1010026
    SCHEME_ATTR = 'scheme', 0x1010027
    HOST_ATTR = 'host', 0x1010028
    PATH_PREFIX_ATTR = 'pathPrefix', 0x101002b
    WINDOW_ANIMATION_STYLE = 'windowAnimationStyle', 0x10100ae
    TARGET_ACTIVITY_ATRR = 'targetActivity', 0x1010202
    ALWAYS_RETAIN_TASK_STATE_ATTR = 'alwaysRetainTaskState', 0x1010203
    ALLOW_TASK_REPARENTING_ATTR = 'allowTaskReparenting', 0x1010204
    MIN_SDK_VERSION_ATTR = 'minSdkVersion', 0x0101020c
    KEEO_SCREEN_ON_ATTR = 'keepScreenOn', 0x1010216
    VERSION_CODE_ATTR = 'versionCode', 0x0101021b
    VERSION_NAME_ATTR = 'versionName', 0x0101021c
    REQ_TOUCH_SCREEN_ATTR = 0x01010227
    REQ_KEYBOARD_TYPE_ATTR = 0x01010228
    REQ_HARD_KEYBOARD_ATTR = 0x01010229
    REQ_NAVIGATION_ATTR = 0x0101022a
    WINDOW_SOFTINPUT_MODE_ATTR = 'windowSoftInputMode', 0x101022b
    NO_HISTORY_ATTR = 'noHistory', 0x101022d
    REQ_FIVE_WAY_NAV_ATTR = 0x01010232
    ANY_DENSITY_ATTR = 'anyDensity', 0x0101026c
    TARGET_SDK_VERSION_ATTR = 'targetSdkVersion', 0x01010270
    MAX_SDK_VERSION_ATTR = 0x01010271
    TEST_ONLY_ATTR = 0x01010272
    ALLOW_BACKUP_ATTR = 'allowBackup', 0x1010280
    GL_ES_VERSION_ATTR = 'glEsVersion', 0x01010281
    SMALL_SCREEN_ATTR = 'smallScreens', 0x01010284
    NORMAL_SCREEN_ATTR = 'normalScreens', 0x01010285
    LARGE_SCREEN_ATTR = 'largeScreens', 0x01010286
    REQUIRED_ATTR = 'required', 0x0101028e
    INSTALL_LOCATION_ATTR = 'installLocation', 0x10102b7
    VM_SAFE_MODE = 'vmSafeMode', 0x10102b8
    XLARGE_SCREEN_ATTR = 0x010102bf
    SCREEN_SIZE_ATTR = 0x010102ca
    SCREEN_DENSITY_ATTR = 0x010102cb
    HARDWARE_ACCELERATED_ATTR = 'hardwareAccelerated', 0x10102d3
    LARGE_HEAP = 'largeHeap', 0x101035a
    REQUIRES_SMALLEST_WIDTH_DP_ATTR = 0x01010364
    COMPATIBLE_WIDTH_LIMIT_DP_ATTR = 0x01010365
    LARGEST_WIDTH_LIMIT_DP_ATTR = 0x01010366
    STOP_WITH_TASK_ATTR = 'stopWithTask', 0x101036a
    PUBLIC_KEY_ATTR = 0x010103a6
    ISOLATED_PROCESS = 'isolatedProcess', 0x10103a9
    SUPPORTS_RT1 = 'supportsRtl', 0x10103af
    CATEGORY_ATTR = 0x010103e8
    RESIZEABLE_ACTIVITY_ATTR = 'resizeableActivity', 0x10104f6
    NETWORK_SECURITY_CONFIG = 'networkSecurityConfig', 0x1010527
    COMPILE_SDK_VERSION_ATTR = 'compileSdkVersion', 0x01010572
    COMPILE_SDK_VERSION_CODENAME_ATTR = 'compileSdkVersionCodename', 0x01010573
    APP_COMPONENTFACTORY = 'appComponentFactory', 0x101057a

    @staticmethod
    def list():
        '''获取attr列表
        '''
        result = []
        for key in EnumAttrType.__dict__:
            if key != key.upper(): continue
            val = EnumAttrType.__dict__[key]
            if not isinstance(val, tuple): continue
            result.append(val)
        result = sorted(result, key=lambda it : it[1])
        return result
    
    @staticmethod
    def get_value(name):
        '''
        '''
        for key, val in EnumAttrType.list():
            if key == name: return val
        return 0xFFFFFFFF
    
class EnumResValueType(object):
    '''ResValue枚举类型
    '''
    TYPE_NULL = 0x00
    TYPE_REFERENCE = 0x01
    TYPE_ATTRIBUTE = 0x02
    TYPE_STRING = 0x03
    TYPE_FLOAT = 0x04  # The 'data' holds a single-precision floating point number.
    TYPE_DIMENSION = 0x05
    TYPE_FRACTION = 0x06
    TYPE_DYNAMIC_REFERENCE = 0x07
    TYPE_FIRST_INT = 0x10
    TYPE_INT_DEC = 0x10
    TYPE_INT_HEX = 0x11
    TYPE_INT_BOOLEAN = 0x12  # The 'data' is either 0 or 1, for input "false" or "true" respectively.
    TYPE_FIRST_COLOR_INT = 0x1c
    TYPE_INT_COLOR_ARGB8 = 0x1c
    TYPE_INT_COLOR_RGB8 = 0x1d
    TYPE_INT_COLOR_ARGB4 = 0x1e
    TYPE_INT_COLOR_RGB4 = 0x1f
    TYPE_LAST_COLOR_INT = 0x1f
    TYPE_LAST_INT = 0x1f
    
class ResValue(StructHeaderBase):
    '''Res_value
    '''
    __header__ = [('size', 'H'),  # Number of bytes in this structure.
                  ('res0', 'B'),  # Always set to 0.
                  ('data_type', 'B'),
                  ('data', 'I'),  # The data for this item, as interpreted according to dataType.
                  ]
    
    def __init__(self, *args):
        self.size = 8
        self.res0 = 0
        super(ResValue, self).__init__(*args)
    
    def parse(self):
        super(ResValue, self).parse()
        assert(self.size == 8)
        assert(self.res0 == 0)
        
    @staticmethod
    def convert_from(val):
        '''根据val生成ResValue对象
        '''
        assert(isinstance(val, six.string_types))
        rv = ResValue()
        ref_pattern = re.compile(r'^@0x[\w|\d]+$')
        hex_pattern = re.compile(r'^0x[\w|\d]+$')
        float_pattern = re.compile(r'^\d+\.\d+f$')
        
        if ref_pattern.match(val):
            rv.data_type = EnumResValueType.TYPE_REFERENCE
            val = int(val[1:], 16)
            rv.data = val
        elif hex_pattern.match(val):
            # 16进制
            rv.data_type = EnumResValueType.TYPE_INT_HEX
            val = int(val, 16)
            rv.data = val
        elif val.isdigit():
            # 10进制整型
            val = int(val)
            rv.data_type = EnumResValueType.TYPE_INT_DEC
            rv.data = val
        elif float_pattern.match(val):
            # 浮点数
            val = val[:-1]
            val = float(val)
            rv.data_type = EnumResValueType.TYPE_FLOAT
            rv.set_float(val)
        elif val in ('true', 'false'):
            # bool
            rv.data_type = EnumResValueType.TYPE_INT_BOOLEAN
            rv.data = 0 if val == 'false' else 1
        else:
            # 字符串
            rv.data_type = EnumResValueType.TYPE_STRING
            rv.data = 0xFFFFFFFF  # 上层修改该值
        return rv
    
    def format_value(self):
        '''
        '''
        if self.size == 8:
            if self.data_type == EnumResValueType.TYPE_FIRST_INT:
                return str(self.data)
            elif self.data_type == EnumResValueType.TYPE_STRING:
                return self.data  # 调用方进行转换
            elif self.data_type == EnumResValueType.TYPE_REFERENCE:
                return '@' + str(hex(self.data))
            elif self.data_type == EnumResValueType.TYPE_INT_BOOLEAN:
                return 'false' if self.data == 0 else 'true'
            elif self.data_type == EnumResValueType.TYPE_INT_HEX:
                return str(hex(self.data))
            elif self.data_type == EnumResValueType.TYPE_FLOAT:
                return str(self.get_float()) + 'f'
                
        raise NotImplementedError('%d %d' % (self.size, self.data_type))
    
    def get_float(self):
        '''获取浮点数
        '''
        flag = self.data >> 31
        e = ((self.data >> 23) & 255) - 127
        n = ((self.data & ((1 << 23) - 1)))
        n /= ((1 << 23) * 1.0)
        return ((-1) ** flag) * (n + 1) * (2 ** e)
    
    def set_float(self, val):
        '''设置浮点数
        '''
        flag = 0
        if val < 0: flag = 1
        e = 0
        while val >= 2:
            val /= 2
            e += 1
        while val < 1:
            val *= 2
            e -= 1

        val = int((val - 1) * (1 << 23))
        e += 127
        
        self.data = (flag << 31) | (e << 23) | val
    
class ResChunkHeader(StructHeaderBase):
    '''ResChunk_header
    '''
    
    __header__ = [('type', 'H'),  # chunk的类型
                  ('head_size', 'H'),  # chunk的头部大小
                  ('size', 'I')  # chunk的大小
                  ]
    __type__ = -1
    
    def __init__(self, path_or_fp=None):
        super(ResChunkHeader, self).__init__(path_or_fp)
        if not path_or_fp and self.__class__ != ResChunkHeader:
            # 自动生成字段
            self.type = self.__class__.__type__
            self.header_size = self.__class__.total_header_size
            
    def parse(self):
        '''
        '''
        super(ResChunkHeader, self).parse()
        assert(self.__class__ == ResChunkHeader or self.__class__.__type__ != -1)
        assert(self.__class__ == ResChunkHeader or self.type == self.__class__.__type__)
        assert(self.__class__ == ResChunkHeader or self.head_size == self.__class__.total_header_size)
    
    def serialize_header(self):
        '''序列化文件头
        '''
        self.type = self.__class__.__type__
        self.head_size = self.__class__.total_header_size
        return super(ResChunkHeader, self).serialize_header()
    
class ResXMLTreeHeader(ResChunkHeader):
    '''ResXMLTree_header
    '''
    __type__ = 0x3

class ResXMLTreeNode(ResChunkHeader):
    '''ResXMLTree_node
    '''
    
    __header__ = [('line_number', 'I'),
                  ('comment_index', 'I')  # Optional XML comment that was associated with this element; -1 if none.
                  ]
    
    def __init__(self, *args):
        self.line_number = 2
        self.comment_index = 0xFFFFFFFF
        super(ResXMLTreeNode, self).__init__(*args)

class ResXMLTreeCDataExt(StructHeaderBase):
    '''
    '''
    __header__ = [('data', 'I'),
                  ('typed_data', ResValue)
                  ]
    
class ResCDataChunk(ResXMLTreeNode):
    '''ResXMLTree_cdataExt
    '''
    __type__ = 0x104
    
    def __init__(self, *args):
        self.body = ResXMLTreeCDataExt()
        super(ResCDataChunk, self).__init__(*args)
        
    def parse(self):
        super(ResCDataChunk, self).parse()
        self.body = ResXMLTreeCDataExt(self._fp)
        assert(self.size == self.total_header_size + self.body.total_header_size)
        
class ResStringPoolHeader(ResChunkHeader):
    '''ResStringPool_header
    '''
    __header__ = [('string_count', 'I'),  # Number of strings in this pool (number of uint32_t indices that follow in the data)
                  ('style_count', 'I'),  # Number of style span arrays in the pool (number of uint32_t indices follow the string indices)
                  ('flags', 'I'),  # 0 256: String pool is encoded in UTF-8
                  ('strings_start', 'I'),  # Index from header of the string data
                  ('styles_start', 'I')  # Index from header of the style data
                  ]
    __type__ = 0x1
    
    def __init__(self, *args):
        self.style_count = 0
        self.flags = 0
        self.styles_start = 0
        self.string_count = 0
        self.strings_start = ResStringPoolHeader.total_header_size
        self._utf8_flag = False
        super(ResStringPoolHeader, self).__init__(*args)
        
    def parse(self):
        '''
        '''
        super(ResStringPoolHeader, self).parse()
        assert(self.style_count == 0)
        assert(self.flags in (0, 256))
        assert(self.styles_start == 0)
        if self.flags == 256:
            # utf8
            self._utf8_flag = True
            
class ResStringPoolChunk(ResStringPoolHeader):
    '''字符串池
    '''
    def __init__(self, *args):
        self.string_offset_list = []  # 字符串偏移数组
        self.style_offset_list = []  # style偏移数组
        self.string_list = []
        super(ResStringPoolChunk, self).__init__(*args)
        
    def add_string(self, string):
        '''添加字符串
        '''
        if six.PY2 and not isinstance(string, unicode):
            string = string.decode('utf8')
        if len(self.string_list) == 0:
            self.string_offset_list.append(0)
        else:
            self.string_offset_list.append(self.string_offset_list[-1] + (len(self.string_list[-1]) + 2) * 2)
        self.string_list.append(string)
        self.string_count += 1
        self.strings_start += 4
        return len(self.string_list) - 1
    
    def read_strings(self):
        '''
        '''
        start_offset = self._fp.tell()
        for string_offset in self.string_offset_list:
            if string_offset != self._fp.tell() - start_offset:
                index = self.string_offset_list.index(string_offset)
                if index >= 0:
                    self.string_list.append(self.string_list[index])
                    continue
 
                raise APKError('Invalid string offset: %d' % string_offset)

            assert(string_offset == (self._fp.tell() - start_offset))
            if not self._utf8_flag:
                str_len = struct.unpack('<H', self._fp.read(2))[0]
                str_len *= 2  # unicode
            else:
                str_len = struct.unpack('<BB', self._fp.read(2))[0]
            
            string = self._fp.read(str_len)
            if not self._utf8_flag:
                if six.PY2:
                    string = ''.join([unichr(struct.unpack('<H', string[i:i + 2])[0]) for i in range(0, str_len, 2)])
                    string = string.encode('utf8')
                else:
                    string = ''.join([chr(struct.unpack('<H', string[i:i + 2])[0]) for i in range(0, str_len, 2)])
                assert(self._fp.read(2) == b'\x00\x00')
            else:
                assert(self._fp.read(1) == b'\x00')
            
            self.string_list.append(string)
            
        if self._utf8_flag:
            assert(self._fp.read(1) == '\x00')
            
    def build_strings(self):
        '''
        '''
        result = b''
        for string in self.string_list:
            str_len = len(string)
            result += struct.pack('<H', str_len)
            for c in string:
                result += struct.pack('<H', ord(c))
            result += b'\x00\x00'
        return result
    
    def parse(self):
        super(ResStringPoolChunk, self).parse()
        for _ in range(self.string_count):
            offset = struct.unpack_from('I', self._fp.read(4))[0]
            self.string_offset_list.append(offset)

        for _ in range(self.style_count):
            offset = struct.unpack_from('I', self._fp.read(4))[0]
            self.style_offset_list.append(offset)

        assert(self.strings_start == self._fp.tell() - 8)
        
        self.read_strings()
        
        if self._fp.tell() < self.size + 8:
            bytes_to_read = self.size + 8 - self._fp.tell()
            assert(self._fp.read(bytes_to_read) == b'\x00' * bytes_to_read)  # styles
        
        total_size = self.total_header_size + 4 * self.string_count + 4 * self.style_count
        for s in self.string_list:
            if not self._utf8_flag:
                if six.PY2:
                    s = s.decode('utf8')
                total_size += (len(s) + 2) * 2
            else:
                total_size += len(s) + 3
        assert(self.size % 4 == 0)
        
    def serialize(self):
        '''序列化
        '''
        result = b''
        for it in self.string_offset_list:
            result += struct.pack('I', it)
        for it in self.style_offset_list:
            result += struct.pack('I', it)
        result += self.build_strings()
        if len(result) % 4 != 0:
            result += b'\x00\x00'
        self.size = self.total_header_size + len(result)
        result = self.serialize_header() + result
        return result
    
class ResXMLResourceMapChunk(ResChunkHeader):
    '''
    '''
    __type__ = 0x0180
    
    def __init__(self, *args):
        self.res_map = []
        super(ResXMLResourceMapChunk, self).__init__(*args)
        
    def parse(self):
        super(ResXMLResourceMapChunk, self).parse()
        total_size = self.total_header_size
        for _ in range((self.size - self.header_size) // 4):
            self.res_map.append(struct.unpack('I', self._fp.read(4))[0])
            total_size += 4
        for it in self.res_map:
            for key in EnumAttrType.__dict__:
                if key != key.upper(): continue
                val = EnumAttrType.__dict__[key]
                if isinstance(val, tuple):
                    if val[1] == it:
                        break
                elif val == it:
                    break
            else:
                logging.warn('[%s] Attribute 0x%x not defined' % (self.__class__.__name__, it))
        assert(self.size == total_size)
    
    def serialize(self):
        result = b''
        for it in self.res_map:
            result += struct.pack('I', it)
        self.size = self.total_header_size + len(result)
        return self.serialize_header() + result
    
class ResXMLTreeNamespaceExt(StructHeaderBase):
    '''ResXMLTree_namespaceExt
    '''
    
    __header__ = [('prefix_index', 'I'),
                  ('uri_index', 'I')
                  ]

class ResXMLStartNamespaceChunk(ResXMLTreeNode):
    '''
    '''
    __type__ = 0x0100
    
    def __init__(self, *args):
        self.body = ResXMLTreeNamespaceExt()
        super(ResXMLStartNamespaceChunk, self).__init__(*args)
        
    def parse(self):
        '''
        '''
        super(ResXMLStartNamespaceChunk, self).parse()
        self.body = ResXMLTreeNamespaceExt(self._fp)
        assert(self.size == self.total_header_size + self.body.total_header_size)
        
    def serialize(self):
        result = self.body.serialize_header()
        self.size = self.total_header_size + len(result)
        return self.serialize_header() + result
    
class ResXMLEndNamespaceChunk(ResXMLTreeNode):
    '''
    '''
    __type__ = 0x0101
    
    def __init__(self, *args):
        self.body = ResXMLTreeNamespaceExt()
        super(ResXMLEndNamespaceChunk, self).__init__(*args)
        
    def parse(self):
        '''
        '''
        super(ResXMLEndNamespaceChunk, self).parse()
        self.body = ResXMLTreeNamespaceExt(self._fp)
        assert(self.size == self.total_header_size + self.body.total_header_size)
        
    def serialize(self):
        result = self.body.serialize()
        self.size = self.total_header_size + len(result)
        return self.serialize_header() + result
    
class ResXMLTreeAttrExt(StructHeaderBase):
    '''ResXMLTree_attrExt
    '''
    __header__ = [('ns_index', 'I'),
                  ('name_index', 'I'),  # String name of this node if it is an ELEMENT; the raw character data if this is a CDATA node.
                  ('attribute_start', 'H'),  #  Byte offset from the start of this structure where the attributes start.
                  ('attribute_size', 'H'),  # Size of the ResXMLTree_attribute structures that follow.
                  ('attribute_count', 'H'),
                  ('id_index', 'H'),  # Index (1-based) of the "id" attribute. 0 if none.
                  ('class_index', 'H'),
                  ('style_index', 'H')
                  ]
    
    def __init__(self, *args):
        self.ns_index = 0xFFFFFFFF
        self.attribute_start = 20
        self.attribute_size = 20
        self.id_index = 0
        self.class_index = 0
        self.style_index = 0
        super(ResXMLTreeAttrExt, self).__init__(*args)
    
    def parse(self):
        '''
        '''
        super(ResXMLTreeAttrExt, self).parse()
        assert(self.ns_index == 0xFFFFFFFF)
        assert(self.attribute_start == 20)
        assert(self.attribute_size == 20)
        assert(self.id_index == 0)
        assert(self.class_index == 0)
        assert(self.style_index == 0)
        
class ResXMLTreeAttribute(StructHeaderBase):
    '''ResXMLTree_attribute  
    '''
    __header__ = [('ns_index', 'I'),
                  ('name_index', 'I'),  # Name of this attribute
                  ('raw_value', 'I'),  # The original raw string value of this attribute
                  ('typed_value', ResValue)
                  ]
    
class ResXMLStartElementChunk(ResXMLTreeNode):
    '''
    '''
    __type__ = 0x0102
    
    def __init__(self, *args):
        self.attr_ext = ResXMLTreeAttrExt()
        self.attrs = []
        super(ResXMLStartElementChunk, self).__init__(*args)
        
    def parse(self):
        '''
        '''
        super(ResXMLStartElementChunk, self).parse()
        self.attr_ext = ResXMLTreeAttrExt(self._fp)
        total_size = self.total_header_size + self.attr_ext.total_header_size
        for _ in range(self.attr_ext.attribute_count):
            attr = ResXMLTreeAttribute(self._fp)
            self.attrs.append(attr)
            total_size += attr.total_header_size
        assert(self.size == total_size)    
        
    def serialize(self):
        result = self.attr_ext.serialize()
        for attr in self.attrs:
            result += attr.serialize()
        self.size = self.total_header_size + len(result)
        return self.serialize_header() + result
    
class ResXMLTreeEndElementExt(StructHeaderBase):
    '''ResXMLTree_endElementExt
    '''
    __header__ = [('ns_index', 'I'),
                  ('name_index', 'I')
                  ]
    
class ResXMLEndElementChunk(ResXMLTreeNode):
    '''
    '''
    __type__ = 0x0103
    
    def __init__(self, *args):
        self.body = ResXMLTreeEndElementExt()
        super(ResXMLEndElementChunk, self).__init__(*args)
        
    def parse(self):
        '''
        '''
        super(ResXMLEndElementChunk, self).parse()
        self.body = ResXMLTreeEndElementExt(self._fp)
        assert(self.size == self.total_header_size + self.body.total_header_size)
        
    def serialize(self):
        result = self.body.serialize()
        self.size = self.total_header_size + len(result)
        return self.serialize_header() + result
    
class AXMLFile(ResXMLTreeHeader):
    '''AXML文件
    '''
    
    def _get_string(self, index):
        '''获取StringPool中的字符串
        '''
        if index == 0xFFFFFFFF: return None
        return self.string_pool_chunk.string_list[index]
    
    def parse(self):
        '''
        '''
        super(AXMLFile, self).parse()
        assert(self.size == self._file_size)
        
        # self._string_list = []
        
        self.string_pool_chunk = ResStringPoolChunk(self._fp)

        # chunk = ResChunkHeader(self._fp)
        # self._fp.seek(-8, 1)

        # if chunk.type == ResXMLResourceMapChunk.__type__:
        self.res_map_chunk = ResXMLResourceMapChunk(self._fp)
        for i, it in enumerate(self.res_map_chunk.res_map):
            k = ''
            for key in EnumAttrType.__dict__:
                if key != key.upper(): continue
                val = EnumAttrType.__dict__[key]
                if isinstance(val, tuple):
                    if val[1] == it:
                        k = val[0]
                        break
                elif val == it:
                    k = key
                    break
            if k == self.string_pool_chunk.string_list[i]: continue
     
        self.start_ns_chunk = ResXMLStartNamespaceChunk(self._fp)
        
        self.ns_prefix = self._get_string(self.start_ns_chunk.body.prefix_index)
        self.ns_uri = self._get_string(self.start_ns_chunk.body.uri_index)

        self.elements = None  # 树状结构
        
        element_node = None
        while True:
            chunk_header = ResChunkHeader(self._fp)
            self._fp.seek(-8, 1)
            if chunk_header.type == ResXMLStartElementChunk.__type__:
                element = ResXMLStartElementChunk(self._fp)
                new_element_node = {}
                new_element_node['elem'] = element
                new_element_node['attrs'] = element.attrs
                new_element_node['children'] = []
                if self.elements:
                    new_element_node['parent'] = element_node
                    element_node['children'].append(new_element_node)
                    element_node = new_element_node
                else:
                    element_node = self.elements = new_element_node
                    
                tag_name = self._get_string(element.attr_ext.name_index)

                if tag_name == 'activity':
                    # 检查是否存在name属性
                    for attr in element.attrs:
                        if self._get_string(attr.name_index) == 'name':
                            assert(len(self._get_string(attr.raw_value)) > 0)
                            break
                    else:
                        raise APKError('activity does not specify android:name attribute')
            elif chunk_header.type == ResXMLEndElementChunk.__type__:
                end_elem_chunk = ResXMLEndElementChunk(self._fp)
                assert(end_elem_chunk.body.ns_index == element_node['elem'].attr_ext.ns_index)
                assert(end_elem_chunk.body.name_index == element_node['elem'].attr_ext.name_index)
                assert('parent' in element_node or element_node == self.elements)
                if 'parent' in element_node: 
                    element_node = element_node['parent']
                else:
                    break
            elif chunk_header.type == ResCDataChunk.__type__:
                cdata_chunk = ResCDataChunk(self._fp)
            else:
                raise NotImplementedError('Unsupported type=0x%x header_size=%d chunk_size=%d' % (chunk_header.type, chunk_header.head_size, chunk_header.size))
        
        self.end_ns_chunk = ResXMLEndNamespaceChunk(self._fp)
        assert(self.end_ns_chunk.body.prefix_index == self.start_ns_chunk.body.prefix_index)
        assert(self.end_ns_chunk.body.uri_index == self.start_ns_chunk.body.uri_index)

        assert(self._fp.tell() == self._file_size)
    
    def _xml_append_child(self, dom, root, xml_root):
        '''
        '''
        if xml_root == dom:
            node = dom.documentElement
            node.setAttribute('xmlns:%s' % self.ns_prefix, self.ns_uri)
        else:
            name = self._get_string(root['elem'].attr_ext.name_index)
            node = dom.createElement(name)
            xml_root.appendChild(node)

        for attr in root['attrs']:
            key = self._get_string(attr.name_index)
            if key in ['package', 'platformBuildVersionCode', 'platformBuildVersionName']:
                assert(attr.ns_index == 0xFFFFFFFF)
            res_id = EnumAttrType.get_value(key)
            val = attr.typed_value.format_value()
            if attr.typed_value.data_type == EnumResValueType.TYPE_STRING:
                val = self._get_string(val)
                if val.isdigit() or val == 'true' or val == 'false' or val.startswith('0x'): 
                    val = 'str(%s)' % val  # 保证类型正确
                assert(attr.raw_value == attr.typed_value.data)
            else:
                pass

            if attr.ns_index != 0xFFFFFFFF:
                assert(self._get_string(attr.ns_index) == self.ns_uri)
                key = self.ns_prefix + ':' + key
            node.setAttribute(key, val)
            node.setAttribute('line_number', str(root['elem'].line_number))
        for child in root['children']:
            self._xml_append_child(dom, child, node)
            
    def to_xml(self, save_path=None):
        '''转换为xml格式
        '''
        impl = xml.dom.minidom.getDOMImplementation()
        root = self._get_string(self.elements['elem'].attr_ext.name_index)

        dom = impl.createDocument('%s:%s' % (self.ns_prefix, self.ns_uri), root, None)
        self._xml_append_child(dom, self.elements, dom)
        if save_path:
            with open(save_path, 'wb') as fp:
                dom.writexml(fp, addindent=' ' * 4, newl='\n', encoding='utf-8')
        
        return dom
    
    def serialize(self):
        '''序列化
        '''
        body = self.string_pool_chunk.serialize()
        body += self.res_map_chunk.serialize()
        body += self.start_ns_chunk.serialize()
        for it in self.elem_chunk_list:
            body += it.serialize()
        body += self.end_ns_chunk.serialize()
        self.size = self.__class__.header_size + len(body)
        
        return self.serialize_header() + body
        
    def save(self, save_path):
        '''保存到文件
        '''
        with open(save_path, 'wb') as f:
            f.write(self.serialize())

    @staticmethod
    def from_xml(xml_text):
        '''根据xml文件生成AXMLFile对象
        '''
        if isinstance(xml_text, str):
            dom = xml.dom.minidom.parseString(xml_text)
        else:
            dom = xml_text
            
        obj = AXMLFile()
        
        obj.string_pool_chunk = ResStringPoolChunk()

        obj.string_offset_list = []
        obj.style_offset_list = []
        
        obj.res_map_chunk = ResXMLResourceMapChunk()
        
        for key, val in EnumAttrType.list():
            # 将这些字符串先存起来
            obj.string_pool_chunk.add_string(key)
            obj.res_map_chunk.res_map.append(val)
        
        def _get_string_index(s):
            if six.PY2 and not isinstance(s, unicode):
                s = s.decode('utf8')
            try:
                return obj.string_pool_chunk.string_list.index(s)
            except ValueError:
                obj.string_pool_chunk.add_string(s)
                return obj.string_pool_chunk.string_list.index(s)
        
        obj.ns_prefix = _get_string_index('android')
        obj.ns_uri = _get_string_index('http://schemas.android.com/apk/res/android')
        obj.start_ns_chunk = ResXMLStartNamespaceChunk()
        obj.start_ns_chunk.body.prefix_index = obj.ns_prefix
        obj.start_ns_chunk.body.uri_index = obj.ns_uri
        
        obj.end_ns_chunk = ResXMLEndNamespaceChunk()
        obj.end_ns_chunk.body.prefix_index = obj.start_ns_chunk.body.prefix_index
        obj.end_ns_chunk.body.uri_index = obj.start_ns_chunk.body.uri_index
        
        def _walk_dom_tree(dom_node):
            '''
            '''
            elem_chunk_list = []
            for node in dom_node.childNodes:
                if not hasattr(node, 'tagName'): continue
                node_name = node.tagName
                    
                start_elem_chunk = ResXMLStartElementChunk()
                start_elem_chunk.attr_ext = ResXMLTreeAttrExt()
                start_elem_chunk.attr_ext.name_index = _get_string_index(node_name)
                
                items = node.attributes.items()
                # 按照属性名在EnumAttrType中顺序排序
                items = sorted(items, key=lambda x: EnumAttrType.get_value(x[0].split(':')[-1]))
                        
                for name, val in items:
                    if name == 'line_number':
                        start_elem_chunk.line_number = int(val)
                        continue
                    attr = ResXMLTreeAttribute()
                    if name.startswith('xmlns:'):
                        continue
                    elif name.startswith(obj._get_string(obj.ns_prefix) + ':'):
                        name = name[len(obj._get_string(obj.ns_prefix)) + 1:]
                        attr.ns_index = obj.ns_uri
                    else:
                        attr.ns_index = 0xFFFFFFFF

                    attr.name_index = _get_string_index(name)
                    attr.typed_value = ResValue.convert_from(val)
                    if attr.typed_value.data_type == EnumResValueType.TYPE_STRING:
                        string_pattern = re.compile(r'^str\(.+\)$')
                        if string_pattern.match(val):
                            val = val[4:-1]
                        attr.typed_value.data = _get_string_index(val)
                        attr.raw_value = attr.typed_value.data
                    else:
                        attr.raw_value = 0xFFFFFFFF

                    start_elem_chunk.attrs.append(attr)
                
                    
                start_elem_chunk.attr_ext.attribute_count = len(start_elem_chunk.attrs)
                
                end_elem_chunk = ResXMLEndElementChunk()
                end_elem_chunk.body.ns_index = start_elem_chunk.attr_ext.ns_index
                end_elem_chunk.body.name_index = start_elem_chunk.attr_ext.name_index

                elem_chunk_list.append(start_elem_chunk)
                child_elem_node_list = _walk_dom_tree(node)
                elem_chunk_list.extend(child_elem_node_list)
                elem_chunk_list.append(end_elem_chunk)
                
            return elem_chunk_list
                
        obj.elem_chunk_list = _walk_dom_tree(dom)
        
        return obj
        
if __name__ == '__main__':
    pass
    
