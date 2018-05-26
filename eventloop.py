#!/usr/bin/python
# -*- coding: UTF-8 -*-

import select


class SelectLoop(object):
    def __init__(self):
        self._r_list = set()
        self._w_list = set()
        self._x_list = set()

    def poll(self, timeout=None):
        r, w, x = select.select(self._r_list, self._w_list, self._x_list)
        result = []
        for res in r:
            t = (res, 1)
            result.append(t)
        return result

    def register(self, fd):
        self._r_list.add(fd)



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
        self._fdmap = {} #[fd](f,handler)

    def poll(self):
        events = self._impl.poll(timeout=None)
        result = []
        for item in events:
            t = (item[0], self._fdmap[item[0]][0], item[1])
            result.append(t)
        return result
        # [(768, <socket._socketobject object at 0x05ABEA78>)]

    def stop(self):
        self._isstopping = True

    def add(self, f, handler):
        fd = f.fileno()
        self._fdmap[fd] = (f, handler)
        self._impl.register(fd)

    def run(self):
        events = []
        while not self._isstopping:
            try:
                events = self.poll()
            except Exception as e:
                print(e)

            for fd, sock, event in events:
                handler = self._fdmap[fd][1]
                try:
                    # 转入控制器
                    handler.handle_event(sock, event)
                except (OSError, IOError) as e:
                    print(e)
