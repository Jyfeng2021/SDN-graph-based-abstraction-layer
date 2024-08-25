#!/usr/bin/env python

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.node import IVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from subprocess import call

def myNetwork():

    net = Mininet( topo=None,
                   build=False,
                   ipBase='10.0.0.0/8')

    info( '*** Adding controller\n' )
    c0=net.addController(name='c0',
                      controller=RemoteController,
                      ip='127.0.0.1',
                      protocol='tcp',
                      port=6633)

    info( '*** Add switches\n')
    s3 = net.addSwitch('s3', cls=OVSKernelSwitch, dpid='0000000000000003')
    s7 = net.addSwitch('s7', cls=OVSKernelSwitch, dpid='0000000000000007')
    s2 = net.addSwitch('s2', cls=OVSKernelSwitch, dpid='0000000000000002')
    s4 = net.addSwitch('s4', cls=OVSKernelSwitch, dpid='0000000000000004')
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch, dpid='0000000000000001')
    s5 = net.addSwitch('s5', cls=OVSKernelSwitch, dpid='0000000000000005')
    s6 = net.addSwitch('s6', cls=OVSKernelSwitch, dpid='0000000000000006')

    info( '*** Add hosts\n')
    h2 = net.addHost('h2', cls=Host, ip='10.0.0.2', defaultRoute=None)
    h1 = net.addHost('h1', cls=Host, ip='10.0.0.1', defaultRoute=None)
    h4 = net.addHost('h4', cls=Host, ip='10.0.0.4', defaultRoute=None)
    h3 = net.addHost('h3', cls=Host, ip='10.0.0.3', defaultRoute=None)

    info( '*** Add links\n')
    s7s5 = {'bw':10,'delay':'5','loss':5,'jitter':'5','speedup':5}
    net.addLink(s7, s5, cls=TCLink , **s7s5)
    s5s4 = {'bw':10}
    net.addLink(s5, s4, cls=TCLink , **s5s4)
    s4s3 = {'bw':10}
    net.addLink(s4, s3, cls=TCLink , **s4s3)
    s3s2 = {'bw':10}
    net.addLink(s3, s2, cls=TCLink , **s3s2)
    s2s1 = {'bw':10}
    net.addLink(s2, s1, cls=TCLink , **s2s1)
    s1s7 = {'bw':10}
    net.addLink(s1, s7, cls=TCLink , **s1s7)
    s1s6 = {'bw':10}
    net.addLink(s1, s6, cls=TCLink , **s1s6)
    s6s2 = {'bw':10}
    net.addLink(s6, s2, cls=TCLink , **s6s2)
    s6s3 = {'bw':10}
    net.addLink(s6, s3, cls=TCLink , **s6s3)
    s6s4 = {'bw':10}
    net.addLink(s6, s4, cls=TCLink , **s6s4)
    s6s5 = {'bw':10}
    net.addLink(s6, s5, cls=TCLink , **s6s5)
    s1h1 = {'bw':10}
    net.addLink(s1, h1, cls=TCLink , **s1h1)
    s3h2 = {'bw':10}
    net.addLink(s3, h2, cls=TCLink , **s3h2)
    s4h3 = {'bw':10}
    net.addLink(s4, h3, cls=TCLink , **s4h3)
    s5h4 = {'bw':10}
    net.addLink(s5, h4, cls=TCLink , **s5h4)

    info( '*** Starting network\n')
    net.build()
    info( '*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info( '*** Starting switches\n')
    net.get('s3').start([c0])
    net.get('s7').start([c0])
    net.get('s2').start([c0])
    net.get('s4').start([c0])
    net.get('s1').start([c0])
    net.get('s5').start([c0])
    net.get('s6').start([c0])

    info( '*** Post configure switches and hosts\n')

    CLI(net)
