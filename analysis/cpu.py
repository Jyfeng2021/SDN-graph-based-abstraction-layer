# -*- coding: utf-8 -*-
## # This module is used to monitor CPU information, monitor memory information, monitor network information

import psutil
import datetime
import time
import matplotlib.pyplot as plt


# Monitoring cpu Information
def cpu():
    cpu_percent = psutil.cpu_percent(interval=1)             # Total cpu usage.
    # # Get the number of logical cpus and the usage of each logical CPU.
    logical_cpus_count = psutil.cpu_count(logical=True)                                            # number
    logical_cpu_percent = psutil.cpu_percent(interval=1, percpu=True)    
    total = 0
    for percentage in logical_cpu_percent:
        total = total + percentage
    per_logicalcpu_percent = total / logical_cpus_count   

    cpu_info={
        'cpu_percent': cpu_percent,
        'per_logicalcpu_percent': per_logicalcpu_percent,
        'logical_cpu_percent': logical_cpu_percent,
    }
    return cpu_info

# Monitor memory information
def mem():
    mem = psutil.virtual_memory()   
    # print(mem)
    mem_total = int(mem[0] / 1024 / 1024)
    mem_used = int(mem[3] / 1024 / 1024)
    mem_per = int(mem[2])
    mem_info = {
        'mem_total': mem_total,
        'mem_used': mem_used,
        'mem_per': mem_per,
    }
    return mem_info

# Monitor network traffic
def network():
    network = psutil.net_io_counters()  #(bytes_sent, bytes_recv, packets_sent, packets_recv, errin, errout, dropin, dropout)
    # print(network)
    network_sent = int(psutil.net_io_counters()[0] / 8 / 1024)  # Received data in kb per second
    network_recv = int(psutil.net_io_counters()[1] / 8 / 1024)
    network_info = {
        'network_sent': network_sent,
        'network_recv': network_recv
    }
    return network_info                

# The CPU status is displayed at an interval of 10 seconds
def all_msg():
    msg = []
    now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')      #  append ['2019-03-21 15:31:39']
    # now_time = datetime.datetime.strptime(now_time, '%Y-%m-%d %H:%M:%S')  # append [datetime.datetime(2019, 3, 21, 15, 29, 42)]
    msg.append(now_time)                                                 
    cpu_info = cpu()
    msg.append(cpu_info['per_logicalcpu_percent'])                          
    mem_info = mem()
    msg.append(mem_info['mem_per'])                                        
    network_info = network()
    msg.append(network_info['network_sent'])                              # The amount of network traffic received (MB)
    msg.append(network_info['network_recv'])                              # The amount of network traffic sent (MB)
    return msg                   # The order of the list is the order of addition, respectively: current time, cpu usage, memory usage, amount of network traffic received, amount of network traffic sent (MB)


def write_txt(lis, filename):
    with open(filename, 'a') as f:
        for item in lis:
            f.write("%s " % item)
        f.write("\n")                

def read_txt(filename):
    data = []    
    with open(filename, 'r') as f:               
        lines = f.readlines()
    for line in lines:                              
        numbers = line.strip().split(' ')                       
        date_time = numbers[0]+" "+numbers[1]
        # data.append([number for number in numbers])        
        data.append([date_time] + [int(number) for number in numbers[2:]])
    return data

def draw(draw_list):
    # Extract x and y values from the list
    x_values = [item for item in range(0,len(draw_list))]
    y1_values = [item[1] for item in draw_list]
    y2_values = [item[2] for item in draw_list]

    # Create a line chart
    plt.plot(x_values, y1_values, label='cpu')
    plt.plot(x_values, y2_values, label='memory')

    # # Legend and title
    plt.legend()                           
    plt.title('Computer performance monitoring')           
    plt.xlabel('time(s)')                  
    plt.ylabel('ratio(%)')               
    plt.xlim([0,132])                  
    plt.ylim([0, 101])                     
    plt.grid(True)                          
    plt.show()                            
def main():
    n = 0                                             # Number of statistics (initially 1)
    statistics_interval=120                           # The statistical period is 120 seconds (end at 120)
    sleep_interval=1                                  # The sleep interval is 1 second (step length is 1)
    draw_list=[]
    while (1):
        msg = all_msg()
        draw_list.append(msg)
        print(msg)                                    # Print the data written to txt in real-time.
        write_txt(msg, 'cpu_output.txt')
        time.sleep(sleep_interval)                    # Collect the current computer usage every 1 second.
        n += 1
        if (n >= statistics_interval):                 # Exit the loop
            print("A total of %s statistics were collected" % n, "The values are current time, cpu usage, memory usage, received network traffic, and sent network traffic (MB)")
            break
    # draw(draw_list)                                    # Draw the results


if __name__ == '__main__':
    main()

"""
# # Send emails to report the status of your computer in real time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from email.header import Header
def send_email(info):
    sender = '***@qq.com'
    recevier = '***@qq.com'
    subject = 'Warning'
    username = '***@qq.com'
    password = '***'  # Corresponding password
    msg = MIMEText(info, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = sender
    msg['To'] = recevier
    smtp = smtplib.SMTP()
    smtp.connect('smtp.qq.com')
    smtp.login(username, password)
    smtp.sendmail(sender, recevier, msg.as_string())
    smtp.quit()


# The main function 
def main():
    cpu_info = cpu()
    mem_info = mem()
    disk_info = disk()
    network_info = network()
    info = ''' 
                Monitoring Information 
        ========================= 
        cpu usage: %s,
        ========================= 
        Total memory size (MB): %s, 
        Used memory size (MB): %s, 
        Memory usage rate: %s,
        =========================
        C disk usage rate: %s, 
        D disk usage rate: %s,
        E disk usage rate: %s,
        =========================
        Network traffic received (MB): %s, 
        Network traffic sent (MB): %s,
    ''' % (cpu_info,
          mem_info['mem_total'], mem_info['mem_used'], mem_info['mem_per'],
          disk_info['c_per'], disk_info['d_per'], disk_info['e_per'],
          network_info['network_sent'], network_info['network_recv'])
    send_email(info)
main()
"""


"""
# Monitor disk usage
def disk():
    c_per = int(psutil.disk_usage('C:')[3])  # Check the usage information of C disk: total space, used, remaining, usage percentage;
    d_per = int(psutil.disk_usage('d:')[3])
    e_per = int(psutil.disk_usage('e:')[3])
    # print(c_per, d_per, e_per)
    disk_info = {
        'c_per': c_per,
        'd_per': d_per,
        'e_per': e_per,
    }
    return disk_info

io = psutil.disk_partitions()
print("System disk information: " + str(io))

for i in io:
    try:
        o = psutil.disk_usage(i.device)
        ioo = psutil.disk_io_counters()
        print(ioo)
    except Exception as e:
        pass
    print("%s disk total capacity: " % i.device + str(int(o.total / (1024.0 * 1024.0 * 1024.0))) + "G")
    print("Used capacity: " + str(int(o.used / (1024.0 * 1024.0 * 1024.0))) + "G")
    print("Available capacity: " + str(int(o.free / (1024.0 * 1024.0 * 1024.0))) + "G")
"""
