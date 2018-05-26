#!/usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import socket

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
    def __init__(self, conn, loop, config):
        self._conn = conn
        self._loop = loop
        self._config = config
        self._local_sock = conn[0]
        self._remote_sock = None
        self._stage = STAGE_INIT
        self._remote_server_addr = ()

        self._loop.add(self._local_sock, self)

    def handle_event(self, sock, event):
        if sock == self._local_sock:
            # 本地socks5
            self.on_local_read()
            return
        elif sock == self._remote_sock:
            # 远程服务器连接
            self.on_remote_read()
            return

    # 读取本地socks5的信息
    def on_local_read(self):
        if not self._local_sock:
            return
        data = None
        try:
            data = self._local_sock.recv(BUF_SIZE)
            if not data:
                return
        except(OSError, IOError) as e:
            print(e)
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
        # print(data.encode('hex'))
        # print(data)

    # 建立握手
    def handle_stage_init(self, data):
        if self.write_to_sock(b'\x05\00', self._local_sock):
            self._stage = STAGE_ADDR

    # 解析ip和port
    def parse_addr(self, data):
        ip = data[2:16]
        port = ord(data[17:])
        result = (ip, port)
        return result

    # 创建远程连接
    def create_remote_sock(self, server_addr):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(server_addr)
        return sock

    # 与remote_sock连接
    def handle_stage_addr(self, data):
        # cmd = int(data[1])
        cmd = data[1]
        cmd = ord(cmd) #string转int
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
        self._loop.add(self._remote_sock, self)
        self._stage = STAGE_CONNECTING
        self.write_to_sock(b'\x05\x00\x00\x01'
                           b'\x00\x00\x00\x00\x10\x10', self._local_sock)

    # 已经连接上，转发信息
    def handle_stage_connecting(self, data):
        self.write_to_sock(data, self._remote_sock)

    # 发送
    def write_to_sock(self, data, sock):
        sock.send(data)
        return True

    def on_remote_read(self):
        if not self._remote_sock:
            return
        data = self._remote_sock.recv(BUF_SIZE)
        print(data)
        self.write_to_sock(data, self._local_sock)
