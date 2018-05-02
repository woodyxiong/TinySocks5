#!/usr/bin/python
# -*- coding: UTF-8 -*-

import socket
import select


class SelectLoop(object):
    def __init__(self):
        self._r_list = set()
        self._w_list = set()
        self._x_list = set()


class EventLoop(object):
    def __init__(self):
        if hasattr(select, 'epoll'):
            self._impl = select.epoll()
            self._model = 'epoll'
        # elif hasattr(select, 'kqueue'):
        #     self._impl = KqueueLoop()
        #     self._model = 'kqueue'
        elif hasattr(select, 'select'):
            self._impl = SelectLoop()
            self._model = 'select'
