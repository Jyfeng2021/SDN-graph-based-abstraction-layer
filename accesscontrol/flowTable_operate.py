from app.dataBase_candle import FindAuth
import requests

"""
This part mainly implements the flow entry delivery function, including the initial flow entry delivery and permission flow entry delivery

1. Initialize flow entry delivery

After the network architecture is established, the self-learning switch program run by the controller will send flow entries. In this case, all connections are not blocked

Initialize the flow entry, that is, deliver the flow entry that blocks connections to the switch. The flow entry that has no access permission by default is delivered initially based on the database records.



2. Deliver the permission flow entry

Permission flow entry delivery, that is, when a connection request is made, the system queries the corresponding records in the database to determine whether the connection has permission, and then delivers the corresponding

Stream entry, overrides the block connection stream entry in initialization.
"""
"" "
This part mainly implements the flow entry delivery function, including the initial flow entry delivery and permission flow entry delivery
1. Initialize flow entry delivery
After the network architecture is established, the self-learning switch program run by the controller will send flow entries. In this case, all connections are not blocked
Initialize the flow entry, that is, deliver the flow entry that blocks connections to the switch. The flow entry that has no access permission by default is delivered initially based on the database records.

2. Deliver the permission flow entry
Permission flow entry delivery, that is, when a connection request is made, the system queries the corresponding records in the database to determine whether the connection has permission, and then delivers the corresponding
Stream entry, overrides the block connection stream entry in initialization.
"" "


class PostOperation:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def get_switched_id(self, b_ip1=None, b_ip2=None, b_port1=None, b_port2=None):
        ip, port = self.ip, self.port

            ip, port = b_ip1, b_port1
        elif b_ip2:
            ip, port = b_ip2, b_port2

        url = 'http://' + ip + ':' + port + '/stats/switches'

        re_switch_id = requests.get(url=url).json()
        switch_id = 0
        for i in re_switch_id:
            switch_id = i
        # print(switch_id)
        return switch_id

    # 初始化流表项下发方法            Example Initialize the flow entry delivery method
    def init_add_flow(self, b_ip1=None, b_ip2=None, b_port1=None, b_port2=None):

        find_auth = FindAuth()
        record = find_auth.get_record()

        dpid = self.get_switched_id()

        # 遍历记录，每条记录对应一条流表项# Walk through the records, each record corresponds to a flow table entry
        for i in record:
            ip, port = self.ip, self.port
            src_ip, dst_ip, dst_port = str(i[0]), str(i[1]), str(i[2])
            # print(src_ip, dst_ip, dst_port)

            as_res = find_auth.get_as(src_ip)
            if as_res == 'as1':
                dpid = self.get_switched_id(b_ip1=b_ip1, b_port1=b_port1)
                ip, port = b_ip1, b_port1
            elif as_res == 'as2':
                dpid = self.get_switched_id(b_ip2=b_ip2, b_port2=b_port2)
                ip, port = b_ip2, b_port2

          
            url = 'http://' + ip + ':' + port + '/stats/flowentry/add'
            #Initializes the flow entry
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
                        "type": "DROP"  # By default, all connections have no permissions
                    }
                ]
            }

            response = requests.post(url=url, json=data)
            if response.status_code == 200:
                print('Successfully Add!')
            else:
                print('Fail!')

        # print(record)

    # 权限流表项下发方法# Permission flow entry delivery method
    def post_add_flow(self, src_ip, dst_ip, dst_port, auth):
     
        dpid = self.get_switched_id()

        if auth == 'no':
    
            url = 'http://' + self.ip + ':' + self.port + '/stats/flowentry/delete_strict'

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
