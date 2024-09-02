from app.dataBase_candle import FindAuth
import requests

"""
此部分主要实现流表项的下发功能，包括初始化流表项下发和权限流表项下发(北向接口，通过request的get、post实现)
1、初始化流表项下发
当网络架构建立好之后，控制器运行的自学习交换机程序会下发流表项，此时进行的各种连接都不会被阻拦，所以需要
初始化流表项，也就是向交换机下发阻拦连接的流表项，这里主要是根据数据库记录，初始时下发默认无访问权限的流表项。

2、权限流表项下发
权限流表项下发，也就是当进行连接请求时，本系统通过查询数据库中对应的记录，判断连接是否有权限，然后下发对应的
流表项，覆盖初始化中的阻拦连接流表项。
"""


class PostOperation:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    # 获取各个控制器下的交换机dpid
    def get_switched_id(self, b_ip1=None, b_ip2=None, b_port1=None, b_port2=None):
        ip, port = self.ip, self.port
        # 对本系统对应的网络结构        if b_ip1:
            ip, port = b_ip1, b_port1
        elif b_ip2:
            ip, port = b_ip2, b_port2

        # 获取dpid的url
        url = 'http://' + ip + ':' + port + '/stats/switches'
        # 通过get()请求获取dpid
        re_switch_id = requests.get(url=url).json()
        switch_id = 0
        for i in re_switch_id:
            switch_id = i
        # print(switch_id)
        return switch_id

    # 初始化流表项下发方法
    def init_add_flow(self, b_ip1=None, b_ip2=None, b_port1=None, b_port2=None):
        # 先获取权限数据库的所有记录，每条记录对应一个初始化流表项
        find_auth = FindAuth()
        record = find_auth.get_record()
        # 获取控制器下的交换机的dpid
        dpid = self.get_switched_id()

        # 遍历记录，每条记录对应一条流表项
        for i in record:
            ip, port = self.ip, self.port
            src_ip, dst_ip, dst_port = str(i[0]), str(i[1]), str(i[2])
            # print(src_ip, dst_ip, dst_port)

            # 获取记录当中的源主机归属域，通过归属域才能知道流表项向哪个控制器下发
            as_res = find_auth.get_as(src_ip)
            if as_res == 'as1':
                dpid = self.get_switched_id(b_ip1=b_ip1, b_port1=b_port1)
                ip, port = b_ip1, b_port1
            elif as_res == 'as2':
                dpid = self.get_switched_id(b_ip2=b_ip2, b_port2=b_port2)
                ip, port = b_ip2, b_port2

            # 下发流表项的url
            url = 'http://' + ip + ':' + port + '/stats/flowentry/add'
            # 初始化流表项，其优先级为100，限制类型为tcp(http)，源主机、目的主机、目的端口对应的连接
            data = {
                "dpid": dpid,
                "cookie": 0,
                "cookie_mask": 0,
                "table_id": 0,
                "priority": 100,
                "flags": 0,
                "match": {
                    "dl_type": 0x0800,
                    "nw_proto": 6,
                    "tcp_dst": dst_port,
                    "nw_src": src_ip,
                    "nw_dst": dst_ip,
                },
                "actions": [
                    {
                        "type": "DROP"  # 动作为丢弃，即初始时默认所有连接无权限
                    }
                ]
            }

            response = requests.post(url=url, json=data)
            if response.status_code == 200:
                print('Successfully Add!')
            else:
                print('Fail!')

        # print(record)

    # 权限流表项下发方法
    def post_add_flow(self, src_ip, dst_ip, dst_port, auth):
        # 先获取控制器下对应的交换机的dpid
        dpid = self.get_switched_id()

        # 进行流表项的下发
        """
        当对应的连接权限为‘no’时，需要进行流表项的删除，采用严格删除方法，也就是若已存在此连接对应的
        'yes'权限流表项时，删除yes权限流表项，若不存在此连接对应的流表项，严格删除方法并不会做事，
        匹配的仍然是初始化的阻拦流表项。
        当对应的权限为’yes‘时，需要进行流表项的下发，也就是让连接请求正常通过链路，此时通过下发流表项
        覆盖初始化的阻拦流表项，也就是下发流表项的优先级高于初始化流表项优先级即可。
        """
        if auth == 'no':
            # 严格删除方法对应的url
            url = 'http://' + self.ip + ':' + self.port + '/stats/flowentry/delete_strict'
            """
            删除和下面所有数据严格匹配的流表项
            """
            data = {
                "dpid": dpid,
                "cookie": 0,
                "cookie_mask": 0,
                "table_id": 0,
                "idle_timeout": 300,
                "hard_timeout": 600,
                "priority": 101,
                "flags": 0,
                "match": {
                    "dl_type": 0x0800,
                    "nw_proto": 6,
                    "tcp_dst": dst_port,
                    "nw_src": src_ip,
                    "nw_dst": dst_ip,
                },
                "actions": [
                    {
                        "type": "OUTPUT",
                        "port": 3
                    }
                ]
            }
            response = requests.post(url=url, json=data)
            if response.status_code == 200:
                print('Delete Add!')
            else:
                print('Fail!')

            print('No permission!')
        # 当权限为‘ubknown’时，不处理
        elif auth == 'unknown':
            print('Unknown permissions!')
        elif auth == 'yes':
            url = 'http://' + self.ip + ':' + self.port + '/stats/flowentry/add'
            data = {
                "dpid": dpid,
                "cookie": 0,
                "cookie_mask": 1,
                "table_id": 0,
                "idle_timeout": 300,
                "hard_timeout": 600,
                "priority": 101,
                "flags": 1,
                "match": {
                    "dl_type": 0x0800,
                    "nw_proto": 6,
                    "tcp_dst": dst_port,
                    "nw_src": src_ip,
                    "nw_dst": dst_ip,
                },
                "actions": [
                    {
                        "type": "OUTPUT",
                        "port": 3
                    }
                ]
            }

            response = requests.post(url=url, json=data)
            if response.status_code == 200:
                print('Successfully Add!')
            else:
                print('Fail!')
        else:
            print('Error!')


if __name__ == '__main__':
    postOperation = PostOperation('172.17.0.2', '8080')
    postOperation.init_add_flow()
    # postOperation.get_switched_id()
    # postOperation.post_add_flow('10.0.1.2', '10.0.3.1', '8001', 'yes')
