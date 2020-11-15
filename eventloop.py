#!/usr/bin/python
# -*- coding: UTF-8 -*-

import select
import logging

TIMEOUT = 10

POLL_NULL = 0x00
POLL_IN = 0x01
POLL_OUT = 0x04
POLL_ERR = 0x08
POLL_HUP = 0x10
POLL_NVAL = 0x20


class SelectLoop(object):
    def __init__(self):
        self._r_list = set()
        self._w_list = set()
        self._e_list = set()

    def poll(self, timeout=None):
        r, w, e = select.select(self._r_list, self._w_list, self._e_list, timeout)
        result = []
        for res_r in r:
            t = (res_r, POLL_IN)
            result.append(t)
        for res_w in w:
            t = (res_w, POLL_OUT)
            result.append(t)
        for res_e in e:
            t = (res_e, POLL_ERR)
            result.append(t)
        return result

    def register(self, fd, mode):
        # if self._r_list.__contains__(fd):
        #     logging.info("select的_r_list的"+str(fd)+"已经存在")
        # self._r_list.add(fd)
        # if self._w_list.__contains__(fd):
        #     logging.info("select的_w_list的"+str(fd)+"已经存在")
        # self._w_list.add(fd)
        # if self._e_list.__contains__(fd):
        #     logging.info("select的_e_list的"+str(fd)+"已经存在")
        # self._e_list.add(fd)
        if mode & POLL_IN:
            if self._r_list.__contains__(fd):
                logging.info("select的_r_list的" + str(fd) + "已经存在")
            self._r_list.add(fd)
        if mode & POLL_OUT:
            if self._w_list.__contains__(fd):
                logging.info("select的_w_list的" + str(fd) + "已经存在")
            self._w_list.add(fd)
        if mode & POLL_ERR:
            if self._e_list.__contains__(fd):
                logging.info("select的_e_list的" + str(fd) + "已经存在")
            self._e_list.add(fd)

    def unregister(self, fd):
        if self._r_list.__contains__(fd):
            self._r_list.remove(fd)
        if self._w_list.__contains__(fd):
            self._w_list.remove(fd)
        if self._e_list.__contains__(fd):
            self._e_list.remove(fd)

    def clear_we_list(self, fd):
        if self._w_list.__contains__(fd):
            self._w_list.remove(fd)
        if self._e_list.__contains__(fd):
            self._e_list.remove(fd)


class EventLoop(object):
    def __init__(self):
        self._isstopping = False
        # if hasattr(select, 'epoll'):
        #     self._impl = select.epoll()
        #     self._model = 'epoll'
        # elif hasattr(select, 'kqueue'):
        #     self._impl = KqueueLoop()
        #     self._model = 'kqueue'
        if hasattr(select, 'select'):
            self._impl = SelectLoop()
            self._model = 'select'
        else:
            raise Exception("Don't hava select model")
        self._fdmap = {}  # [fd](f,handler)

    def poll(self, timeout):
        events = self._impl.poll(timeout)
        result = []
        for item in events:
            t = (item[0], self._fdmap[item[0]][0], item[1])
            result.append(t)
        return result
        # [(768, <socket._socketobject object at 0x05ABEA78>)]

    def stop(self):
        self._isstopping = True

    def add(self, socket, mode, handler):
        fd = socket.fileno()
        if self._fdmap.__contains__(fd):
            logging.info("event映射的文件标识符", fd, "已存在")
        self._fdmap[fd] = (socket, handler)
        self._impl.register(fd, mode)

    def remove(self, f, handler):
        fd = f.fileno()
        if not self._fdmap[fd]:
            logging.info("event映射的文件标识符", fd, "为空")
        del self._fdmap[fd]
        self._impl.unregister(fd)

    def clear_we(self, fd):
        self._impl.clear_we_list(fd)

    def run(self):
        events = []
        while not self._isstopping:
            print("2333")
            try:
                events = self.poll(TIMEOUT)
            except Exception as e:
                print(events)
                print(e)
                logging.info(e)

            #   events(fileno,socket,1)
            for fd, sock, event in events:
                try:
                    if sock.fileno() < 0:
                        logging.warning("文件标识符小于零" + str(sock.fileno()))
                        break
                    if self._fdmap[sock.fileno()][0]:
                        handler = self._fdmap[sock.fileno()][1]
                    else:
                        self.remove(sock.fileno())
                        logging.warning("未找到对应的句柄" + str(sock.fileno()))
                        break
                    # 转入控制器
                    handler.handle_event(sock, event)
                except (OSError, IOError) as e:
                    logging.warning(e)
                    print(e)

    def modify(self, fd, mode):
        self.unregister(fd)
        self.register(fd, mode)


def errno_from_exception(e):
    """Provides the errno from an Exception object.

    There are cases that the errno attribute was not set so we pull
    the errno out of the args but if someone instatiates an Exception
    without any args you will get a tuple error. So this function
    abstracts all that behavior to give you a safe way to get the
    errno.
    """

    if hasattr(e, 'errno'):
        return e.errno
    elif e.args:
        return e.args[0]
    else:
        return None
