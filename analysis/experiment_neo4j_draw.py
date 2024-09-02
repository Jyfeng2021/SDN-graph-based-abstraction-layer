

# import networkx as nx
# from matplotlib import pyplot as plt
import time
from py2neo import Node, Relationship, Graph, NodeMatcher, RelationshipMatcher
graph = Graph("http://localhost:7474", auth=("neo4j", "jyfjyfjyf"),name="neo4j")


def linear(n):
    # 初始化线性拓扑
    h = []
    s = []
    link=[]
    for i in range(1, n + 1):
        str_h = 'h' + str(i)
        str_s = 's' + str(i)
        h.append(str_h)
        s.append(str_s)
        link.append((h[-1], s[-1]))
        link.append((s[-1], h[-1]))
        if i > 1:
            link.append((s[i - 1], s[i - 2]))
            link.append((s[i - 2], s[i - 1]))
    return link,s+h,len(h)         #返回连接关系和节点和节点数量。

def mesh(n):
    # Initialize mesh topology
    h = []
    s = []
    link=[]
    for i in range(1, n+1):
        str_h = 'h' + str(i)
        str_s = 's' + str(i)
        h.append(str_h)
        s.append(str_s)
        link.append((h[-1], s[-1]))
        link.append((s[-1], h[-1]))
        for j in range(len(s)-1):
            link.append((s[j], s[-1]))
            link.append((s[-1], s[j]))
    return link,s+h,len(h)           #返回连接关系和节点。节点数量。

def Tree(n):   #n必须是偶数
    #Marking the number of switch for per level
    L1 = n;
    L2 = L1*2
    L3 = L2

    #Starting create the switch
    c = []    #core switch核心层
    a = []    #aggregate switch汇聚层
    e = []    #edge switch接入层
    h=[]
    links=[]

    #notice: switch label is a special data structure
    for i in range(L1):
        c_sw = 'c{}'.format(i+1)   #label from 1 to n,not start with 0
        c.append(c_sw)

    for i in range(L2):
        a_sw = 'a{}'.format(L1+i+1)
        a.append(a_sw)

    for i in range(L3):
        e_sw = 'e{}'.format(L1+L2+i+1)
        e.append(e_sw)

    #Starting create the link between switchs
    #first the first level and second level link
    for i in range(L1):
        c_sw = c[i]
        for j in range(L2):
            links.append((c_sw,a[j]))
            links.append((a[j],c_sw))

    #second the second level and third level link
    for i in range(L2):
        links.append((a[i],e[i]))
        links.append((e[i],a[i]))
        if not i%2:
            links.append((a[i],e[i+1]))
            links.append((e[i + 1],a[i]))
        else:
            links.append((a[i],e[i-1]))
            links.append((e[i - 1],a[i]))

    #Starting create the host and create link between switchs and hosts
    for i in range(L3):
        for j in range(2):
            hs = 'h{}'.format(i*2+j+1)
            links.append((e[i],hs))
            links.append((hs,e[i]))
            h.append(hs)

    return links,c+a+e+h,len(h)          #返回连接关系和节点。和节点数量。

def batch_create(graph, nodes_list, relations_list):
    """
        批量创建节点/关系,nodes_list和relations_list不同时为空即可
        特别的：当利用关系创建节点时，可使得nodes_list=[]
    :param graph: Graph()
    :param nodes_list: Node()集合
    :param relations_list: Relationship集合
    :return:
    """

    subgraph = Subgraph(nodes_list, relations_list)
    tx_ = graph.begin()
    tx_.create(subgraph)
    graph.commit(tx_)


# G=nx.DiGraph()
# links,nodes,num=Tree(4)
# G.add_nodes_from(nodes)
# G.add_edges_from(links)
#
# star_timestamp = time.time()
# path=nx.shortest_path(G,'h1','h8')
# delay = (time.time()-star_timestamp) *1000   #转化为毫秒 ms
#
# print("delay",delay,path)
# nx.draw_networkx(G)
# plt.show()

#以下内容为测试的。
#graph.delete_all()  # 先将数据库清空
# node_matcher = NodeMatcher(graph)  # 节点匹配器
# match = node_matcher.match('MATCH (a)--() RETURN a') # 查询结点
# print(list(match))


# node_matcher = NodeMatcher(graph)  # 节点匹配器
# h1 = node_matcher.match('Host',name='h1')  # 提取满足属性值的节点
# h4 = node_matcher.match('Host',name='h4')  # 提取满足属性值的节点
# node_to_node1 = Relationship(h1.first(),'link',h4.first())
# graph.create(node_to_node1)
# print(h1.first())

# node_matcher = NodeMatcher(graph)  # 节点匹配器
# nodes = node_matcher.match()   # 直接提取所有节点
# for node in nodes:
#     if node['name']=='h1':
#         print(node)
#
# cypher_1 = "MATCH (n:Host) RETURN n"

#以上内容为测试的。



number=512        #数量512
try:
    with open(r'/home/jyf/Desktop/Experiment/experiment/neo4j_linear.txt', 'a') as f1:
        for i in range(2,number,6):
            graph.delete_all()  # 先将数据库清空
            links,nodes,num=linear(i)      #生成网络拓扑
            end='h'+str(num)

            node_matcher = NodeMatcher(graph)  # 节点匹配器
            for node in nodes:
                node_h = Node('Host', name=node)
                graph.create(node_h)

            for link in links:
                node1 = node_matcher.match('Host', name=link[0])  # 提取满足属性值的节点
                node2 = node_matcher.match('Host', name=link[1])  # 提取满足属性值的节点
                node_to_node1 = Relationship(node1.first(),'link',node2.first())
                graph.create(node_to_node1)
                node_to_node2 = Relationship(node2.first(),'link',node1.first())
                graph.create(node_to_node2)

            star_timestamp = time.time()
            cypher_ = "MATCH (p1:Host{name:'h1'}),(p2:Host{name:'%s'}),p=shortestpath((p1)-[*]-(p2)) RETURN p"%(end)
            path = graph.run(cypher_).data()           #计算最短路径，并返回
            end_timestamp = time.time()
            delay = (end_timestamp-star_timestamp) *1000000   #转化为微秒，微秒（microsecond），时间单位:μs

            f1.write(str(delay) + '\n')
            print("delay",delay)
except:
    print("linear，出错")
time.sleep(1)

try:
    with open(r'/home/jyf/Desktop/Experiment/experiment/neo4j_mesh.txt', 'a') as f2:
        for i in range(2,number,6):
            graph.delete_all()  # 先将数据库清空
            links,nodes,num=mesh(i)      #生成网络拓扑
            end='h'+str(num)

            node_matcher = NodeMatcher(graph)  # 节点匹配器
            for node in nodes:
                node_h = Node('Host', name=node)
                graph.create(node_h)

            for link in links:
                node1 = node_matcher.match('Host', name=link[0])  # 提取满足属性值的节点
                node2 = node_matcher.match('Host', name=link[1])  # 提取满足属性值的节点
                node_to_node1 = Relationship(node1.first(),'link',node2.first())
                graph.create(node_to_node1)
                node_to_node2 = Relationship(node2.first(),'link',node1.first())
                graph.create(node_to_node2)

            star_timestamp = time.time()
            cypher_ = "MATCH (p1:Host{name:'h1'}),(p2:Host{name:'%s'}),p=shortestpath((p1)-[*]-(p2)) RETURN p"%(end)
            path = graph.run(cypher_).data()           #计算最短路径，并返回
            end_timestamp = time.time()
            delay = (end_timestamp-star_timestamp) *1000000   #转化为微秒，微秒（microsecond），时间单位:μs

            f2.write(str(delay) + '\n')
            print("delay",delay)
except:
    print("mesh，出错")
time.sleep(1)

try:
    with open(r'/home/jyf/Desktop/Experiment/experiment/neo4j_tree.txt', 'a') as f3:
        for i in range(2,number,6):
            graph.delete_all()  # 先将数据库清空
            links,nodes,num=Tree(i)      #生成网络拓扑
            end='h'+str(num)

            node_matcher = NodeMatcher(graph)  # 节点匹配器
            for node in nodes:
                node_h = Node('Host', name=node)
                graph.create(node_h)

            for link in links:
                node1 = node_matcher.match('Host', name=link[0])  # 提取满足属性值的节点
                node2 = node_matcher.match('Host', name=link[1])  # 提取满足属性值的节点
                node_to_node1 = Relationship(node1.first(),'link',node2.first())
                graph.create(node_to_node1)
                node_to_node2 = Relationship(node2.first(),'link',node1.first())
                graph.create(node_to_node2)

            star_timestamp = time.time()
            cypher_ = "MATCH (p1:Host{name:'h1'}),(p2:Host{name:'%s'}),p=shortestpath((p1)-[*]-(p2)) RETURN p"%(end)
            path = graph.run(cypher_).data()           #计算最短路径，并返回
            end_timestamp = time.time()
            delay = (end_timestamp-star_timestamp) *1000000   #转化为微秒，微秒（microsecond），时间单位:μs

            f3.write(str(delay) + '\n')
            print("delay", delay)
except:
    print("tree，出错")
