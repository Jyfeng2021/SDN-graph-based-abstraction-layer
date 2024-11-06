Here's how to run a graph-based abstraction layer.  

1.Start the ryu controller in the console：   
cd /home/jyf/ryu/ryu/app/   
sudo ryu-manager graph-based_abstraction layer  --verbose  

2.Start mininet in the console:
You can use the custom topology from our experiment:
sudo python3 experiment_topo.py  

You can also use mininet's built-in topology creation method:    
Single topology:
sudo mn --controller=remote --topo=single,4 --mac  
Linear topology:
sudo mn --controller=remote --topo=linear,4 --mac  
Tree topology:
sudo mn --controller=remote --topo=tree,2,2 --mac  

3.Run the traffic random generator：  
Non-remote controller can run: 
sudo python3 Traffic_ generated_randomly.py  
Remote controller can run: 
sudo python3 Traffic_ generated_randomly.py --controller=remote ip=192.168.253.131 --topo=linear=4  
To run the traffic-fixed generator, you can run Traffic_generated_nonrandom.py in the same way as the random traffic generator.

Tip: 
Start the controller first, then the topology, and wait until the switch is fully connected to the controller before running the traffic generator.

==============================================================================================================
mininet detailed use of mininet can be found on the official website, where common examples are listed：
In mininet> to the switch flow table:  
dpctl add-flow s1 priority=0,actions=output:controller  

View the flow table: dpctl dump-flows  

View the statistics of a port, including Tx,Rx counters, bytes, and Error counters：
dump-ports  

To view Layer 1 and Layer 2 information about a port:
dpctl show  

==============================================================================================================
When the operation is not normal, the following error message is displayed: “Exception: Please shut down the controller which is running on port 6653” 
The treatment method is:
sudo fuser -k 6653/tcp  
sudo mn -c  
