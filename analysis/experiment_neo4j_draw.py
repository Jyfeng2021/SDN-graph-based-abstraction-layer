

# import networkx as nx
# from matplotlib import pyplot as plt
import time
from py2neo import Node, Relationship, Graph, NodeMatcher, RelationshipMatcher
graph = Graph("http://localhost:7474", auth=("neo4j", "jyfjyfjyf"),name="neo4j")


def linear(n):
    # 初始化线性拓扑  Initialize the linear topology
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
    return link,s+h,len(h)         #Returns connection relationships and nodes. And the number of nodes.

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
    return link,s+h,len(h)           #Returns connection relationships and nodes. And the number of nodes.

def Tree(n):   #n must be even
    #Marking the number of switch for per level
    L1 = n;
    L2 = L1*2
    L3 = L2

    #Starting create the switch
    c = []    #core switch
    a = []    #aggregate switch
    e = []    #edge switch
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

    return links,c+a+e+h,len(h)          #Returns connection relationships and nodes. And the number of nodes.

def batch_create(graph, nodes_list, relations_list):
    """
    :param graph: Graph()
    :param nodes_list: Node() 
    :param relations_list: Relationship 
    :return:
    """

    subgraph = Subgraph(nodes_list, relations_list)
    tx_ = graph.begin()
    tx_.create(subgraph)
    graph.commit(tx_)




number=512       
try:
    with open(r'/home/jyf/Desktop/Experiment/experiment/neo4j_linear.txt', 'a') as f1:
        for i in range(2,number,6):
            graph.delete_all()  
            links,nodes,num=linear(i)     
            end='h'+str(num)

            node_matcher = NodeMatcher(graph)
            for node in nodes:
                node_h = Node('Host', name=node)
                graph.create(node_h)

            for link in links:
                node1 = node_matcher.match('Host', name=link[0])  
                node2 = node_matcher.match('Host', name=link[1]) 
                node_to_node1 = Relationship(node1.first(),'link',node2.first())
                graph.create(node_to_node1)
                node_to_node2 = Relationship(node2.first(),'link',node1.first())
                graph.create(node_to_node2)

            star_timestamp = time.time()
            cypher_ = "MATCH (p1:Host{name:'h1'}),(p2:Host{name:'%s'}),p=shortestpath((p1)-[*]-(p2)) RETURN p"%(end)
            path = graph.run(cypher_).data()          
            end_timestamp = time.time()
            delay = (end_timestamp-star_timestamp) *1000000  

            f1.write(str(delay) + '\n')
            print("delay",delay)
except:
    print("linear，error")
time.sleep(1)

try:
    with open(r'/home/jyf/Desktop/Experiment/experiment/neo4j_mesh.txt', 'a') as f2:
        for i in range(2,number,6):
            graph.delete_all()   
            links,nodes,num=mesh(i)      
            end='h'+str(num)

            node_matcher = NodeMatcher(graph)  # Query matching
            for node in nodes:
                node_h = Node('Host', name=node)
                graph.create(node_h)

            for link in links:
                node1 = node_matcher.match('Host', name=link[0])  
                node2 = node_matcher.match('Host', name=link[1])  
                node_to_node1 = Relationship(node1.first(),'link',node2.first())
                graph.create(node_to_node1)
                node_to_node2 = Relationship(node2.first(),'link',node1.first())
                graph.create(node_to_node2)

            star_timestamp = time.time()
            cypher_ = "MATCH (p1:Host{name:'h1'}),(p2:Host{name:'%s'}),p=shortestpath((p1)-[*]-(p2)) RETURN p"%(end)
            path = graph.run(cypher_).data()                      ## Calculate the shortest path and return
            end_timestamp = time.time()
            delay = (end_timestamp-star_timestamp) *1000000    

            f2.write(str(delay) + '\n')
            print("delay",delay)
except:
    print("mesh，error")
time.sleep(1)

try:
    with open(r'/home/jyf/Desktop/Experiment/experiment/neo4j_tree.txt', 'a') as f3:
        for i in range(2,number,6):
            graph.delete_all()  
            links,nodes,num=Tree(i)                                       #Generate network topology
            end='h'+str(num)

            node_matcher = NodeMatcher(graph) 
            for node in nodes:
                node_h = Node('Host', name=node)
                graph.create(node_h)

            for link in links:
                node1 = node_matcher.match('Host', name=link[0])   
                node2 = node_matcher.match('Host', name=link[1])   
                node_to_node1 = Relationship(node1.first(),'link',node2.first())
                graph.create(node_to_node1)
                node_to_node2 = Relationship(node2.first(),'link',node1.first())
                graph.create(node_to_node2)

            star_timestamp = time.time()
            cypher_ = "MATCH (p1:Host{name:'h1'}),(p2:Host{name:'%s'}),p=shortestpath((p1)-[*]-(p2)) RETURN p"%(end)
            path = graph.run(cypher_).data()                                                                                                         ## Calculate the shortest path and return
            end_timestamp = time.time()
            delay = (end_timestamp-star_timestamp) *1000000  
            f3.write(str(delay) + '\n')
            print("delay", delay)
except:
    print("tree，error")
