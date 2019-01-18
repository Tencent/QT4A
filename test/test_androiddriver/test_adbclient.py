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

'''adbclient模块单元测试
'''

import random
import select
import socket
import struct
import tempfile
import time
import threading
import unittest
try:
    from unittest import mock
except:
    import mock

from qt4a.androiddriver.adbclient import ADBClient

class Context(object):
    '''上下文
    '''
    
    def __init__(self):
        self._device_id = None
        self._file_path = None
        
    @property
    def device_id(self):
        return self._device_id
        
    @device_id.setter
    def device_id(self, id):
        self._device_id = id
    
    @property
    def file_path(self):
        return self._file_path
    
    @file_path.setter
    def file_path(self, path):
        self._file_path = path
    
class MockADBServer(object):
    '''mock adb server
    '''
    
    def __init__(self, port=5037):
        self._port = port
        self._serv = socket.socket()
        self._serv.bind(('127.0.0.1', self._port))
        self._serv.listen(1)
        self._running = True
        t = threading.Thread(target=self.run)
        t.setDaemon(True)
        t.start()
    
    def stop(self):
        self._running = False
        self._serv.close()
        time.sleep(1)
        
    def run(self):
        context_dict = {}
        fds = [self._serv]
        while self._running:
            infds, outfds, errfds = select.select(fds, [], [], 1)
            if len(infds) > 0:
                for fd in infds:
                    if fd == self._serv:
                        try:
                            sock, _ = fd.accept()
                        except:
                            continue
                        else:
                            fds.append(sock)
                            context_dict[sock] = Context()
                    else:
                        try:
                            data = fd.recv(4096)
                        except:
                            fd.close()
                            fds.remove(fd)
                        else:
                            if not data:
                                fd.close()
                                fds.remove(fd)
                            else:
                                response, close_conn = self.handle_input(context_dict[fd], data)
                                if response: fd.send(response)
                                if close_conn: 
                                    fd.close()
                                    fds.remove(fd)
                                    context_dict.pop(fd)
    
    def handle_input(self, context, data):
        '''处理输入数据
        '''
        try:
            data_len = int(data[:4], 16)
        except ValueError:
            pass
        else:
            assert(len(data) == data_len + 4)
            data = data[4:4 + data_len]

        response = b'OKAY'
        close_conn = False
        if data == b'host:devices':
            data = b'127.0.0.1:21369\tdevice'
            response += b'%04x%s' % (len(data), data)
            close_conn = True
        elif data.startswith(b'host:transport:'):
            device_id = data[15:]
            context.device_id = device_id
        elif data.startswith(b'host-serial:'):
            pos = data.find(b':forward:')
            if pos > 0:
                data = data[pos + 9:]
                local, remote = data.split(b';')
            pos = data.find(b':get-state')
            if pos > 0:
                response += b'0006device'
            close_conn = True
        elif data.startswith(b'host:connect:'):
            data = data[13:]
            data = b'connected to %s' % data
            response += b'%04x%s' % (len(data), data)
            close_conn = True
        elif data.startswith(b'host:disconnect:'):
            data = b'disconnected'
            response += b'%04x%s' % (len(data), data)
            close_conn = True
        elif data.startswith(b'shell:'):
            cmdline = data[6:]
            if cmdline == b'id':
                response += b'uid=0(root) gid=0(root) groups=1003(graphics),1004(input),1007(log),1011(adb),1015(sdcard_rw),1028(sdcard_r),3001(net_bt_admin),3002(net_bt),3003(inet),3006(net_bw_stats) context=kernel'
            elif cmdline.startswith(b'echo'):
                response += b'\r\n'
            elif cmdline.startswith(b'pm '):
                response += b'Failure'
            else:
                raise NotImplementedError(cmdline)
            close_conn = True
        elif data == b'sync:':
            pass
        elif data.startswith(b'STAT'):
            data_len = struct.unpack('I', data[4:8])[0]
            assert(len(data) == data_len + 8)
            file_path = data[8:]
            context.file_path = file_path
            response = b'STAT\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        elif data.startswith(b'SEND'):
            data_len = struct.unpack('I', data[4:8])[0]
            assert(len(data) == data_len + 8)
            response = b''
        elif data.startswith(b'DATA'):
            data = data[-8:-4]
            if data == b'DONE':
                response += b'\x00\x00\x00\x00'
                close_conn = True
            else:
                response = b''
        elif data.startswith(b'RECV'):
            response = b'DATA\x04\x00\x00\x001234'
            response += b'DONE\x00\x00\x00\x00'
        elif data.startswith(b'DONE'):
            response += b'\x00\x00\x00\x00'
            close_conn = True
        elif data.startswith(b'QUIT'):
            response = b''
            close_conn = True
        elif data == b'framebuffer:':
            pass
        else:
            print(repr(data))
            raise
        return response, close_conn
        

class TestADBClient(unittest.TestCase):
    '''ADBClient类测试用例
    '''

    def setUp(self):
        self._port = random.randint(10000, 60000)
        self._mock_server = MockADBServer(self._port)
        
    def tearDown(self):
        self._mock_server.stop()
        
    def get_client(self):
        return ADBClient.get_client('127.0.0.1', self._port)
    
    def get_device_name(self):
        return '127.0.0.1:21369'

    def test_devices(self):
        client = self.get_client()
        result = client.devices()
        self.assertIn('127.0.0.1:21369\tdevice', result)

    def test_shell(self):
        client = self.get_client()
        stdout, stderr = client.shell(self.get_device_name(), 'id', timeout=10)
        self.assertIn(b'uid=0(root)', stdout)
        self.assertEqual(stderr, b'')
     
    def test_push(self):
        client = self.get_client()
        file_path = tempfile.mktemp('.txt')
        text = '1' * 1024
        with open(file_path, 'w') as fp:
            fp.write(text)
        result = client.push(self.get_device_name(), file_path, '/data/local/tmp/1.txt')
        self.assertIn('1024 bytes in', result)
  
    def test_pull(self):
        client = self.get_client()
        file_path = tempfile.mktemp('.txt')
        client.shell(self.get_device_name(), 'echo 1234 > /data/local/tmp/1.txt', timeout=10)
        client.pull(self.get_device_name(), '/data/local/tmp/1.txt', file_path)
        with open(file_path, 'r') as fp:
            text = fp.read()
            self.assertEqual(text.strip(), '1234')
        
    def test_uninstall(self):
        client = self.get_client()
        result = client.uninstall(self.get_device_name(), 'com.tencent.demo', timeout=20)
        self.assertIn('Failure', result)
    
    def test_forward(self):
        client = self.get_client()
        result = client.forward(self.get_device_name(), 'tcp:12345', 'tcp:12345')
        self.assertEqual(result, '')

    def test_remove_forward(self):
        client = self.get_client()
        client.forward(self.get_device_name(), 'tcp:12345', 'tcp:12345')
        result = client.remove_forward(self.get_device_name(), 'tcp:12345')
        self.assertEqual(result, '')
 
    def test_get_state(self):
        client = self.get_client()
        result = client.get_state(self.get_device_name())
        self.assertEqual(result, 'device')
       
    def test_connect(self):
        client = self.get_client()
        result = client.connect('127.0.0.1:12345')
        self.assertEqual(result, True)
        running = False
        
    def test_disconnect(self):
        client = self.get_client()
        result = client.disconnect('127.0.0.1:12345')
        self.assertEqual(result, True)
 
    #def test_snapshot_screen(self):
    #    from PIL import Image
    #    client = self.get_client()
    #    result = client.snapshot_screen(self.get_device_name())
    #    self.assertIsInstance(result, Image.Image)
 
if __name__ == '__main__':
    unittest.main()
