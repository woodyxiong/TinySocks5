#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import
import socket

import eventloop
from tcprelay import Tcprelay


class Controller(object):
    def __init__(self, config):
        self._config = config
        self._eventloop = None
        self._fd_to_handlers = {}

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self._config['port']))
        self.server_socket.listen(1024)

    def add_to_loop(self, loop):
        if self._eventloop:
            raise Exception("controller already add to loop")
        self._eventloop = loop
        self._eventloop.add(self.server_socket, eventloop.POLL_IN | eventloop.POLL_ERR, self)

    def handle_event(self, sock, event):
        if sock == self.server_socket:
            # 新客户端连接
            conn = self.server_socket.accept()
            Tcprelay(self, conn, self._eventloop, self._config, self._fd_to_handlers)
