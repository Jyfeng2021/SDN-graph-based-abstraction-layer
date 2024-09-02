以下是运行基于图的抽象层的方法。  
启动ryu控制器：   
cd /home/jyf/ryu/ryu/app/   
sudo ryu-manager graph-based_abstraction layer  --verbose!  

mininet运行：  
测试用的topo:    
单一拓扑：  
sudo mn --controller=remote --topo=single,4 --mac  
线性拓扑：  
sudo mn --controller=remote --topo=linear,4 --mac  
树形拓扑：  
sudo mn --controller=remote --topo=tree,2,2 --mac  
现有的topo文件：  
sudo python3 experiment_topo.py  


运行流量生成器：  
非远程控制器运行：  
sudo python3 topo_launcher.py  
远程控制器运行：  
sudo python3 topo_launcher.py --controller=remote ip=192.168.253.131 --topo=linear=4  


在 mininet> 中给交换机下放流表：  
举个例子：dpctl add-flow s1 priority=0,actions=output:controller  

查看流表： dpctl dump-flows  

查看端口的统计信息（包括Tx,Rx counters, bytes以及Error counters等）：  
dump-ports  

查看端口的一层和二层信息：  
dpctl show  

当运行不正常有如下的错误提示：  
Exception: Please shut down the controller which is running on port 6653:  
处理方法是：  
sudo fuser -k 6653/tcp  
sudo mn -c  
