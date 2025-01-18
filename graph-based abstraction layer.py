
import time
import copy
import networkx as nx
from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.controller import ofp_event
from ryu.topology.api import get_switch, get_link,get_host
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import ethernet
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types

from ryu.lib.packet import arp, ipv4
from ryu.topology import event, switches
from ryu.topology.switches import LLDPPacket
from ryu.base.app_manager import lookup_service_brick
# import os
# os.environ['MPLCONFIGDIR'] = os.getcwd() + "/configs/"
# import matplotlib.pyplot as plt

class TopoDiscover(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TopoDiscover, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.name = "TopoDiscover"
        self.switches = lookup_service_brick('switches')
        self.SwitcheGraph = nx.DiGraph()          # Directed graph, which represents the switch network
        self.PreSequenceSwitcheGraph =[]           # Continuous sampling of the switch network,  default sampling five times
        self.HostGraph = nx.DiGraph()              # Directed graph, which stands for host network
        self.Graph = nx.DiGraph()                  # Directed graph, a network of entire networks，
        self.PreSequenceGraph =[]             # Continuous sampling of the network , default sampling five times

        self.datapaths = {}                            # Store switch instance information
        self.dpip_map_name = {}                # Store the mapping between the dpid and the name of the switch
        self.lldp_delay = {}                           #LLDP latency
        self.echo_delay = {}                         #echo Round-trip delay
        self.port_stats = {}                           #status of a port
        self.pre_port_stats = []                   # The statistical status of the previous ports is saved
        self.port_desc_stats = {}                 # Description of the port
        self.flow_stats = {}                           # Storage flow-table status information

        self.discover_spawn = hub.spawn(self._discover_topology)

    def _discover_topology(self):
            while True:
                if len(self.datapaths) >2:         # Counting starts when there are more than two switches
                    self.send_echo_request()
                    self.get_switches()             # The order cannot be chaotic.     
                    self.get_links()                 
                    self.get_hosts()                 
                    self._request_stats()                    #Requests switch port and flow table status information
                    self.Create_graph_hostlinks()   
                    #print('PreSequenceGraph:',self.PreSequenceGraph)    

                    # nx.draw_networkx(self.Graph)
                    # plt.show()
                hub.sleep(8)


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
    When the initial handshake between the controller and the switch is complete, the table-MISS (default flow table) is added
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        if datapath.id not in self.datapaths:
            self.datapaths[datapath.id] = datapath
        print("switch:%s connected"%datapath.id)       # The switch is connected successfully

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPStateChange,[MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):                           # Add, delete and store all datapath instances
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:                              # Add a switch
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:                            # Delete switch
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        # datapath = msg.datapath
        # ofproto = datapath.ofproto
        # parser = datapath.ofproto_parser
        # in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:   # ethertype Indicates a protocol type
            try:                                         # This section is to get the timestamp of lldp
                recv_timestamp = time.time()
                src_dpid, src_outport = LLDPPacket.lldp_parse(msg.data)    # Get the source switch dpid and port_no(port connected to the destination switch)
                dst_dpid = msg.datapath.id                                                       # Get the destination Switch (the second)
                if self.switches is None:
                    self.switches = lookup_service_brick("switches")                             # Get the switch module instance
       
                for port in self.switches.ports.keys():                                                         # Start to get the send timestamp of the corresponding switch port
                    if src_dpid == port.dpid and src_outport == port.port_no:        
                        port_data = self.switches.ports[port]                                              
                        send_timestamp = port_data.timestamp
                        if send_timestamp:
                            lldpdelay = recv_timestamp - send_timestamp
                            self.lldp_delay.setdefault(src_dpid, {})
                            self.lldp_delay[src_dpid][dst_dpid] = lldpdelay                           # Save lldp
                return
            except Exception as error:
                print("Failed to obtain the lldp timestamp:",error)
                return

        dst = eth.dst
        src = eth.src

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,priority=priority, match=match,instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,match=match, instructions=inst)
        datapath.send_msg(mod)

###############################################The following is the network topology construction################################################################
    def save_PreSequenceGraph(self, list_type, Graph, max_len=5):      # Store consecutively sampled network graph to list, default sampling five times.
        if Graph not in list_type:
            if isinstance(Graph,nx.classes.digraph.DiGraph):
                preGraph=Graph.copy()                         # Make a deep copy of the graph.
            else:
                preGraph = copy.deepcopy(Graph)           
            list_type.append(preGraph)
        if len(list_type) > max_len:
            list_type.pop(0)

    def get_switches(self, Dpid=None):
        switch_list = get_switch(self.topology_api_app, Dpid)  
        for num,switch in enumerate(switch_list):
            dpid = switch.dp.id
            name='s{}'.format(num+1)
            self.dpip_map_name.update({dpid:name})     
            ports=[]
            for port in switch.ports:
                ports.append(port.port_no)
            self.SwitcheGraph.add_node(name,dpid=dpid,ports=ports,links={})                  #Get a map of the switch and all its ports.
        #print('更新交换机节点及属性：',self.SwitcheGraph.nodes(data=True))

    def get_links(self, Dpid=None):
        link_lists = get_link(self.topology_api_app, Dpid)     #Console command: -observe-links

        for link in link_lists:
            src = link.src
            dst = link.dst

            nodeattr=nx.get_node_attributes(self.SwitcheGraph,'dpid')   
            for name,dpid in nodeattr.items():
                if dpid==src.dpid:
                    value={(src.dpid, dst.dpid):(src.port_no, dst.port_no)}   #links key and value：（src_dpid，dst_dpid）：（src_port，dst_port）
                    self.SwitcheGraph.nodes[name]['links'].update(value)    # View the other attributes and update the node
            ## The following is to add edges to the switch
            s = self.dpip_map_name[src.dpid]
            d = self.dpip_map_name[dst.dpid]

            link_delay=self.get_link_delay(src.dpid,dst.dpid)                               #Get a delay between switches.
            packet_loss=self.get_link_loss(src.dpid,dst.dpid)                               #Get a loss between switches.
            CurrSpeed,MaxSpeed=self.get_port_speed(src.dpid,dst.dpid)              # Get the link rate information of the switch(curr_speed,max_speed)
            link_throughput=self.get_link_throughput(src.dpid,dst.dpid)                    # Get throughput

            self.SwitcheGraph.add_edge(s, d,delay=link_delay,loss=packet_loss,throughput=link_throughput,curr_speed=CurrSpeed)  #Latency,  loss ,  throughput, and port rate

            self.save_PreSequenceGraph(self.PreSequenceSwitcheGraph,self.SwitcheGraph,5)  # Get the situation before the switch

    def get_hosts(self, Dpid=None):
        host_lists = get_host(self.topology_api_app)  # ping
        for num,host in enumerate(host_lists):
            Hport = host.port
            name = 'h{}'.format(num + 1)
            self.HostGraph.add_node(name,dpid=Hport.dpid,port=Hport.port_no,ip=host.ipv4,mac=host.mac)

    def Create_graph_hostlinks(self):    
        try:
            self.Graph= nx.union(self.SwitcheGraph,self.HostGraph)     # Merge the two graphs.

        except:
            print("Two graphs failed to merge, error!")
     
        Host = nx.get_node_attributes(self.HostGraph, 'dpid')
        for name, dpid in Host.items():
            self.Graph.add_edge(name,self.dpip_map_name[dpid],delay=0,loss=0,throughput=0,curr_speed=0)    #Latency,  loss ,  throughput, and port rate
            #print('name={},dpip_map_name={}'.format(name, self.dpip_map_name[dpid]))
        print('View the nodes of the graph：', self.Graph.nodes(data=True))
        print('View the edges of the graph：', self.Graph.edges(data=True))

        self.save_PreSequenceGraph(self.PreSequenceGraph,self.Graph,5)                 
        try:
            nx.write_gml(self.Graph, "/home/jyf/Desktop/test.gml")  
        except:
            print("Error saving graph to local!")
###############################################The following is the delay information################################################################

# # The controller sends echo packets to the switch and records the time
    def send_echo_request(self):
        for datapath in self.datapaths.values():
            parser = datapath.ofproto_parser
            echo_req = parser.OFPEchoRequest(datapath, data=bytes("%.12f" % time.time(), encoding="utf8"))              # Get the current time
            datapath.send_msg(echo_req)
            # echo packets are sent to the next switch every 0.5 seconds to prevent the Echo packets from reaching the controller at the same time
            hub.sleep(0.5)

    ## Indicates the echo response packet sent by the switch to the controller. After receiving the Echo response packet, the controller calculates the round trip delay based on the current time-timestamp
    @set_ev_cls(ofp_event.EventOFPEchoReply, [MAIN_DISPATCHER, CONFIG_DISPATCHER])
    def echo_reply_handler(self, ev):
        now_timestamp = time.time()
        try:
            echo_delay = now_timestamp - eval(ev.msg.data)
            self.echo_delay[ev.msg.datapath.id] = echo_delay        #echo  delay saved
            #print("echo_delay:",echo_delay)
        except Exception as error:
            print("echo delay error:",error)
            return

    def get_link_delay(self, src_dpid, dst_dpid):      # Get the delay between switches
        try:
            fwd_delay = self.lldp_delay[src_dpid][dst_dpid]
            re_delay = self.lldp_delay[dst_dpid][src_dpid]
            src_latency = self.echo_delay[src_dpid]
            dst_latency = self.echo_delay[dst_dpid]
            delay = ((fwd_delay + re_delay - src_latency - dst_latency) / 2)* 1000  # ms
            #print("delay", delay)
            return max(delay, 0)
        except:
            print("The delay between switches is not obtained. An error occurred")
            return 0
###############################################The following is the throughput and bandwidth information, which requires traffic on the network################################################################
    def _request_stats(self):     # Request switch port and flow table status
        for datapath in self.datapaths.values():
            self.logger.debug('send stats request: %016x', datapath.id)
            ofp = datapath.ofproto
            ofp_parser = datapath.ofproto_parser

            req = ofp_parser.OFPFlowStatsRequest(datapath)                    # Stream statistics request
            datapath.send_msg(req)

            req = ofp_parser.OFPPortDescStatsRequest(datapath, 0)               # Port description request
            datapath.send_msg(req)

            req = ofp_parser.OFPPortStatsRequest(datapath, 0, ofp.OFPP_ANY)    # Port statistics request
            datapath.send_msg(req)
            hub.sleep(10)                 #Data sampling interval

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):                  # Stores the state of a single flow
        dpid = ev.msg.datapath.id
        body = ev.msg.body
        for stat in body:
            table_id=stat.table_id
            key = (dpid, table_id)
            value = (stat.duration_sec, stat.duration_nsec,stat.priority,stat.idle_timeout, stat.hard_timeout,
                     stat.flags,stat.cookie, stat.packet_count, stat.byte_count,stat.match, stat.instructions)
            self.flow_stats[key] = value
        #print('flow_stats:', self.flow_stats)


    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)     
    def port_stats_reply_handler(self, ev):
        dpid = ev.msg.datapath.id
        body = ev.msg.body
        for stat in body:
            port_no = stat.port_no
            if port_no != ofproto_v1_3.OFPP_LOCAL:            
                key = (dpid, port_no)
                value = (stat.tx_bytes, stat.rx_bytes, stat.tx_packets, stat.rx_packets,
                         stat.rx_errors, stat.tx_errors, stat.duration_sec, stat.duration_nsec,
                         stat.tx_dropped, stat.rx_dropped, stat.rx_over_err, stat.rx_crc_err,
                         stat.rx_frame_err, stat.collisions)
                self.port_stats[key] = value

        self.save_PreSequenceGraph(self.pre_port_stats, self.port_stats, 5)    
        #print('port_stats:',self.port_stats)            #{(dpid, port_no):((stat.tx_bytes, stat.rx_bytes,...)}

    def get_link_loss(self, src_dpid, dst_dpid):      Get the packet loss rate between switch links
        try:

            linkattr = nx.get_node_attributes(self.SwitcheGraph, 'links')
            for links in linkattr.values():                    # s1 links key and value：（src_dpid，dst_dpid）：（src_port，dst_port）
                for k, v in links.items():
                    if k == (src_dpid, dst_dpid):
                        src_port = v[0]       # Source port
                        dst_port = v[1]        # Destination port
                        src_tx_packets = self.port_stats[(src_dpid, src_port)][2]    #[2]tx_packets The number of packets transmitted by the source port,
                        dst_rx_packets = self.port_stats[(dst_dpid, dst_port)][3]    #[3]rx_packets The number of packets transmitted by the Destination port
                        if dst_rx_packets!=0:
                            loss = abs((src_tx_packets - dst_rx_packets) / float(src_tx_packets))* 100   
                        #print('loss:',loss)
                        return max(loss, 0)
        except:
            print("Did not get the loss between switches, error")
            return 0


    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        """ For the description of the storage port, see the OFPPort class, Configuration, Status, and Current Speed"""
        dpid = ev.msg.datapath.id
        body = ev.msg.body

        for p in body:
            port_no = p.port_no
            if port_no != ofproto_v1_3.OFPP_LOCAL:                 
                key = (dpid, port_no)
                value =(p.hw_addr,p.name, p.config,p.state, p.curr,p.advertised,p.supported, p.peer, p.curr_speed,p.max_speed)
                self.port_desc_stats[key] = value
        #print('port_desc_stats:', self.port_desc_stats)

    def get_port_speed(self, src_dpid, dst_dpid):        #Get the current rate information and maximum rate information of ports between switch links
        try:
            linkattr = nx.get_node_attributes(self.SwitcheGraph, 'links')
            for links in linkattr.values():                    # s1 links key：（src_dpid，dst_dpid）：（src_port，dst_port）
                for k, v in links.items():
                    if k == (src_dpid, dst_dpid):
                        src_port = v[0]            #Source port
                        dst_port = v[1]           # Destination port
                        curr_speed = max(self.port_desc_stats[(src_dpid, src_port)][-2], 0)    # Current port rate
                        max_speed = max(self.port_desc_stats[(src_dpid, src_port)][-1], 0)     # Maximum port speed
                        #print('curr_speed and max_speed:',curr_speed,max_speed)
                        return curr_speed/10**3,max_speed/10**3          #kbps Turn into Mbit/s
        except:
            print("The current rate and maximum rate between switches are not obtained. An error occurs. Procedure")
            return 0,0

    def get_link_throughput(self, src_dpid, dst_dpid):        #Get the packet loss rate between switch links
        try:
            if len(self.pre_port_stats)>=2:           #pre_port_stats至少存储了两个图
                linkattr = nx.get_node_attributes(self.SwitcheGraph, 'links')
                for links in linkattr.values():                    # s1 links key：（src_dpid，dst_dpid）：（src_port，dst_port）
                    for k, v in links.items():
                        if k == (src_dpid, dst_dpid):
                            src_port = v[0]       
                            dst_port = v[1]      
                            src_tx_bytes = self.port_stats[(src_dpid, src_port)][0]    #tx_bytes,Number of transmitted bytes. 
                            src_rx_bytes = self.port_stats[(src_dpid, src_port)][1]    #rx_bytes， Number of received bytes.  
                            src_duration_sec = self.port_stats[(src_dpid, src_port)][6]    #duration_sec,Time port has been alive in seconds.
                            src_duration_nsec = self.port_stats[(src_dpid, src_port)][7]    #duration_nsec，Time port has been alive in nanoseconds beyond duration_sec.

                            #。
                            presrc_tx_bytes = self.pre_port_stats[0][(src_dpid, src_port)][0]    #tx_bytes,Number of transmitted bytes.
                            presrc_rx_bytes = self.pre_port_stats[0][(src_dpid, src_port)][1]    #rx_bytes， Number of received bytes. 
                            presrc_duration_sec = self.pre_port_stats[0][(src_dpid, src_port)][6]    #duration_sec,Time port has been alive in seconds.
                            presrc_duration_nsec = self.pre_port_stats[0][(src_dpid, src_port)][7]    #duration_nsec，Time port has been alive in nanoseconds beyond duration_sec.

                        
                            s=(src_tx_bytes + src_rx_bytes - presrc_tx_bytes - presrc_rx_bytes)* 8/10**6
                            time=src_duration_sec + src_duration_nsec/ (10 ** 9) - presrc_duration_sec - presrc_duration_nsec/ (10 ** 9)       
                            throughput = s/time          #Mbit/s

                            #print('throughput:',throughput)
                            return max(throughput, 0)
        except:
            print("Didn't get throughput between switches, error")
            return 0
