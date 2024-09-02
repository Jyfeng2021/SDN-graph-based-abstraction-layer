from app.flowTable_operate import PostOperation
from monitor.pyTcpdumpServer import Server1

if __name__ == '__main__':
    # 初始化流表项
    init = PostOperation('172.17.0.2', '8080')
    init.init_add_flow('172.17.0.2', '172.17.0.3', '8080', '8080')

    # 开启服务端程序
    server = Server1('10.0.2.15', 62121, 2)
    server.server_start()