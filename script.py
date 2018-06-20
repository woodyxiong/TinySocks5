
#
# -*- coding: UTF-8 -*-
# 使用socket模拟多线程，使多用户可以同时连接
import socket
import select

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setblocking(False)
sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
res = None

try:
    sock.connect(("google.com", 80))
    # sock.connect(("192.168.1.106", 789))
except Exception as e:
    print(e)

inputs = set()
inputs.add(sock)


while True:
    r_list, w_list, e_list = select.select(inputs, inputs, inputs)
    print("r")
    print(r_list)
    print("w")
    print(w_list)
    print("e")
    print(e_list)
