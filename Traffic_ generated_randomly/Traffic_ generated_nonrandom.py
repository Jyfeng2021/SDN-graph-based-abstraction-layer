#!/usr/bin/python
"""
Custom topology launcher Mininet, with traffic generation using iperf
用iperf在主机之间生成随机流量，供控制器监测和分类
调用方式为：
在命令终端，本文件所在目录下输入：sudo python3 topo_launcher.py 就可以运行，若需要选择参数则：sudo python3 topo_launcher.py --controller=remote ip=127.0.0.1 --topo=linear=4
注意：这里的流量不是随机产生，而是有小到大的产生。
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch, DefaultController
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

from linear import LinearTopo
from mesh import MeshTopo
from fat_tree_topo import FatTreeTopo

from os import path
from os import mkdir
import random
import time
import sys
import re
import numpy as np

# L4 PROTOCOLS
protocol_list = ['--udp', '']  # 是udp / 还是tcp方式的协议
port_min = 1025          #端口范围
port_max = 65536

# IPERF 设置的采样间隔
sampling_interval = '1'     # 采样间隔为秒seconds

# 流参数
bandwidth_list = ['100K', '200K', '300K', '400K', '500K', '600K', '700K', '800K', '900K', '1000K','2000K', '3000K', '4000K', '5000K', '6000K', '7000K', '8000K', '9000K','1M','2M','3M','4M','5M','6M','7M','8M','9M','10M', '20M', '30M', '40M', '50M', '60M', '70M', '80M', '90M', '100M','200M', '300M', '400M', '500M', '600M', '700M', '800M', '900M', '1000M']

def _generate_flow(id, duration, net, log_dir):
    """
   生成流，可能是不同的协议： tcp or udp
   id：第几个, duration：时间间隔, net：mininet对象, log_dir：日志地址
    """
    hosts = net.hosts             #

    # 选择随机的 src 和 dst，作为主机和服务器。
    end_points = random.sample(hosts, 2)         #从主机列表中随机抽取两个主机。
    src = net.get(str(end_points[0]))
    dst = net.get(str(end_points[1]))

    # 设置连接参数：协议，端口，带宽
    protocol = random.choice(protocol_list)
    port_argument = str(random.randint(port_min, port_max))
    bandwidth_argument = bandwidth_list[id]

    # 创建命令，这里就是用iperf进行流量生成，并进行网络丢包和延迟检测。
    server_cmd = "iperf -s "                      #这里是服务器端。
    server_cmd += protocol                        #指定协议
    server_cmd += " -p "                          #指定端口
    server_cmd += port_argument
    server_cmd += " -i "                          #指定间隔时间
    server_cmd += sampling_interval
    server_cmd += " > "                                           #文件存在覆盖原有文件内容。
    server_cmd += log_dir + "/flow_%003d" % id + ".txt 2>&1 "        #检测结果存入文件中
    server_cmd += " & "                                              #表示在后台运行

    client_cmd = "iperf -c "                 #这里是客户端。具体iperf命令网上可以查询。
    client_cmd += dst.IP() + " "
    client_cmd += protocol
    client_cmd += " -p "
    client_cmd += port_argument
    if protocol == "--udp":
        client_cmd += " -b "
        client_cmd += bandwidth_argument
    client_cmd += " -t "
    client_cmd += str(duration)
    client_cmd += " & "                                         #表示在后台运行

    dst.cmdPrint(server_cmd)# send the cmd
    src.cmdPrint(client_cmd)

def Generate_flows(n_flows, duration, net, log_dir):
    """
    Generate elephant and mice flows randomly for the given duration，生成流。
    """

    if not path.exists(log_dir):                           #日志文件夹如果不存在就生成。
        mkdir(log_dir)

    interval = int(duration / n_flows)                   #计算时间间隔

    # generating the flows 开始生成流
    for i in range(n_flows):

        _generate_flow(i, interval, net, log_dir)         #调用流生成函数
        time.sleep(interval)

    info("流生成终止...杀死active iperf sessions...\n")

    # killing iperf in all the hosts
    for host in net.hosts:
        host.cmdPrint('killall -9 iperf')                #清理资源


# 主函数

if __name__ == "__main__":
    log_dir = "/home/jyf/ryu/ryu/app/Experiment_ControlChannel/FlowGeneration/NoRandomLog"                                  #存放流量监测日志的文件夹
    topology = LinearTopo()                                                        #以下都是默认参数。默认为线性拓扑
    default_controller = True
    controller_ip = "127.0.0.1"                                                    # 本地localhost
    controller_port = 6633
    debug_flag = False
    debug_host = "localhost"
    debug_port = 6000

    # 读取命令行参数
    for arg in sys.argv:
        if arg.startswith("--controller"):            #选择控制器，对控制器参数进行配置，--controller=remote ip=ip_address
            default_controller = False
            arg = arg[2:]
            sub_arg = re.split("[,=]", arg)
            if "ip" in sub_arg:
                index = sub_arg.index("ip") + 1
                controller_ip = sub_arg[index]
            if "port" in sub_arg:
                index = sub_arg.index("port") + 1
                controller_port = int(sub_arg[index])

        elif arg.startswith("--topo"):                #选择topo类型，为：linear，mesh，fat_tree,--topo=拓扑名，节点数量
            arg = arg[2:]
            sub_arg = re.split("[,=]", arg)           #注意用等号或者逗号分割参数的。
            if sub_arg[1] == "linear":
                if len(sub_arg) == 3:
                    n = int(sub_arg[2])
                    topology = LinearTopo(n)

            if sub_arg[1] == "mesh":
                if len(sub_arg) == 3:
                    n = int(sub_arg[2])
                    topology = MeshTopo(n)
                else:
                    topology = MeshTopo()
            elif sub_arg[1] == "fat_tree":
                topology = FatTreeTopo()

        elif arg.startswith("--debug"):                      #这个需要pycharm专业版才能用，所以此参数可以不用。
            debug_flag = True
            if len(arg) > 7:
                arg = arg[8:]
                sub_arg = re.split(":", arg)
                debug_host = sub_arg[0]
                debug_port = int(sub_arg[1])

            sys.path.append("/home/stainlee/Programs/pycharm-2017.3.3/debug-eggs/pycharm-debug.egg")

            import pydevd
            #连接pycharm可以进行调试，但是需要专业版
            pydevd.settrace(debug_host, port=debug_port, stdoutToServer=True, stderrToServer=True)

    # Starting program
    setLogLevel('info')

    # 开始生成的 mininet
    if default_controller:
        print("默认参数")
        net = Mininet(topo=topology, controller=DefaultController, host=CPULimitedHost, link=TCLink,switch=OVSSwitch, autoSetMacs=True)
    else:                               #设置参数的时候，控制器
        #net = Mininet(topo=topology, controller=None, host=CPULimitedHost, link=TCLink,switch=OVSSwitch, autoSetMacs=True)               #原作者写的配置的控制器
        print("按照设置配置连接控制器的参数")
        net = Mininet(topo=topology,build=False,autoSetMacs=True)            #我写的配置的控制器
        net.addController('c1', controller=RemoteController, ip=controller_ip, protocol='tcp',port=controller_port)

    net.start()

    user_input = "QUIT"
    Mininet()
    # 一直运行直到退出。quits
    while True:
        # if user enters CTRL + D then treat it as quit，CTRL + D就推出了。
        try:
            user_input = input("请输入英文：GEN（生成流量）/CLI（mininet控制台）/QUIT（退出程序）不用区分大小写: ")                        #有三个参数可以选择，分别是：GEN/CLI/QUIT  ，Gen表示生成流量，CLI表示进入mininet，quit表示退出。
        except EOFError as error:
            user_input = "QUIT"

        if user_input.upper() == "GEN":
            experiment_duration = int(input("请输入总时长单位秒建议138（Experiment duration）: "))
            n_flows = int(input("请输入流的数量建议46（No of elephant flows）: "))
            info("Begain generation flows...\n")

            Generate_flows(n_flows, experiment_duration, net, log_dir)
        elif user_input.upper() == "CLI":     #进入mininet命令行后就可以按照mininet命令运行了。
            info("进入 CLI...若需要推出CLI清输入：exit \n")
            CLI(net)
        elif user_input.upper() == "QUIT":     #退出后会自动清理进程
            info("Terminating...\n")
            net.stop()
            break
        else:
            print("Command not found")

