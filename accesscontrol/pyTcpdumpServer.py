import socket
import re
from multiprocessing import Process
from app.dataBase_candle import FindAuth
from app.flowTable_operate import PostOperation

"""
得到源ip、目的ip、目的端口等信息，进而去数据库寻找此连接权限，若权限有，则下发相对应的通过流表项
Get the source ip address, destination ip address, destination port and other information, and then go to the database to find the connection permission, if the permission is available, the corresponding through the flow entry is issued

"""


class Server1:
    def __init__(self, host, port, lst_num):
        self.host = host
        self.port = port
        self.lst_num = lst_num


    def recv_message(self, conn, addr):
        data = conn.recv(1024)

        result = re.findall(".*IP (.*): Flags.*", data.decode('utf-8'))
        list_res = result[0].split('> ')
        src_ip = '.'.join(list_res[0].split('.')[:4])
        dst_ip, dst_port = '.'.join(list_res[1].split('.')[0:4]), list_res[1].split('.')[4:]
        # print(src_ip, dst_ip, dst_port[0])

        #Get permission
        find_auth = FindAuth()
        auth_res = find_auth.get_data(src_ip=src_ip, dst_ip=dst_ip, dst_port=dst_port[0])
        as_res = find_auth.get_as(src_ip=src_ip)
        print("from {0}:".format(addr), data.decode('utf-8'))
        print('Limits of authority：', auth_res)

        if as_res == 'as1':
            postTable = PostOperation('172.17.0.2', '8080')
            postTable.post_add_flow(src_ip=src_ip, dst_ip=dst_ip, dst_port=dst_port[0], auth=auth_res)
        elif as_res == 'as2':
            postTable = PostOperation('172.17.0.3', '8080')
            postTable.post_add_flow(src_ip=src_ip, dst_ip=dst_ip, dst_port=dst_port[0], auth=auth_res)


    def server_link(self, conn, addr):
        conn.send("Welcome connect!".encode())

        while True:
            try:
                self.recv_message(conn, addr)
            except Exception:
                break

        conn.close()

    # 服务端的启动程序  Server side startup program
    def server_start(self):
        # IPv4
        s_pro = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_pro.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_pro.bind((self.host, self.port))
        s_pro.listen(self.lst_num)
        print('Waiting link...')
        while True:
            conn, addr = s_pro.accept()
            print("Success connect from ", addr)
            p = Process(target=self.server_link, args=(conn, addr))
            p.start()


if __name__ == '__main__':
    server = Server1('10.0.2.15', 62121, 2)
    server.server_start()
