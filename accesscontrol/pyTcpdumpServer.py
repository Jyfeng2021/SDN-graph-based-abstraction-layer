import socket
import re
from multiprocessing import Process
from app.dataBase_candle import FindAuth
from app.flowTable_operate import PostOperation

"""
tcpdump抓包服务端：
主要用来接收抓包监测的终端访问资源服务器的连接信息，将抓到的包发送到这里进行处理，
得到源ip、目的ip、目的端口等信息，进而去数据库寻找此连接权限，若权限有，则下发相对应的通过流表项

本系统的服务端采用多进程实现socket客户端的多连接，可以处理接收多个抓包程序发送过来的信息。
"""


class Server1:
    def __init__(self, host, port, lst_num):
        self.host = host
        self.port = port
        self.lst_num = lst_num

    # 数据处理
    def recv_message(self, conn, addr):
        data = conn.recv(1024)
        # 对收到的抓包信息进行解析，得出源ip、目的ip、目的端口等信息
        result = re.findall(".*IP (.*): Flags.*", data.decode('utf-8'))
        list_res = result[0].split('> ')
        src_ip = '.'.join(list_res[0].split('.')[:4])
        dst_ip, dst_port = '.'.join(list_res[1].split('.')[0:4]), list_res[1].split('.')[4:]
        # print(src_ip, dst_ip, dst_port[0])

        # 获取权限
        find_auth = FindAuth()
        auth_res = find_auth.get_data(src_ip=src_ip, dst_ip=dst_ip, dst_port=dst_port[0])
        as_res = find_auth.get_as(src_ip=src_ip)
        print("from {0}:".format(addr), data.decode('utf-8'))
        print('权限：', auth_res)

        # 根据所属自治域选择向不同的控制器下发流表项
        if as_res == 'as1':
            postTable = PostOperation('172.17.0.2', '8080')
            postTable.post_add_flow(src_ip=src_ip, dst_ip=dst_ip, dst_port=dst_port[0], auth=auth_res)
        elif as_res == 'as2':
            postTable = PostOperation('172.17.0.3', '8080')
            postTable.post_add_flow(src_ip=src_ip, dst_ip=dst_ip, dst_port=dst_port[0], auth=auth_res)

    # 服务端的数据接收，在调用时使用多进程
    def server_link(self, conn, addr):
        conn.send("Welcome connect!".encode())

        while True:
            try:
                self.recv_message(conn, addr)
            except Exception:
                break

        conn.close()

    # 服务端的启动程序
    def server_start(self):
        # IPv4
        s_pro = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 操作系统会在服务器socket被关闭或服务器进程终止后马上释放该服务器的端口
        s_pro.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_pro.bind((self.host, self.port))
        s_pro.listen(self.lst_num)
        print('Waiting link...')
        while True:
            conn, addr = s_pro.accept()
            print("Success connect from ", addr)
            # 启动多进程实现多连接
            p = Process(target=self.server_link, args=(conn, addr))
            p.start()


if __name__ == '__main__':
    server = Server1('10.0.2.15', 62121, 2)
    server.server_start()
