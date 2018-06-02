#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import shell
import controller
import eventloop
import logging

def main():
    # 获取配置
    config = shell.get_config()
    # 设置日志 debug/info/warning/error/critical
    logging.basicConfig(level=logging.INFO,
                        filename='./log.txt',
                        filemode='w',
                        format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    try:
        tcp_server = controller.Controller(config)
        loop = eventloop.EventLoop()
        tcp_server.add_to_loop(loop)
    except Exception as e:
        print(e)
        logging.error(e)
        sys.exit(-1)

    loop.run()


if __name__ == '__main__':
    main()
