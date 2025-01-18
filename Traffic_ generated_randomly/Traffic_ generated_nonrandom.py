#!/usr/bin/python
"""
Custom topology launcher Mininet, with traffic generation using iperf.
Generate random traffic between hosts for controller monitoring and classification.
Usage:
Run in terminal from the directory of this script: sudo python3 topo_launcher.py
To customize parameters: sudo python3 topo_launcher.py --controller=remote ip=127.0.0.1 --topo=linear=4
Note: Traffic is not randomly generated but increases sequentially.
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
protocol_list = ['--udp', '']  # UDP or TCP protocol
port_min = 1025          # Port range
port_max = 65536

# IPERF sampling interval
sampling_interval = '1'     # Sampling interval in seconds

# Flow parameters
bandwidth_list = ['100K', '200K', '300K', '400K', '500K', '600K', '700K', '800K', '900K', '1000K','2000K', '3000K', '4000K', '5000K', '6000K', '7000K', '8000K', '9000K','1M','2M','3M','4M','5M','6M','7M','8M','9M','10M', '20M', '30M', '40M', '50M', '60M', '70M', '80M', '90M', '100M','200M', '300M', '400M', '500M', '600M', '700M', '800M', '900M', '1000M']

def _generate_flow(id, duration, net, log_dir):
    """
    Generate flows with different protocols: TCP or UDP.
    id: Flow ID, duration: Interval, net: Mininet object, log_dir: Log directory
    """
    hosts = net.hosts  # Get the list of hosts

    # Randomly select src and dst as the client and server
    end_points = random.sample(hosts, 2)  # Randomly select two hosts from the list
    src = net.get(str(end_points[0]))
    dst = net.get(str(end_points[1]))

    # Set connection parameters: protocol, port, bandwidth
    protocol = random.choice(protocol_list)
    port_argument = str(random.randint(port_min, port_max))
    bandwidth_argument = bandwidth_list[id]

    # Create commands to generate traffic and detect packet loss and delay using iperf
    server_cmd = "iperf -s "                      # Server side
    server_cmd += protocol                        # Specify protocol
    server_cmd += " -p "                          # Specify port
    server_cmd += port_argument
    server_cmd += " -i "                          # Specify interval
    server_cmd += sampling_interval
    server_cmd += " > "                           # Overwrite existing content
    server_cmd += log_dir + "/flow_%003d" % id + ".txt 2>&1 "  # Log results to file
    server_cmd += " & "                           # Run in background

    client_cmd = "iperf -c "                      # Client side
    client_cmd += dst.IP() + " "
    client_cmd += protocol
    client_cmd += " -p "
    client_cmd += port_argument
    if protocol == "--udp":
        client_cmd += " -b "
        client_cmd += bandwidth_argument
    client_cmd += " -t "
    client_cmd += str(duration)
    client_cmd += " & "                           # Run in background

    dst.cmdPrint(server_cmd)  # Execute the server command
    src.cmdPrint(client_cmd)  # Execute the client command

def Generate_flows(n_flows, duration, net, log_dir):
    """
    Generate elephant and mice flows randomly for the given duration.
    """

    if not path.exists(log_dir):  # Create log directory if it doesn't exist
        mkdir(log_dir)

    interval = int(duration / n_flows)  # Calculate interval

    # Generating the flows
    for i in range(n_flows):
        _generate_flow(i, interval, net, log_dir)  # Call flow generation function
        time.sleep(interval)

    info("Flow generation terminated... killing active iperf sessions...\n")

    # Killing iperf on all hosts
    for host in net.hosts:
        host.cmdPrint('killall -9 iperf')  # Clean up resources


# Main function

if __name__ == "__main__":
    log_dir = "/home/jyf/ryu/ryu/app/Experiment_ControlChannel/FlowGeneration/NoRandomLog"  # Directory for traffic monitoring logs
    topology = LinearTopo()  # Default parameters, linear topology
    default_controller = True
    controller_ip = "127.0.0.1"  # Localhost
    controller_port = 6633
    debug_flag = False
    debug_host = "localhost"
    debug_port = 6000

    # Read command-line arguments
    for arg in sys.argv:
        if arg.startswith("--controller"):  # Configure controller parameters
            default_controller = False
            arg = arg[2:]
            sub_arg = re.split("[,=]", arg)
            if "ip" in sub_arg:
                index = sub_arg.index("ip") + 1
                controller_ip = sub_arg[index]
            if "port" in sub_arg:
                index = sub_arg.index("port") + 1
                controller_port = int(sub_arg[index])

        elif arg.startswith("--topo"):  # Select topology type: linear, mesh, fat_tree
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

        elif arg.startswith("--debug"):  # Debug option (requires PyCharm Professional)
            debug_flag = True
            if len(arg) > 7:
                arg = arg[8:]
                sub_arg = re.split(":", arg)
                debug_host = sub_arg[0]
                debug_port = int(sub_arg[1])

            sys.path.append("/home/stainlee/Programs/pycharm-2017.3.3/debug-eggs/pycharm-debug.egg")

            import pydevd
            # Connect to PyCharm for debugging
            pydevd.settrace(debug_host, port=debug_port, stdoutToServer=True, stderrToServer=True)

    # Starting program
    setLogLevel('info')

    # Start Mininet
    if default_controller:
        print("Default parameters")
        net = Mininet(topo=topology, controller=DefaultController, host=CPULimitedHost, link=TCLink, switch=OVSSwitch, autoSetMacs=True)
    else:
        print("Configuring controller parameters")
        net = Mininet(topo=topology, build=False, autoSetMacs=True)
        net.addController('c1', controller=RemoteController, ip=controller_ip, protocol='tcp', port=controller_port)

    net.start()

    user_input = "QUIT"
    Mininet()
    # Run until user exits
    while True:
        try:
            user_input = input("Enter GEN (generate traffic)/CLI (Mininet CLI)/QUIT (exit program). Case insensitive: ")  # Three options: GEN/CLI/QUIT
        except EOFError as error:
            user_input = "QUIT"

        if user_input.upper() == "GEN":
            experiment_duration = int(input("Enter total duration in seconds (recommended 138): "))
            n_flows = int(input("Enter number of flows (recommended 46): "))
            info("Begin generating flows...\n")

            Generate_flows(n_flows, experiment_duration, net, log_dir)
        elif user_input.upper() == "CLI":  # Mininet CLI
            info("Entering CLI... To exit CLI, type: exit\n")
            CLI(net)
        elif user_input.upper() == "QUIT":  # Exit and clean up
            info("Terminating...\n")
            net.stop()
            break
        else:
            print("Command not found")
