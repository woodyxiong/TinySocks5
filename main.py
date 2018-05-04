#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import shell
import controller
import eventloop
# import tcprelay


def main():
    # 获取配置
    config = shell.get_config()

    try:
        tcp_server = controller.Controller(config)
        loop = eventloop.EventLoop()
    except Exception as e:
        print(e)
        sys.exit(0)

    loop.run()


if __name__ == '__main__':
    main()
