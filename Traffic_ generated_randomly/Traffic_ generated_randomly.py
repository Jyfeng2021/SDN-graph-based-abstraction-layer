#!/usr/bin/python
"""
Custom topology launcher Mininet, with traffic generation using iperf.

The calling method is:
On the command terminal, enter the file directory, and select parameters as required: Traffic_generated_randomly.py
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

# FLOW SIZES
# According to CISCO, flows with 15 packets or greater are considered elephant flows.
# Considering 1512 byte packets, the elephant flow size threshold is:
# threshold = (14 * 1512)/1000 = 21.168 KBytes

mice_flow_min = 100  # Minimum mice flow size in KB
mice_flow_max = 10240  # Maximum mice flow size in KB
elephant_flow_min = 10240  # Minimum elephant flow size in KB
elephant_flow_max = 1024 * 1024 * 10  # Maximum elephant flow size in KB

# L4 PROTOCOLS
protocol_list = ['--udp', '']  # Protocol options: UDP or TCP
port_min = 1025  # Minimum port number
port_max = 65536  # Maximum port number

sampling_interval = '1'  # Sampling interval in seconds

elephant_bandwidth_list = ['10M', '20M', '30M', '40M', '50M', '60M', '70M', '80M', '90M', '100M',
                           '200M', '300M', '400M', '500M', '600M', '700M', '800M', '900M', '1000M']

mice_bandwidth_list = ['100K', '200K', '300K', '400K', '500K', '600K', '700K', '800K', '900K', '1000K',
                       '2000K', '3000K', '4000K', '5000K', '6000K', '7000K', '8000K', '9000K', '10000K', '1000K']


def random_normal_number(low, high):
    """Generate a random number from a normal distribution within a specified range."""
    range = high - low
    mean = int(float(range) * 0.75) + low
    sd = int(float(range) / 4)
    num = np.random.normal(mean, sd)
    return int(num)


def generate_elephant_flows(id, duration, net, log_dir):
    """
    Generate an elephant flow, which may use TCP or UDP protocol.
    id: Flow ID, duration: Flow duration, net: Mininet object, log_dir: Directory to save logs.
    """
    hosts = net.hosts
    end_points = random.sample(hosts, 2)  # Select two random hosts
    src = net.get(str(end_points[0]))
    dst = net.get(str(end_points[1]))

    protocol = random.choice(protocol_list)
    port_argument = str(random.randint(port_min, port_max))
    bandwidth_argument = random.choice(elephant_bandwidth_list)

    server_cmd = f"iperf -s {protocol} -p {port_argument} -i {sampling_interval} > {log_dir}/elephant_flow_{id:03d}.txt 2>&1 &"
    client_cmd = f"iperf -c {dst.IP()} {protocol} -p {port_argument}"
    if protocol == "--udp":
        client_cmd += f" -b {bandwidth_argument}"
    client_cmd += f" -t {duration} &"

    dst.cmdPrint(server_cmd)
    src.cmdPrint(client_cmd)


def generate_mice_flows(id, duration, net, log_dir):
    """
    Generate a mice flow, which may use TCP or UDP protocol.
    """
    hosts = net.hosts
    end_points = random.sample(hosts, 2)  # Select two random hosts
    src = net.get(str(end_points[0]))
    dst = net.get(str(end_points[1]))

    protocol = random.choice(protocol_list)
    port_argument = str(random.randint(port_min, port_max))
    bandwidth_argument = random.choice(mice_bandwidth_list)

    server_cmd = f"iperf -s {protocol} -p {port_argument} -i {sampling_interval} > {log_dir}/mice_flow_{id:03d}.txt 2>&1 &"
    client_cmd = f"iperf -c {dst.IP()} {protocol} -p {port_argument}"
    if protocol == "--udp":
        client_cmd += f" -b {bandwidth_argument}"
    client_cmd += f" -t {duration} &"

    dst.cmdPrint(server_cmd)
    src.cmdPrint(client_cmd)


def generate_flows(n_elephant_flows, n_mice_flows, duration, net, log_dir):
    """
    Generate both elephant and mice flows randomly for the given duration.
    """
    if not path.exists(log_dir):
        mkdir(log_dir)

    n_total_flows = n_elephant_flows + n_mice_flows
    interval = duration // n_total_flows

    flow_type = ['E'] * n_elephant_flows + ['M'] * n_mice_flows
    random.shuffle(flow_type)

    flow_start_time = [0] + [random.randint(1, interval) for _ in range(1, n_total_flows)]
    flow_start_time = [sum(flow_start_time[:i + 1]) for i in range(n_total_flows)]

    flow_end_time = []
    for i in range(n_total_flows):
        s = flow_start_time[i]
        e = int(0.95 * duration)
        end_time = random_normal_number(s, e)
        while end_time > e:
            end_time = random_normal_number(s, e)
        flow_end_time.append(end_time)

    flow_duration = [end_time - start_time for start_time, end_time in zip(flow_start_time, flow_end_time)]

    for i in range(n_total_flows):
        time.sleep(flow_start_time[i] - (flow_start_time[i - 1] if i > 0 else 0))
        if flow_type[i] == 'E':
            generate_elephant_flows(i, flow_duration[i], net, log_dir)
        elif flow_type[i] == 'M':
            generate_mice_flows(i, flow_duration[i], net, log_dir)

    time.sleep(duration - flow_start_time[-1])

    for host in net.hosts:
        host.cmdPrint('killall -9 iperf')


if __name__ == "__main__":
    log_dir = "/home/jyf/Desktop/Experiment/test"
    topology = LinearTopo()
    default_controller = True
    controller_ip = "127.0.0.1"
    controller_port = 6633

    for arg in sys.argv:
        if arg.startswith("--controller"):
            default_controller = False
            sub_arg = re.split("[,=]", arg[2:])
            if "ip" in sub_arg:
                controller_ip = sub_arg[sub_arg.index("ip") + 1]
            if "port" in sub_arg:
                controller_port = int(sub_arg[sub_arg.index("port") + 1])
        elif arg.startswith("--topo"):
            sub_arg = re.split("[,=]", arg[2:])
            if sub_arg[1] == "linear" and len(sub_arg) == 3:
                topology = LinearTopo(int(sub_arg[2]))

    setLogLevel('info')

    if default_controller:
        net = Mininet(topo=topology, controller=DefaultController, host=CPULimitedHost, link=TCLink,
                      switch=OVSSwitch, autoSetMacs=True)
    else:
        net = Mininet(topo=topology, controller=None, host=CPULimitedHost, link=TCLink,
                      switch=OVSSwitch, autoSetMacs=True)
        net.addController('c1', controller=RemoteController, ip=controller_ip, port=controller_port)

    net.start()

    while True:
        try:
            user_input = input("GEN/CLI/QUIT: ").strip().upper()
        except EOFError:
            user_input = "QUIT"

        if user_input == "GEN":
            duration = int(input("Experiment duration (seconds): "))
            n_elephant_flows = int(input("Number of elephant flows: "))
            n_mice_flows = int(input("Number of mice flows: "))
            generate_flows(n_elephant_flows, n_mice_flows, duration, net, log_dir)
        elif user_input == "CLI":
            CLI(net)
        elif user_input == "QUIT":
            net.stop()
            break
        else:
            print("Invalid command")
