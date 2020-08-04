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

'''clientsocket模块单元测试
'''

import threading
import json
import time
import random
import sys
import unittest

try:
    import socketserver
except ImportError:
    import SocketServer as socketserver

from qt4a.androiddriver.clientsocket import AndroidSpyClient

class AndroidSpyRequestHandler(socketserver.StreamRequestHandler):
    '''mock server
    '''
    
    def send_response(self, response):
        response = json.dumps(response, ensure_ascii=False)
        response = '%.8X%s' % (len(response), response)
        response = response.encode('utf8') + b'\n'
        slice_len = 1024
        offset = 0
        while offset < len(response):
            self.wfile.write(response[offset:offset + slice_len])
            self.wfile.flush()
            offset += slice_len
            #time.sleep(0.1)

    def handle(self):
        while True:
            line = self.rfile.readline()
            if sys.version_info[0] == 3 and isinstance(line, bytes):
                line = line.decode('utf8')
            request = json.loads(line)
            cmd = request['Cmd']
            if cmd == 'Hello':
                self.send_response(request)
            elif cmd == 'Exit':
                self.send_response(request)
                break
            elif cmd == 'Test':
                response = {'Cmd': cmd, 'Seq': request['Seq']}
                response['Result'] = u'中文结果测试' * 10000
                self.send_response(response)
        print('Server exit')

class TestAndroidSpyClient(unittest.TestCase):
    '''AndroidSpyClient类测试用例
    '''
    
    def _create_server(self, port):
        server = socketserver.TCPServer(('127.0.0.1', port), AndroidSpyRequestHandler)
        server.serve_forever()
    
    def _create_server_in_thread(self, port):
        t = threading.Thread(target=self._create_server, args=(port,))
        t.setDaemon(True)
        t.start()

    def test_send_command(self):
        port = random.randint(10000, 60000)
        self._create_server_in_thread(port)
        client = AndroidSpyClient(port)
        rsp = client.send_command('Hello')
        self.assertEqual(rsp['Cmd'], 'Hello')
        
        rsp = client.send_command('Test')
        self.assertEqual(len(rsp['Result']), 60000)

        client.send_command('Exit')

if __name__ == '__main__':
    unittest.main()