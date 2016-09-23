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

'''
维护客户端Socket连接
'''

import sys, os
import socket
import select
import time
import threading
from util import logger, CrossThreadException

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
      
class SocketBase(object):
    '''Socket基类，接口层
    '''

    def __init__(self, socket_handler=None):
        self._running = True
        self._socket_handler = socket_handler  # 回调类
        self._timer = None
        self._reconnect = False  # 重连标记
        self._server_addr = None

    @property
    def server_addr(self):
        return self._server_addr

    @property
    def timer(self):
        return self._timer

    @timer.setter
    def timer(self, _timer):
        self._timer = _timer

    @property
    def reconnect(self):
        return self._reconnect

    @reconnect.setter
    def reconnect(self, value):
        if value == True and self._reconnect == True:
            # 重登录过程中发生断开
            raise RuntimeError('重登录过程中发生断开')
        self._reconnect = value

    def stop(self):
        self._running = False

    def work_thread(self):
        pass
        if self._timer:  # 起消息循环作用
            self._timer.rotate()

    def on_recv(self, data):
        '''收到返回数据的回调
        '''
        if self._socket_handler:
            self._socket_handler.on_recv(data)

    def on_send(self, data):
        '''发送出数据的回调
        '''
        if self._socket_handler:
            self._socket_handler.on_send(data)


class QQTCPSocket(SocketBase):
    def __init__(self, addr, port, qq_handler=None):
        super(QQTCPSocket, self).__init__(qq_handler)
        self._sock = None
        self._addr = addr
        self._port = port
        self._connect = False

    @staticmethod
    def server_opened(port):
        '''判断服务是否已经打开
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(('127.0.0.1', port))
            sock.send('Hello')  # 有时connect会成功，但是send才会发现失败
            infds, outfds, errfds = select.select([sock, ], [], [], 1)
            if len(infds) > 0:
                try:
                    buf = infds[0].recv(4096 * 4)  # 8196
                except socket.error, e:
                    print e
                    return False
            sock.close()
            return True
        except socket.error, e:
            print e
            if e.args[0] == 10035: return True
            return False

    def connect(self):
        logger.debug('Connect to %s:%d' % (self._addr, self._port))
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for i in range(3):  # 尝试连接3次，重试间隔时间为5秒
            try:
                self._sock.connect((self._addr, self._port))
                logger.debug('Connect Success')
                self._connect = True
                break
            except socket.error:
                if i == 2:
                    raise RuntimeError('连接服务端 %s:%d 失败' % (self._addr, self._port))
                time.sleep(5)
        self._server_addr = (self._addr, self._port)
        self._sock.setblocking(0)  # 设为非阻塞
        t = threading.Thread(target=self.work_thread)
        t.setDaemon(True)
        t.start()

    def work_thread(self):
        '''工作线程
        '''
        while self._running:
            infds, outfds, errfds = select.select([self._sock, ], [], [], 1)
            # 如果infds状态改变,进行处理,否则不予理会
            # print infds,outfds,errfds
            if len(infds) > 0:
                try:
                    buf = infds[0].recv(4096 * 4)  # 8196
                except socket.error, e:
                    logger.error('Scoket Error: %s' % e)
                    CrossThreadException.instance().exception = sys.exc_info()
                    self._connect = False
                    return

                if len(buf) > 0:
#                    self.on_recv(buf)
                    try:
                        self.on_recv(buf)
                    except Exception, e:
                        CrossThreadException.instance().exception = sys.exc_info()
                        logger.warn('Exception on Socket Thread：%s' % e)
                        if self._running:
                            import traceback
                            for line in traceback.format_exception(*sys.exc_info()):
                                print >> sys.stderr, line,
                        # time.sleep(0.2)  # 等待主线程捕获异常
                        break
                else:
                    # 连接关闭
                    # logger.error('TCP连接被关闭')
                    if self._running:
                        raise RuntimeError('TCP连接被关闭')
                    self._connect = False
                    return
            super(QQTCPSocket, self).work_thread()
        self._sock.close()
        self._sock = None

    def on_recv(self, data):
        '''收到数据的回调
        '''
        # logger.debug('recv data:\n' + repr(data))
        super(QQTCPSocket, self).on_recv(data)

    def send(self, data):
        '''发送数据
        '''
        if not self._connect:
            self.connect()
        self.on_send(data)
        # logger.debug('send data:\n' + repr(data))
        return self._sock.send(data)


class TCPSocketClient(object):
    '''TCPSocket客户端
    '''
    def __init__(self, addr, port, timeout=20):
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
            sock.send('Hello')  # 有时connect会成功，但是send才会发现失败
            time.sleep(0.4)
            sock.send('Hello')
            return True
        except socket.error, e:
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
            except socket.error, e:
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
                self._connect = True
                return True
            except Exception, e:
                logger.warn('connect (%s, %s) error: %s' % (self._addr, self._port, e))
                if i == 2: return False  # 连接失败
                time.sleep(1)

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def send(self, data):
        if not self._connect:
            if not self.connect(): return None
        try:
            self._sock.send(data)
        except socket.error, e:
            logger.info('发送%r错误： %s' % (data, e))
            self._sock.close()
            self._connect = False
            return None
        recv_buff = ''
        expect_len = 0
        decode_flag = True  # 解码成功标记
        while expect_len == 0 or decode_flag == False or len(recv_buff) < expect_len:
            infds, outfds, errfds = select.select([self._sock, ], [], [], self._timeout)
            if len(infds) > 0:
                try:
                    buff = self._sock.recv(4096 * 4)
                except socket.error, e:
                    logger.info("接收%r返回数据错误： %s" % (data, e))
#                    import traceback
#                    traceback.print_exc()
                    self._sock.close()
                    self._connect = False
                    return None
                if len(buff) == 0: break

                if expect_len == 0:
                    expect_len = int(buff[:8], 16)
                    recv_buff = buff[8:]
                else:
                    if isinstance(recv_buff, unicode):
                        # 为防止合并字符串时返回解码错误
                        recv_buff = recv_buff.encode('utf8')
                    recv_buff += buff
                try:
                    recv_buff = recv_buff.decode('utf8')
                    decode_flag = True
                except UnicodeDecodeError:
                    # print 'decode error'
                    decode_flag = False
                    pass

            else:
                logger.error('读取%r返回数据超时' % data)
                return None
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
        '''
        '''
        import json
        packet = {}
        packet['Cmd'] = cmd_type
        packet['Seq'] = self.seq
        for key in kwds.keys():
            packet[key] = kwds[key]
        data = json.dumps(packet) + "\n"
        if isinstance(data, unicode):
            data = data.encode('utf8')

#        while not self._lock.acquire(False): #加锁
#            logger.warn('%s 延时发送: %s' % (time.clock(), data))
#            time.sleep(0.1)
        time0 = time.time()
        self._lock.acquire()
        time1 = time.time()
        delta = time1 - time0
        if self._enable_log and delta >= 0.05: logger.info('send wait %s S' % delta)
        if self._enable_log: logger.debug('send: %s' % (data[:512]))
        try:
            result = self.send(data)
        except Exception, e:
            # 避免因异常导致死锁
            logger.error('send %r error: %s' % (data, e))
            result = None
        self._lock.release()  # 解锁
        if not result: return None
        if self._enable_log: logger.debug('recv: %s' % (result[:512]))
        try:
            return json.loads(result)
        except Exception, e:
            logger.error('parse json (%r)error: %s' % (result, e))
            raise e

    def hello(self):
        return self.send_command('Hello')

if __name__ == '__main__':
    pass
    
