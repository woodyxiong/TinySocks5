#!/usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import absolute_import

import errno
import socket
import logging
import eventloop

# select doc https://pymotw.com/3/select/

BUF_SIZE = 32 * 1024

STAGE_INIT = 0  # 收到客户端的连接
STAGE_CONNECTED_REMOTE = 1  # 连接socks5服务端
STAGE_SEND_HELLO_TO_REMOTE = 2  # 客户端-》服务端 050100
STAGE_RECEIVE_HELLO_FROM_REMOTE = 3  # 已连接上 服务端-》客户端 0500
STAGE_SEND_REQUEST_ADDR = 4  # 已发送需要连接的地址
STAGE_CONNECTED = 5  # 已连接上
STAGE_DESTROYED = -1

SOCKS5_SERVER_IP = '172.18.12.70'
SOCKS5_SERVER_PORT = 10080
MYSQL_IP = '10.104.20.42'
MYSQL_PORT = 3306

# SOCKS5_SERVER_IP = '49.234.85.242'
# SOCKS5_SERVER_PORT = 6666
# MYSQL_IP = '127.0.0.1'
# MYSQL_PORT = 3306

MSG_FASTOPEN = 0x20000000

WAIT_STATUS_INIT = 0
WAIT_STATUS_READING = 1
WAIT_STATUS_WRITING = 2
WAIT_STATUS_READWRITING = WAIT_STATUS_READING | WAIT_STATUS_WRITING

STREAM_UP = 0
STREAM_DOWN = 1


# 1. 客户端-》服务端 050100
# 2. 服务端-》客户端 0500

class Tcprelay(object):
    def __init__(self, server, conn, loop, config, fd_to_handlers):
        self._loop = loop
        self._config = config
        self._local_sock = conn[0]
        self._remote_server_addr = None
        self._server = server
        self._stage = STAGE_INIT
        self._fd_to_handlers = fd_to_handlers
        self._data_to_write_to_local = []
        self._data_to_write_to_remote = []
        self._downstream_status = WAIT_STATUS_INIT
        self._upstream_status = WAIT_STATUS_READING

        self._local_sock.setblocking(False)

        self._loop.add(self._local_sock, eventloop.POLL_IN | eventloop.POLL_ERR, self)
        self._fd_to_handlers[conn[0].fileno()] = self

        addr = (SOCKS5_SERVER_IP, SOCKS5_SERVER_PORT)
        self._remote_sock = self.create_remote_sock(addr)
        if self._remote_sock:
            self._loop.add(self._remote_sock, eventloop.POLL_OUT | eventloop.POLL_ERR, self)
            self._fd_to_handlers[self._remote_sock.fileno()] = self
        else:
            logging.warning("连接remote_sock失败")
            self.destroy()

    def handle_event(self, sock, event):
        if event == eventloop.POLL_ERR:
            # 连接失败
            logging.info("连接失败")
            self.destroy()
            return
        elif event == eventloop.POLL_IN:
            if (sock == self._local_sock) & (self._stage == WAIT_STATUS_INIT):
                print("初始化连接，讲道理应该不会到这里")
                return
            if sock == self._local_sock:
                # 本地socks5
                self.on_local_read()
                return
            elif sock == self._remote_sock:
                # 远程服务器连接
                self.on_remote_read()
                return
        elif event == eventloop.POLL_OUT:
            if self._stage == WAIT_STATUS_INIT:
                # 远程连接成功
                self.on_handle_init_remote_connected(sock)
                return
            else:
                # 消息未一次性发送成功的
                self.write_to_sock(b'',sock)
        else:
            logging.warning("tcprelay接收不相关的socket" + str(sock.fileno()))
            self.destroy()

    def on_handle_init_remote_connected(self, sock):
        """
        :param sock:
        :return:
        """
        self._loop.clear_w(sock.fileno())
        self._stage = STAGE_CONNECTED_REMOTE
        self._loop.add(self._remote_sock, eventloop.POLL_IN, self)
        logging.info("连接remote_sock成功")
        if self.write_to_sock(b'\x05\x01\x00', self._remote_sock):
            self._stage = STAGE_SEND_HELLO_TO_REMOTE
            return
        else:
            logging.warning("远程发送hello失败")
            self.destroy()

    # 读取本地信息
    def on_local_read(self):
        data = None
        try:
            data = self._local_sock.recv(BUF_SIZE)
            if not data:
                # 本地断开连接
                self.destroy()
                return
        except(OSError, IOError) as e:
            logging.warning("接收数据时发生错误")
            self.destroy()
            return
        if self._stage == STAGE_CONNECTED:
            self.handle_stage_connecting(data)
            return
        else:
            logging.warning("tcprelay的_stage状态值异常" + str(self._stage))
        # print(data)
        # print(str(data))

    # 创建远程连接
    def create_remote_sock(self, server_addr):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        try:
            sock.connect_ex(server_addr)
        except Exception as e:
            logging.info("远程连接地址失败" + str(server_addr) + "Excption:" + str(e))
            # self.destroy()
        return sock

    # 已经连接上，转发信息
    def handle_stage_connecting(self, data):
        if not self.write_to_sock(data, self._remote_sock):
            logging.warning("未转发完成")

    # 发送
    def write_to_sock(self, data, sock):
        if sock == self._local_sock:
            if self._data_to_write_to_local:
                self._data_to_write_to_local.append(data)
                # data = b''.join(self._data_to_write_to_local)
                # self._data_to_write_to_local = []
                return False
        elif sock == self._remote_sock:
            if self._data_to_write_to_remote:
                self._data_to_write_to_remote.append(data)
                # data = b''.join(self._data_to_write_to_remote)
                # self._data_to_write_to_remote = []
                return False

        incomplete = False
        try:
            data_length = len(data)
            send_length = sock.send(data)
            data = data[send_length:]
            if send_length == data_length:
                self._loop.clear_w(sock.fileno())
                logging.info("发送成功，fileno:"+str(sock.fileno()))
                return True
            else:
                logging.warning("未一次性发送完全")
                incomplete = True
        except (OSError, IOError) as e:
            error_no = eventloop.errno_from_exception(e)
            if error_no in (errno.EAGAIN, errno.EINPROGRESS,
                            errno.EWOULDBLOCK):
                incomplete = True
            else:
                if sock == self._remote_sock:
                    logging.warning("发送远端失败" + str(e))
                else:
                    logging.warning("发送本地失败" + str(e))
                self.destroy()
                return False
        if incomplete:
            logging.warning("发送失败，fileno:"+str(sock.fileno()))
            if sock == self._local_sock:
                self._data_to_write_to_local.append(data)
                self._loop.add(self._local_sock, eventloop.POLL_OUT, self)
                # self._update_stream(STREAM_DOWN, WAIT_STATUS_WRITING)
            elif sock == self._remote_sock:
                self._data_to_write_to_remote.append(data)
                self._loop.add(self._remote_sock, eventloop.POLL_OUT, self)
                # self._update_stream(STREAM_UP, WAIT_STATUS_WRITING)
            else:
                logging.error('write_all_to_sock:unknown socket')
        # else:
        #     if sock == self._local_sock:
        #         self._update_stream(STREAM_DOWN, WAIT_STATUS_READING)
        #     elif sock == self._remote_sock:
        #         self._update_stream(STREAM_UP, WAIT_STATUS_READING)
        #     else:
        #         logging.error('write_all_to_sock:unknown socket')
        return False

    def _update_stream(self, stream, status):
        # update a stream to a new waiting status

        # check if status is changed
        # only update if dirty
        dirty = False
        if stream == STREAM_DOWN:
            if self._downstream_status != status:
                self._downstream_status = status
                dirty = True
        elif stream == STREAM_UP:
            if self._upstream_status != status:
                self._upstream_status = status
                dirty = True
        if not dirty:
            return

        if self._local_sock:
            event = eventloop.POLL_ERR
            if self._downstream_status & WAIT_STATUS_WRITING:
                event |= eventloop.POLL_OUT
            if self._upstream_status & WAIT_STATUS_READING:
                event |= eventloop.POLL_IN
            # self._loop.modify(self._local_sock, event)
        if self._remote_sock:
            event = eventloop.POLL_ERR
            if self._downstream_status & WAIT_STATUS_READING:
                event |= eventloop.POLL_IN
            if self._upstream_status & WAIT_STATUS_WRITING:
                event |= eventloop.POLL_OUT
            # self._loop.modify(self._remote_sock, event)

    # 接收到remote发送的信息
    def on_remote_read(self):
        if not self._remote_sock:
            logging.warning("remote_sock为空")
            return
        data = None
        try:
            data = self._remote_sock.recv(BUF_SIZE)
        except Exception as e:
            logging.warning("接收remote_sock失败" + str(e))
        if data:
            if self._stage == STAGE_SEND_HELLO_TO_REMOTE:
                self.on_receive_remote_hello(data)
                return
            if self._stage == STAGE_SEND_REQUEST_ADDR:
                self.on_judge_connected(data)
                return
            if self._stage == STAGE_CONNECTED:
                if not self.write_to_sock(data, self._local_sock):
                    logging.warning("STAGE_CONNECTED发送失败了")
                return

        else:
            # remote 断开连接
            self.destroy()

    def on_judge_connected(self, data):
        if len(data) < 2:
            logging.error("socks连接数据库失败")
            self.destroy()
            return
        if bytes(data[1]) != b'':
            logging.error("socks连接数据库失败")
            self.destroy()
            return
        self._stage = STAGE_CONNECTED
        if len(data) > 10:
            first_content_bytes = data[10:]
            self.write_to_sock(first_content_bytes, self._local_sock)

    def on_receive_remote_hello(self, data):
        if data != b'\x05\x00':
            logging.warning("非标准的socks5握手data=" + str(data))
            self.destroy()
            return
        self._stage = STAGE_RECEIVE_HELLO_FROM_REMOTE
        mysql_ip = MYSQL_IP
        mysql_port = MYSQL_PORT
        output = b'\x05\x01\x00\x01' \
                 + bytes(map(int, mysql_ip.split('.'))) \
                 + mysql_port.to_bytes(2, byteorder='big')

        if self.write_to_sock(output, self._remote_sock):
            self._stage = STAGE_SEND_REQUEST_ADDR
        else:
            logging.warning("STAGE_RECEIVE_HELLO_FROM_REMOTE失败了")

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
            self._local_sock = None
