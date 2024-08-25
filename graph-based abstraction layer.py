
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
        self.SwitcheGraph = nx.DiGraph()           #有向图，代表交换机网络
        self.PreSequenceSwitcheGraph =[]           #前几次连续采样的交换机网络，默认采样五次
        self.HostGraph = nx.DiGraph()              #有向图，代表主机网络
        self.Graph = nx.DiGraph()                  #有向图，整个网的网络（缺控制器的情况）
        self.PreSequenceGraph =[]                  #前几次连续采样的网络图，默认采样五次

        self.datapaths = {}                        #存储交换机实例信息
        self.dpip_map_name = {}                    #存储交换机的dpid与名字的映射关系，用于后续的比对替换。
        self.lldp_delay = {}                       #存储LLDP时延
        self.echo_delay = {}                       #存储echo往返时延
        self.port_stats = {}                       # 存端口的统计状态
        self.pre_port_stats = []                   # 存前几次端口的统计状态
        self.port_desc_stats = {}                  # 存端口的描述信息
        self.flow_stats = {}                       # 存流表的状态信息

        self.discover_spawn = hub.spawn(self._discover_topology)

    def _discover_topology(self):
            while True:
                if len(self.datapaths) >2:  # 交换机多于两个的时候开始计算
                    self.send_echo_request()
                    self.get_switches()              #1顺序不可以乱。
                    self.get_links()                 #2顺序不可以乱
                    self.get_hosts()                 #3顺序不可以乱
                    self._request_stats()            # 请求交换机端口和流表的状态信息
                    self.Create_graph_hostlinks()    #4顺序不可以乱
                    #print('PreSequenceGraph:',self.PreSequenceGraph)     #5顺序不可以乱

                    # nx.draw_networkx(self.Graph)
                    # plt.show()
                hub.sleep(8)

    # events = [event.EventSwitchEnter,event.EventSwitchLeave, event.EventPortAdd,event.EventPortDelete,event.EventLinkAdd, event.EventLinkDelete]
    # @set_ev_cls(events,[CONFIG_DISPATCHER,MAIN_DISPATCHER])
    # def get_topology(self, ev):
    #     self.get_switches()  # 顺序不可以乱。
    #     self.get_links()
    #     self.get_hosts()
    #     self.Create_graph_hostlinks()


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """
        当控制器和交换机开始的握手动作完成后，进行table-miss(默认流表)的添加
        """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        if datapath.id not in self.datapaths:
            self.datapaths[datapath.id] = datapath
        print("switch:%s connected"%datapath.id)        #交换机连接成功

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPStateChange,[MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):                            #增加，删减存放所有的datapath实例
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:                             #新增交换机
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:                           #删除交换机
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
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:   # ethertype为协议类型
            try:                                         #此部分内容是为了获得lldp的时间戳
                recv_timestamp = time.time()
                src_dpid, src_outport = LLDPPacket.lldp_parse(msg.data)  # 获取两个相邻交换机的源交换机dpid和port_no(与目的交换机相连的端口)
                dst_dpid = msg.datapath.id  # 获取目的交换机（第二个），因为来到控制器的消息是由第二个（目的）交换机上传过来的
                if self.switches is None:
                    self.switches = lookup_service_brick("switches")  # 获取交换机模块实例
                # 获得key（Port类实例）和data（PortData类实例）
                for port in self.switches.ports.keys():  # 开始获取对应交换机端口的发送时间戳
                    if src_dpid == port.dpid and src_outport == port.port_no:  # 匹配key
                        port_data = self.switches.ports[port]  # 获取满足key条件的values值PortData实例，内部保存了发送LLDP报文时的timestamp信息
                        send_timestamp = port_data.timestamp
                        if send_timestamp:
                            lldpdelay = recv_timestamp - send_timestamp
                            self.lldp_delay.setdefault(src_dpid, {})
                            self.lldp_delay[src_dpid][dst_dpid] = lldpdelay  # 将lldp存起来
                return
            except Exception as error:
                print("获取lldp时间戳失败：",error)
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

###############################################以下为网络拓扑构建################################################################
    def save_PreSequenceGraph(self, list_type, Graph, max_len=5):        #存储连续采样的网络图至列表，默认采样五次。
        if Graph not in list_type:
            if isinstance(Graph,nx.classes.digraph.DiGraph):
                preGraph=Graph.copy()                      #对图进行深度拷贝。类似于时间戳。
            else:
                preGraph = copy.deepcopy(Graph)            #可以对其它数据元素进行深度拷贝
            list_type.append(preGraph)
        if len(list_type) > max_len:
            list_type.pop(0)

    def get_switches(self, Dpid=None):
        switch_list = get_switch(self.topology_api_app, Dpid)  # 1.只要交换机与控制器联通，就可以获取
        for num,switch in enumerate(switch_list):
            dpid = switch.dp.id
            name='s{}'.format(num+1)
            self.dpip_map_name.update({dpid:name})       #备注，这里dpid和name是一一对应的，不存在一对多所以才可以这样用。不然相当于更新。
            ports=[]
            for port in switch.ports:
                ports.append(port.port_no)
            self.SwitcheGraph.add_node(name,dpid=dpid,ports=ports,links={})                  # 得到交换机和它的所有端口的映射。
        #print('更新交换机节点及属性：',self.SwitcheGraph.nodes(data=True))

    def get_links(self, Dpid=None):
        link_lists = get_link(self.topology_api_app, Dpid)     # -需要在控制台增加：-observe-links

        for link in link_lists:
            src = link.src
            dst = link.dst

            nodeattr=nx.get_node_attributes(self.SwitcheGraph,'dpid')   #得到节点和指定的属性：s1 1
            for name,dpid in nodeattr.items():
                if dpid==src.dpid:
                    value={(src.dpid, dst.dpid):(src.port_no, dst.port_no)}   #links的键值为：（src_dpid，dst_dpid）：（src_port，dst_port）
                    self.SwitcheGraph.nodes[name]['links'].update(value)    #通过顶点的 name 属性来查看顶点的其他属性，并用updata更新节点
            ## 以下内容是增加交换机的边
            s = self.dpip_map_name[src.dpid]
            d = self.dpip_map_name[dst.dpid]

            link_delay=self.get_link_delay(src.dpid,dst.dpid)                               #得到交换机之间的延迟。
            packet_loss=self.get_link_loss(src.dpid,dst.dpid)                               #得到交换机之间的loss。
            CurrSpeed,MaxSpeed=self.get_port_speed(src.dpid,dst.dpid)              # 得到交换机链路之间的端口速率信息（带宽）和最大速率信息(curr_speed,max_speed)
            link_throughput=self.get_link_throughput(src.dpid,dst.dpid)                      #得到交换机之间的吞吐量，当前的速率信息。

            self.SwitcheGraph.add_edge(s, d,delay=link_delay,loss=packet_loss,throughput=link_throughput,curr_speed=CurrSpeed)  #延迟，丢包率，当前吞吐量，和端口速率

            self.save_PreSequenceGraph(self.PreSequenceSwitcheGraph,self.SwitcheGraph,5)  # 存储连续采样的交换机网络图至列表，默认采样五次。

    def get_hosts(self, Dpid=None):
        host_lists = get_host(self.topology_api_app)  # -需要ping才可以获取
        for num,host in enumerate(host_lists):
            Hport = host.port
            name = 'h{}'.format(num + 1)
            self.HostGraph.add_node(name,dpid=Hport.dpid,port=Hport.port_no,ip=host.ipv4,mac=host.mac)

    def Create_graph_hostlinks(self):     #创建总图，同时增加主机的边到总图。
        try:
            self.Graph= nx.union(self.SwitcheGraph,self.HostGraph)     #两个图进行融合，如果节点重复将会出错。

        except:
            print("两个图融合失败，出错！")
        # 以下内容是增加host到交换机的边。
        Host = nx.get_node_attributes(self.HostGraph, 'dpid')
        for name, dpid in Host.items():
            self.Graph.add_edge(name,self.dpip_map_name[dpid],delay=0,loss=0,throughput=0,curr_speed=0)#延迟，丢包率，吞吐量，和当前端口速率
            #print('name={},dpip_map_name={}'.format(name, self.dpip_map_name[dpid]))
        print('查看总图的节点：', self.Graph.nodes(data=True))
        print('查看总图的边：', self.Graph.edges(data=True))

        self.save_PreSequenceGraph(self.PreSequenceGraph,self.Graph,5)                 #存储连续采样的整体网络图至列表，默认采样五次。

        try:
            nx.write_gml(self.Graph, "/home/jyf/Desktop/test.gml")   #存储会出现错误，此处无法使用。可能需要自定义的方式存储。
        except:
            print("将图存储至本地的时候出错！")
###############################################以下为延迟信息################################################################

# 由控制器向交换机发送echo报文，同时记录此时时间
    def send_echo_request(self):
        # 循环遍历交换机，逐一向存在的交换机发送echo探测报文
        for datapath in self.datapaths.values():
            parser = datapath.ofproto_parser
            echo_req = parser.OFPEchoRequest(datapath, data=bytes("%.12f" % time.time(), encoding="utf8"))  # 获取当前时间
            datapath.send_msg(echo_req)
            # 每隔0.5秒向下一个交换机发送echo报文，防止回送报文同时到达控制器
            hub.sleep(0.5)

    # 交换机向控制器的echo请求回应报文，收到此报文时，控制器通过当前时间-时间戳，计算出往返时延
    @set_ev_cls(ofp_event.EventOFPEchoReply, [MAIN_DISPATCHER, CONFIG_DISPATCHER])
    def echo_reply_handler(self, ev):
        now_timestamp = time.time()
        try:
            echo_delay = now_timestamp - eval(ev.msg.data)
            # 将交换机对应的echo时延写入字典保存起来，也是交换机到控制器的时延。
            self.echo_delay[ev.msg.datapath.id] = echo_delay        #echo时延存起来
            #print("echo_delay:",echo_delay)
        except Exception as error:
            print("echo时延出错：",error)
            return

    def get_link_delay(self, src_dpid, dst_dpid):        #得到交换机之间的时延
        try:
            fwd_delay = self.lldp_delay[src_dpid][dst_dpid]
            re_delay = self.lldp_delay[dst_dpid][src_dpid]
            src_latency = self.echo_delay[src_dpid]
            dst_latency = self.echo_delay[dst_dpid]
            delay = ((fwd_delay + re_delay - src_latency - dst_latency) / 2)* 1000  # ms转化为毫秒
            #print("delay", delay)
            return max(delay, 0)
        except:
            print("没有得到交换机之间的时延，出错")
            return 0
###############################################以下为吞吐量，带宽等信息，需要网络中有流量################################################################
    def _request_stats(self):     #请求交换机端口和流表的状态，统计带宽等信息。
        for datapath in self.datapaths.values():
            self.logger.debug('send stats request: %016x', datapath.id)
            ofp = datapath.ofproto
            ofp_parser = datapath.ofproto_parser

            req = ofp_parser.OFPFlowStatsRequest(datapath)                     #单个流统计请求
            datapath.send_msg(req)

            req = ofp_parser.OFPPortDescStatsRequest(datapath, 0)                 # 1. 端口描述请求
            datapath.send_msg(req)

            req = ofp_parser.OFPPortStatsRequest(datapath, 0, ofp.OFPP_ANY)    #端口统计请求，请求所有端口
            datapath.send_msg(req)
            hub.sleep(10)                 #担心状态信息请求的太快了。请求间隔就是数据采样间隔

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):                  #存储单个flow的状态，暂时没用到，以备后面用，比如匹配端口，ip，流表存在的时间。
        dpid = ev.msg.datapath.id
        body = ev.msg.body
        for stat in body:
            table_id=stat.table_id
            key = (dpid, table_id)
            value = (stat.duration_sec, stat.duration_nsec,stat.priority,stat.idle_timeout, stat.hard_timeout,
                     stat.flags,stat.cookie, stat.packet_count, stat.byte_count,stat.match, stat.instructions)
            self.flow_stats[key] = value
        #print('flow_stats:', self.flow_stats)


    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)         #交换机用此消息响应端口统计请求。
    def port_stats_reply_handler(self, ev):
        dpid = ev.msg.datapath.id
        body = ev.msg.body
        for stat in body:
            port_no = stat.port_no
            if port_no != ofproto_v1_3.OFPP_LOCAL:                 #不能是本地端口
                key = (dpid, port_no)
                value = (stat.tx_bytes, stat.rx_bytes, stat.tx_packets, stat.rx_packets,
                         stat.rx_errors, stat.tx_errors, stat.duration_sec, stat.duration_nsec,
                         stat.tx_dropped, stat.rx_dropped, stat.rx_over_err, stat.rx_crc_err,
                         stat.rx_frame_err, stat.collisions)
                self.port_stats[key] = value

        self.save_PreSequenceGraph(self.pre_port_stats, self.port_stats, 5)       ##存储连续采样的端口状态至列表，默认采样五次。
        #print('port_stats:',self.port_stats)            #{(dpid, port_no):((stat.tx_bytes, stat.rx_bytes,...)}

    def get_link_loss(self, src_dpid, dst_dpid):        #得到交换机链路之间的丢包率
        try:

            linkattr = nx.get_node_attributes(self.SwitcheGraph, 'links')
            for links in linkattr.values():                    # 得到节点和指定的属性：s1 links的键值为：（src_dpid，dst_dpid）：（src_port，dst_port）
                for k, v in links.items():
                    if k == (src_dpid, dst_dpid):
                        src_port = v[0]       # 源端口
                        dst_port = v[1]       # 目的端口
                        src_tx_packets = self.port_stats[(src_dpid, src_port)][2]    #[2]tx_packets传送的包数量,源端口
                        dst_rx_packets = self.port_stats[(dst_dpid, dst_port)][3]    #[3]rx_packets收到的包数量，目的端口
                        if dst_rx_packets!=0:
                            loss = abs((src_tx_packets - dst_rx_packets) / float(src_tx_packets))* 100  #丢包率不知道是否可以直接用：rx_dropped，tx_errors
                        #print('loss:',loss)
                        return max(loss, 0)
        except:
            print("没有得到交换机之间的loss，出错")
            return 0


    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        """ 存储端口描述信息, 见OFPPort类, 配置、状态、当前速度"""
        dpid = ev.msg.datapath.id
        body = ev.msg.body

        for p in body:
            port_no = p.port_no
            if port_no != ofproto_v1_3.OFPP_LOCAL:                 #不能是本地端口
                key = (dpid, port_no)
                value =(p.hw_addr,p.name, p.config,p.state, p.curr,p.advertised,p.supported, p.peer, p.curr_speed,p.max_speed)
                self.port_desc_stats[key] = value
        #print('port_desc_stats:', self.port_desc_stats)

    def get_port_speed(self, src_dpid, dst_dpid):        #得到交换机链路之间的端口当前速率信息和最大速率信息
        try:
            linkattr = nx.get_node_attributes(self.SwitcheGraph, 'links')
            for links in linkattr.values():                    # 得到节点和指定的属性：s1 links的键值为：（src_dpid，dst_dpid）：（src_port，dst_port）
                for k, v in links.items():
                    if k == (src_dpid, dst_dpid):
                        src_port = v[0]  # 源端口
                        dst_port = v[1]  # 目的端口,后续没用。
                        curr_speed = max(self.port_desc_stats[(src_dpid, src_port)][-2], 0)    #端口当前速率信息,详细解释需要看openflow官方文档。不然会出现理解偏差。
                        max_speed = max(self.port_desc_stats[(src_dpid, src_port)][-1], 0)     #端口最大速率信息
                        #print('curr_speed and max_speed:',curr_speed,max_speed)
                        return curr_speed/10**3,max_speed/10**3          #由比特率：kbps，转为Mbit/s
        except:
            print("没有得到交换机之间的当前速率信息和最大速率信息，出错")
            return 0,0

    def get_link_throughput(self, src_dpid, dst_dpid):        #得到交换机链路之间的丢包率
        try:
            if len(self.pre_port_stats)>=2:           #pre_port_stats至少存储了两个图
                linkattr = nx.get_node_attributes(self.SwitcheGraph, 'links')
                for links in linkattr.values():                    # 得到节点和指定的属性：s1 links的键值为：（src_dpid，dst_dpid）：（src_port，dst_port）
                    for k, v in links.items():
                        if k == (src_dpid, dst_dpid):
                            src_port = v[0]       # 源端口
                            dst_port = v[1]       # 目的端口
                            src_tx_bytes = self.port_stats[(src_dpid, src_port)][0]    #tx_bytes,Number of transmitted bytes. 源端口吐出量
                            src_rx_bytes = self.port_stats[(src_dpid, src_port)][1]    #rx_bytes， Number of received bytes.  源端口接收量
                            src_duration_sec = self.port_stats[(src_dpid, src_port)][6]    #duration_sec,Time port has been alive in seconds.
                            src_duration_nsec = self.port_stats[(src_dpid, src_port)][7]    #duration_nsec，Time port has been alive in nanoseconds beyond duration_sec.

                            #默认采样五次，这里不论是第几次采样均将最早的值用来计算，可能是第二次采样，第三次采样至第五次采样开始稳定。
                            presrc_tx_bytes = self.pre_port_stats[0][(src_dpid, src_port)][0]    #tx_bytes,Number of transmitted bytes. 源端口吐出量
                            presrc_rx_bytes = self.pre_port_stats[0][(src_dpid, src_port)][1]    #rx_bytes， Number of received bytes.  源端口接收量
                            presrc_duration_sec = self.pre_port_stats[0][(src_dpid, src_port)][6]    #duration_sec,Time port has been alive in seconds.
                            presrc_duration_nsec = self.pre_port_stats[0][(src_dpid, src_port)][7]    #duration_nsec，Time port has been alive in nanoseconds beyond duration_sec.

                            #吞吐量等于端口现在的量减去以前的量除以时间，得到单位时间的量为吞吐量。
                            s=(src_tx_bytes + src_rx_bytes - presrc_tx_bytes - presrc_rx_bytes)* 8/10**6
                            time=src_duration_sec + src_duration_nsec/ (10 ** 9) - presrc_duration_sec - presrc_duration_nsec/ (10 ** 9)         #将纳秒换算为秒
                            throughput = s/time          #单位为：Mbit/s

                            #print('throughput:',throughput)
                            return max(throughput, 0)
        except:
            print("没有得到交换机之间的throughput，出错")
            return 0