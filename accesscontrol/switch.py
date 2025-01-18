from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
'''
Implementation of self-learning switch
It combines handshake data analysis, flow table delivery, forwarding table learning and other operations
'''


class Switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_table = {}                                                    # initialized to empty

    def doflow(self, datapath, command, priority, match, actions):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        inst = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        req = ofp_parser.OFPFlowMod(datapath=datapath, command=command,
                                    priority=priority, match=match, instructions=inst)
        datapath.send_msg(req)

       @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        # add table-miss
        command = ofp.OFPFC_ADD
        match = ofp_parser.OFPMatch()
        actions = [ofp_parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.doflow(datapath, command, 0, match, actions)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        global src, dst
        msg = ev.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        dpid = datapath.id

        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        for p in pkt.protocols:
            if p.protocol_name == 'ethernet':
                src = p.src
                dst = p.dst
                print('src:{0}  dst:{1}'.format(src, dst))


        # {'dpid':{'src':in_port, 'dst':out_port}}
        self.mac_table.setdefault(dpid, {})
        self.mac_table[dpid][src] = in_port

        ## If there is a corresponding relationship between the forwarding table, it will be carried out according to the forwarding table; If no, you need to broadcast the mac address corresponding to the destination ip address
        # 若转发表存在对应关系，就按照转发表进行；没有就需要广播得到目的ip对应的mac地址
        if dst in self.mac_table[dpid]:
            out_port = self.mac_table[dpid][dst]
        else:
            out_port = ofp.OFPP_FLOOD
        actions = [ofp_parser.OFPActionOutput(out_port)]

        # 如果执行的动作不是flood，那么此时应该依据流表项进行转发操作，所以需要添加流表到交换机
       #If the action is not flood, the flow table is forwarded based on the flow entry. Therefore, you need to add the flow table to the switch
        if out_port != ofp.OFPP_FLOOD:
            match = ofp_parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            command = ofp.OFPFC_ADD
            self.doflow(datapath=datapath, command=command, priority=1,
                        match=match, actions=actions)

        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
            data = msg.data
 
        out = ofp_parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                      in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
