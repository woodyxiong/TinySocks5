#!/usr/bin/python
# -*- coding: UTF-8 -*-

import socket
import select


class SelectLoop(object):
    def __init__(self):
        self._r_list = set()
        self._w_list = set()
        self._x_list = set()

    def poll(self, timeout=None):
        r, w, x = select.select(self._r_list, self._w_list, self._x_list)
        for result in r:
            return result



class EventLoop(object):
    def __init__(self):
        self._isstopping = False
        if hasattr(select, 'epoll'):
            self._impl = select.epoll()
            self._model = 'epoll'
        # elif hasattr(select, 'kqueue'):
        #     self._impl = KqueueLoop()
        #     self._model = 'kqueue'
        elif hasattr(select, 'select'):
            self._impl = SelectLoop()
            self._model = 'select'

    def poll(self):
        events = self._impl.poll(timeout=None)

    def stop(self):
        self._isstopping = True

    def run(self):
        events=[]
        while not self._isstopping:
            try:
                events = self.poll
            except Exception as e:
                print(e)
