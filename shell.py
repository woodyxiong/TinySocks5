#!/usr/bin/python
# -*- coding: UTF-8 -*-

import getopt
import sys


def get_config():
    try:
        config = {}
        shortopts = 'p:u:k:h'
        longopts = ['port', 'user', 'password', 'help']
        optlist, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
        for key, value in optlist:
            if key == '-p':
                config['port'] = value
            elif key == '-u':
                config['user'] = value
            elif key == '-k':
                config['password'] = value
        return config

    except getopt.GetoptError as e:
        print(e)
        print_help()
        sys.exit(0)


def print_help():
    print('''
A tiny socks5 server helps you by pass firewalls.

TinySocks5 options:
    -p,--port       PORT        server port
    -u,--user       USER        socks5 user
    -k,--password   PASSWORD    socks5 password

General options:
    -h,--help       HELP        show help message
    
Program address:
    https://github.com/woodyxiong/TinySocks5
''')
