#!/usr/bin/python
"""
Custom topology launcher Mininet, with traffic generation using iperf
用iperf在主机之间生成随机流量，供控制器监测和分类
调用方式为：
在命令终端，本文件所在目录下输入：python3 topo_launcher.py 就可以运行，若需要选择参数则：

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


# GLOBAL VARIABLES
# experiment_duration = 180  # seconds
# controller_ip = '10.14.87.5'  # ubuntu_lab


# FLOW SIZES
# Calculations
#
# flows with 15 packets or greater is an elephant flow as per CISCO
# considering 1512 byte packets, elephant flow size is
#
# threshold = (14 * 1512)/1000 = 21.168 KBytes
#

mice_flow_min = 100  # KBytes = 100KB                 #最小老鼠流
mice_flow_max = 10240  # KBytes = 10MB                #最大老鼠流
elephant_flow_min = 10240  # KBytes = 10MB               #最小大象流
elephant_flow_max = 1024*1024*10  # KBytes = 10 GB              #最大大象流



# L4 PROTOCOLS
protocol_list = ['--udp', '']  # 是udp / 还是tcp方式的协议
port_min = 1025          #端口范围
port_max = 65536

# IPERF 设置的采样间隔
sampling_interval = '1'  # 采样间隔为秒seconds


# 大象流参数
elephant_bandwidth_list = ['10M', '20M', '30M', '40M', '50M', '60M', '70M', '80M', '90M', '100M',
                           '200M', '300M', '400M', '500M', '600M', '700M', '800M', '900M', '1000M']

# 老鼠流参数
mice_bandwidth_list = ['100K', '200K', '300K', '400K', '500K', '600K', '700K', '800K', '900K', '1000K',
                       '2000K', '3000K', '4000K', '5000K', '6000K', '7000K', '8000K', '9000K', '10000K', '1000K']


def random_normal_number(low, high):             #从正态分布中抽取随机样本。
    range = high - low
    mean = int(float(range) * float(75) / float(100)) + low
    sd = int(float(range) / float(4))
    num = np.random.normal(mean, sd)
    return int(num)


def generate_elephant_flows(id, duration, net, log_dir):

    """
   生成大象流，可能是不同的协议： tcp or udp
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
    bandwidth_argument = random.choice(elephant_bandwidth_list)

    # 创建命令，这里就是用iperf进行流量生成，并进行网络丢包和延迟检测。
    server_cmd = "iperf -s "                      #这里是服务器端。
    server_cmd += protocol                        #指定协议
    server_cmd += " -p "                       #指定端口
    server_cmd += port_argument
    server_cmd += " -i "                         #指定间隔时间
    server_cmd += sampling_interval
    server_cmd += " > "                                           #文件存在覆盖原有文件内容。
    server_cmd += log_dir + "/elephant_flow_%003d" % id + ".txt 2>&1 "        #检测结果存入文件中
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
    client_cmd += " & "

    # send the cmd
    dst.cmdPrint(server_cmd)
    src.cmdPrint(client_cmd)


def generate_mice_flows(id, duration, net, log_dir):

    """
    Generate mice flows
    May use either tcp or udp
    """

    hosts = net.hosts

    # select random src and dst
    end_points = random.sample(hosts, 2)
    src = net.get(str(end_points[0]))
    dst = net.get(str(end_points[1]))

    # select connection params
    protocol = random.choice(protocol_list)
    port_argument = str(random.randint(port_min, port_max))
    bandwidth_argument = random.choice(mice_bandwidth_list)

    # create cmd
    server_cmd = "iperf -s "
    server_cmd += protocol
    server_cmd += " -p "
    server_cmd += port_argument
    server_cmd += " -i "
    server_cmd += sampling_interval
    server_cmd += " > "
    server_cmd += log_dir + "/mice_flow_%003d" % id + ".txt 2>&1 "
    server_cmd += " & "

    client_cmd = "iperf -c "
    client_cmd += dst.IP() + " "
    client_cmd += protocol
    client_cmd += " -p "
    client_cmd += port_argument
    if protocol == "--udp":
        client_cmd += " -b "
        client_cmd += bandwidth_argument
    client_cmd += " -t "
    client_cmd += str(duration)
    client_cmd += " & "

    # send the cmd
    dst.cmdPrint(server_cmd)
    src.cmdPrint(client_cmd)


def generate_flows(n_elephant_flows, n_mice_flows, duration, net, log_dir):
    """
    Generate elephant and mice flows randomly for the given duration，生成流。
    """

    if not path.exists(log_dir):                           #日志文件夹如果不存在就生成。
        mkdir(log_dir)

    n_total_flows = n_elephant_flows + n_mice_flows           #流总数
    interval = int(duration / n_total_flows)                   #计算时间间隔

    # setting random mice flow or elephant flows，设置随机老鼠流或者大象流。
    flow_type = []
    for i in range(n_elephant_flows):
        flow_type.append('E')
    for i in range(n_mice_flows):
        flow_type.append('M')
    random.shuffle(flow_type)

    # setting random flow start times，设置随机流的开始时间。
    flow_start_time = []
    for i in range(n_total_flows):
        n = random.randint(1, interval)
        if i == 0:
            flow_start_time.append(0)
        else:
            flow_start_time.append(flow_start_time[i - 1] + n)

    # setting random flow end times，设置随机流的结束时间
    # using normal distribution，用正态分布
    # we will keep duration till 95% of the total duration，我们只用所有时间的95%，剩下的5%用于走完现存的流。
    # the remaining 5% will be used as buffer to finish off the existing flows
    flow_end_time = []
    for i in range(n_total_flows):
        s = flow_start_time[i]
        e = int(float(95) / float(100) * float(duration))  # 95% of the duration
        end_time = random_normal_number(s, e)
        while end_time > e:
            end_time = random_normal_number(s, e)
        flow_end_time.append(end_time)

    # calculating flow duration from start time and end time generated above
    flow_duration = []
    for i in range(n_total_flows):
        flow_duration.append(flow_end_time[i] - flow_start_time[i])

    print("flow_type:",flow_type)
    print("flow_start_time:",flow_start_time)
    print("flow_end_time:",flow_end_time)
    print("flow_duration:",flow_duration)
    print("Remaining duration :" + str(duration - flow_start_time[-1]))         #剩下的时间

    # generating the flows
    for i in range(n_total_flows):
        if i == 0:
            time.sleep(flow_start_time[i])
        else:
            time.sleep(flow_start_time[i] - flow_start_time[i-1])
        if flow_type[i] == 'E':
            generate_elephant_flows(i, flow_duration[i], net, log_dir)         #调用大象流生成函数
        elif flow_type[i] == 'M':
            generate_mice_flows(i, flow_duration[i], net, log_dir)        #调用老鼠流生成函数

    # sleeping for the remaining duration of the experiment
    remaining_duration = duration - flow_start_time[-1]
    info("Traffic started, going to sleep for %s seconds...\n " % remaining_duration)
    time.sleep(remaining_duration)

    # ending all the flows generated by
    # killing the iperf sessions
    info("Stopping traffic...\n")
    info("Killing active iperf sessions...\n")

    # killing iperf in all the hosts
    for host in net.hosts:
        host.cmdPrint('killall -9 iperf')                #清理资源


# 主函数
if __name__ == "__main__":
    # Loading default parameter values
    log_dir = "/home/jyf/Desktop/Experiment/test"                                  #存放流量监测日志的文件夹
    topology = LinearTopo()                                                        #以下都是默认参数。默认为线性拓扑
    default_controller = True
    controller_ip = "127.0.0.1"                                                    # 本地localhost
    controller_port = 6633
    debug_flag = False
    debug_host = "localhost"
    debug_port = 6000

    # Reading command line arguments
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

        elif arg.startswith("--topo"):                #选择topo类型，为：linear，mesh，fat_tree,--topo=拓扑名 节点数量
            arg = arg[2:]
            sub_arg = re.split("[,=]", arg)
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

            # conecting to pycharm debugger
            pydevd.settrace(debug_host, port=debug_port, stdoutToServer=True, stderrToServer=True)

    # Starting program
    setLogLevel('info')

    # creating log directory
    """
    log_dir = path.expanduser('~') + log_dir
    i = 1
    while True:
        if not path.exists(log_dir + str(i)):
            mkdir(log_dir + str(i))
            log_dir = log_dir + str(i)
            break
        i = i+1
"""
    # 开始生成的 mininet
    if default_controller:                #不设置参数的时候，默认控制器
        net = Mininet(topo=topology, controller=DefaultController, host=CPULimitedHost, link=TCLink,
                      switch=OVSSwitch, autoSetMacs=True)
    else:                                  #配置的控制器
        net = Mininet(topo=topology, controller=None, host=CPULimitedHost, link=TCLink,
                      switch=OVSSwitch, autoSetMacs=True)
        net.addController('c1', controller=RemoteController, ip=controller_ip, port=controller_port)

    net.start()

    user_input = "QUIT"

    # 一直运行直到退出。quits
    while True:
        # if user enters CTRL + D then treat it as quit，CTRL + D就推出了。
        try:
            user_input = input("GEN/CLI/QUIT: ")                        #有三个参数可以选择，分别是：GEN/CLI/QUIT  ，Gen表示生成流量，CLI表示进入mininet，quit表示退出。
        except EOFError as error:
            user_input = "QUIT"

        if user_input.upper() == "GEN":
            experiment_duration = int(input("请输入总时长（Experiment duration）: "))
            n_elephant_flows = int(input("请输入大象流的数量（No of elephant flows）: "))
            n_mice_flows = int(input("请输入老鼠流的数量（No of mice flows）: "))

            generate_flows(n_elephant_flows, n_mice_flows, experiment_duration, net, log_dir)

        elif user_input.upper() == "CLI":     #进入mininet命令行后就可以按照mininet命令运行了。
            info("Running CLI...\n")
            CLI(net)

        elif user_input.upper() == "QUIT":     #退出后会自动清理进程
            info("Terminating...\n")
            net.stop()
            break

        else:
            print("Command not found")

'''
Area for scratch pad

'''
