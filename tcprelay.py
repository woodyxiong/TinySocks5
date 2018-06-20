#!/usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import socket
import logging
import time

BUF_SIZE = 32 * 1024

STAGE_INIT = 0
STAGE_ADDR = 1
STAGE_UDP_ASSOC = 2
STAGE_DNS = 3
STAGE_CONNECTING = 4
STAGE_STREAM = 5
STAGE_DESTROYED = -1

# SOCKS command definition
CMD_CONNECT = 1
CMD_BIND = 2
CMD_UDP_ASSOCIATE = 3


class Tcprelay(object):
    def __init__(self, server, conn, loop, config, fd_to_handlers):
        self._loop = loop
        self._config = config
        self._local_sock = conn[0]
        self._remote_sock = None
        self._remote_server_addr = None
        self._server = server
        self._stage = STAGE_INIT
        self._fd_to_handlers = fd_to_handlers

        self._local_sock.setblocking(False)

        self._loop.add(self._local_sock, self)
        self._fd_to_handlers[conn[0].fileno()] = self

        self._loop.clear_we(self._local_sock.fileno())

    def handle_event(self, sock, event):
        if event == 2:
            # 远程连接成功
            self._loop._impl.clear_we_list(sock.fileno())
            self.write_to_sock(b'\x05\x00\x00\x01'
                               b'\x00\x00\x00\x00\x10\x10', self._local_sock)
            return
        elif event == 3:
            # 远程连接失败
            self.destroy()
            return
        if sock == self._local_sock:
            # 本地socks5
            self.on_local_read()
            return
        elif sock == self._remote_sock:
            # 远程服务器连接
            self.on_remote_read()
            return
        else:
            logging.warning("tcprelay接收不相关的socket"+str(sock.fileno()))
            self.destroy()

    # 读取本地socks5的信息
    def on_local_read(self):
        if not self._local_sock:
            return
        data = None
        try:
            data = self._local_sock.recv(BUF_SIZE)
            if not data:
                # 本地断开连接
                self.destroy()
                return
        except(OSError, IOError) as e:
            logging.warning("接收数据时发生错误")
        if self._stage == STAGE_INIT:
            # 建立握手
            self.handle_stage_init(data)
            return
        if self._stage == STAGE_ADDR:
            # 与remote_sock连接
            self.handle_stage_addr(data)
            return
        if self._stage == STAGE_CONNECTING:
            self.handle_stage_connecting(data)
            return
        else:
            logging.warning("tcprelay的_stage状态值异常"+str(self._stage))
        # print(data)
        # print(str(data))

    # 建立握手
    def handle_stage_init(self, data):
        if data != b'\x05\x01\x00':
            logging.warning("非标准的socks5握手data="+str(data))
            self.destroy()
        if self.write_to_sock(b'\x05\00', self._local_sock):
            self._stage = STAGE_ADDR

    # 解析ip/域名和port
    def parse_addr(self, data):
        try:
            length = data[1]
            addr = data[2:length+2]
            if len(data[length+2:]) == 2:
                port = ord(data[length+2:length+3])*256+ord(data[length+3:])
                result = (addr, port)
                return result
            else:
                logging.warning("解析地址出错,地址加端口:"+str(data[1:]))
                self.destroy()
        except:
            logging.warning("解析地址出错,地址加端口:"+str(data[1:]))
            self.destroy()

    # 创建远程连接
    def create_remote_sock(self, server_addr):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        try:
            sock.connect_ex(server_addr)
        except Exception as e:
            logging.info("远程连接地址失败"+str(server_addr)+"Excption:"+str(e))
            # self.destroy()
        return sock

    # 与remote_sock连接
    def handle_stage_addr(self, data):
        if not data:
            self.destroy()
            return
        if len(data) < 6:
            logging.warning("连接阶段非标准socks,data="+str(data))
        cmd = data[1]
        if cmd == CMD_CONNECT:
            # TCP连接
            data = data[3:]
        elif cmd == CMD_BIND:
            pass
        elif cmd == CMD_UDP_ASSOCIATE:
            # UDP连接
            pass
        header_result = self.parse_addr(data)
        self._remote_server_addr = header_result
        self._remote_sock = self.create_remote_sock(header_result)
        if self._remote_sock:
            self._loop.add(self._remote_sock, self)
            self._stage = STAGE_CONNECTING
            self._fd_to_handlers[self._remote_sock.fileno()] = self
        else:
            logging.warning("连接remote_sock失败")
            self.destroy()

    # 已经连接上，转发信息
    def handle_stage_connecting(self, data):
        if data:
            self.write_to_sock(data, self._remote_sock)
        else:
            logging.warning("转发给remote_sock失败")
            self.destroy()

    # 发送
    def write_to_sock(self, data, sock):
        try:
            data_length = len(data)
            send_length = sock.send(data)
            if send_length < data_length:
                logging.warning("未一次性发送完全")
            return True
        except Exception as e:
            logging.warning("发送失败"+str(e))
            return False

    # 接收到remote发送的信息
    def on_remote_read(self):
        if not self._remote_sock:
            logging.warning("remote_sock为空")
            return
        data = None
        try:
            data = self._remote_sock.recv(BUF_SIZE)
        except Exception as e:
            logging.warning("接收remote_sock失败"+str(e))
        if data:
            # 转发
            self.write_to_sock(data, self._local_sock)
        else:
            # remote 断开连接
            self.destroy()

    # 关闭连接，并销毁
    def destroy(self):
        if self._remote_sock:
            del self._fd_to_handlers[self._remote_sock.fileno()]
            self._loop.remove(self._remote_sock, self)
            self._remote_sock.close()
            self._remote_sock = None
        if self._local_sock:
            del self._fd_to_handlers[self._local_sock.fileno()]
            self._loop.remove(self._local_sock, self)
            self._local_sock.close()
            self._local_sock =None


