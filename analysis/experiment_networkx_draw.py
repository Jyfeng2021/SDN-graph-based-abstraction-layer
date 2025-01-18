

import networkx as nx
import time
#from matplotlib import pyplot as plt


def linear(n):
  
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
    return link,s+h,len(h)          #Returns connection relationships and nodes. And the number of nodes.

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
    return link,s+h,len(h)             #Returns connection relationships and nodes. And the number of nodes.

def Tree(n):    
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

    return links,c+a+e+h,len(h)            #Returns connection relationships and nodes. And the number of nodes.

member=512
try:
    with open(r'/home/jyf/Desktop/Experiment/experiment/Networx_linear.txt', 'a') as f2:
        for i in range(2,member,6):
            G2=nx.DiGraph()
            links,nodes,num=linear(i)      #
            G2.add_nodes_from(nodes)
            G2.add_edges_from(links)

            star_timestamp = time.time()
            path=nx.shortest_path(G2,'h1','h'+str(num))   #Calculate the shortest path and return
            end_timestamp = time.time()
            delay = (end_timestamp-star_timestamp) *1000000   #（microsecond），μs

            f2.write(str(delay) + '\n')
            print("linear_delay",delay,G2,path)
except:
    print("linear，error")
time.sleep(1)

try:
    with open(r'/home/jyf/Desktop/Experiment/experiment/Networx_mesh.txt', 'a') as f3:
        for i in range(2,member,6):
            G3=nx.DiGraph()
            links,nodes,num=mesh(i)     
            G3.add_nodes_from(nodes)
            G3.add_edges_from(links)

            star_timestamp = time.time()
            path=nx.shortest_path(G3,'h1','h'+str(num))   #Calculate the shortest path and return
            end_timestamp = time.time()
            delay = (end_timestamp-star_timestamp) *1000000   #（microsecond），μs

            f3.write(str(delay) + '\n')
            print("mesh_delay",delay,G3,path)
except:
    print("mesh，error")
time.sleep(1)

try:
    with open(r'/home/jyf/Desktop/Experiment/experiment/Networx_Tree.txt', 'a') as f1:
        for i in range(2,member,6):
            G1=nx.DiGraph()
            links,nodes,num=Tree(i)      
            G1.add_nodes_from(nodes)
            G1.add_edges_from(links)

            star_timestamp = time.time()
            path=nx.shortest_path(G1,'h1','h'+str(num))   #Calculate the shortest path and return
            end_timestamp = time.time()
            delay = (end_timestamp-star_timestamp) *1000000   #（microsecond），μs

            f1.write(str(delay) + '\n')
            print("Tree_delay",delay,G1,path)
except:
    print("Tree，error")



