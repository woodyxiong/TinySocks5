#!/usr/bin/python
# -*- coding: UTF-8 -*-

import socket


class Controller(object):
    def __init__(self, config):
        self._config = config
        self._eventloop = None

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', self._config['port']))
        self.server_socket.listen(1024)

    def add_to_loop(self, loop):
        if self._eventloop:
            raise Exception("already add to loop")
        self._eventloop = loop
        # self._eventloop.add(self.server_socket)

