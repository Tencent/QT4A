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

'''客户端Socket连接
'''

from __future__ import unicode_literals

import json
import six
import socket
import select
import time
import threading
from qt4a.androiddriver.util import logger, time_clock

def is_tcp_server_opened(addr, port):
    '''判断TCP服务是否连接正常
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((addr, port))
        sock.close()
        return True
    except socket.error:
        return False


class TCPSocketClient(object):
    '''TCPSocket客户端
    '''
    def __init__(self, addr, port, timeout=60):
        self._sock = None
        self._addr = addr
        self._port = port
        self._connect = False
        self._timeout = timeout

    @staticmethod
    def server_opened(port, addr='127.0.0.1'):
        '''判断服务是否已经打开
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((addr, port))
            sock.send(b'{"Cmd":"Hello","Seq":1}\n')  # 有时connect会成功，但是send才会发现失败
            sock.recv(4096)
            return True
        except socket.error as e:
            logger.debug('server_opened (%s, %s) %s' % (addr, port, e))
            if e.args[0] == 10035: return True
            return False

    def pre_connect(self, timeout=5):
        '''预连接，adb forward调用后不能保证连接一定可用
        '''
        time0 = time.time()
        while time.time() - time0 < timeout:
            try:
                if self.hello() != None:
                    return True
            except socket.error as e:
                # logger.warn(e)
                time.sleep(0.5)  # 尝试频率没必要太频繁
        raise RuntimeError('Socket连接失败')

    def hello(self):
        return self.send('Hello')

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # socket.setdefaulttimeout(120)
        for i in range(3):
            try:
                self._sock.connect((self._addr, self._port))
                self._sock.settimeout(self._timeout)
                self._connect = True
                return True
            except Exception as e:
                logger.warn('connect (%s, %s) error: %s' % (self._addr, self._port, e))
                if i == 2: return False  # 连接失败
                time.sleep(1)

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None
    
    def recv(self, buff_size):
        return self._sock.recv(buff_size)
        
    def send(self, data):
        if not self._connect:
            if not self.connect(): return None
        try:
            self._sock.send(data.encode('utf8'))
        except socket.error as e:
            logger.info('发送%r错误： %s' % (data, e))
            self._sock.close()
            self._connect = False
            return None
        
        expect_len = self.recv(8)
        if not expect_len: return None

        expect_len = int(expect_len, 16) + 1
        recv_buff = ''
        max_utf8_length = 6

        while len(recv_buff) < expect_len:
            buff = self.recv(expect_len - len(recv_buff))

            if not buff:
                logger.warn('Socket closed when recv rsp for %r' % data)
            
            while True:
                try:
                    recv_buff += buff.decode('utf8')
                    break
                except UnicodeDecodeError:
                    if len(buff) > max_utf8_length:
                        for i in range(max_utf8_length):
                            this_buff = buff[:i - max_utf8_length]
                            try:
                                recv_buff += this_buff.decode('utf8')
                            except UnicodeDecodeError:
                                pass
                            else:
                                buff = buff[i - max_utf8_length:]
                                break
                        else:
                            raise RuntimeError('Invalid utf-8 bytes: %r' % buff)
                    buff += self.recv(1)

        return recv_buff

class AndroidSpyClient(TCPSocketClient):
    '''AndroidSpy客户端
    '''
    def __init__(self, port, addr='127.0.0.1', enable_log=True, timeout=20):
        super(AndroidSpyClient, self).__init__(addr, port, timeout)
        self._seq = 0
        self._enable_log = enable_log
        self._lock = threading.Lock()  # TODO: 多线程互斥

    @property
    def seq(self):
        self._seq += 1
        return self._seq

    def send_command(self, cmd_type, **kwds):
        '''send command
        '''
        packet = {}
        packet['Cmd'] = cmd_type
        packet['Seq'] = self.seq
        for key in kwds.keys():
            packet[key] = kwds[key]
        data = json.dumps(packet) + "\n"
        if six.PY2 and isinstance(data, unicode):
            data = data.encode('utf8')

        time0 = time_clock()
        self._lock.acquire()
        time1 = time_clock()
        delta = time1 - time0
        if self._enable_log and delta >= 0.05: logger.info('send wait %s S' % delta)
        if self._enable_log: logger.debug('send: %s' % (data[:512].strip()))

        time0 = time_clock()
        try:
            result = self.send(data)
        except Exception as e:
            # 避免因异常导致死锁
            logger.exception('send %r error: %s' % (data, e))
            result = None
        self._lock.release()  # 解锁
        if not result: return None

        time1 = time_clock()
        try:
            rsp = json.loads(result)
        except:
            logger.error('json error: %r' % (result))
            raise
        else:
            if self._enable_log: 
                delta = int(1000 * (time1 - time0))
                if 'HandleTime' in rsp: delta -= rsp['HandleTime']
                logger.debug('recv: [%d]%s\n' % (delta, result[:512].strip()))
            return rsp
        
    def hello(self):
        return self.send_command('Hello')

class DirectAndroidSpyClient(AndroidSpyClient):
    '''走直连方式的AndroidSpy客户端
    '''
    def __init__(self, sock, enable_log=True, timeout=20):
        super(DirectAndroidSpyClient, self).__init__(0, enable_log=enable_log, timeout=timeout)
        self._sock = sock
        self._connect = True
    
    def recv(self, buff_size):
        time0 = time.time()
        while time.time() - time0 < self._timeout:
            try:
                ret = self._sock.recv(buff_size)
                if ret != None: return ret
            except socket.timeout:
                pass

            time.sleep(0.001)
            continue

        raise socket.timeout('recv data timeout')
                

if __name__ == '__main__':
    pass

