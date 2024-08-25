# -*- coding: utf-8 -*-
import psutil
import datetime
import time
import matplotlib.pyplot as plt
# 本模块用于监控CPU信息，监督内存信息，监督网络信息。贾玉峰写于202306
def cpu():
    cpu_percent = psutil.cpu_percent(interval=1)             #总cpu的占用率。
    # 获取逻辑CPU数量和每个逻辑CPU的占用率。有时候cpu会有好多个。
    logical_cpus_count = psutil.cpu_count(logical=True)   #逻辑CPU数量
    logical_cpu_percent = psutil.cpu_percent(interval=1, percpu=True)     #每个逻辑CPU的占用率，列表
    total = 0
    for percentage in logical_cpu_percent:
        total = total + percentage
    per_logicalcpu_percent = total / logical_cpus_count  # 所有逻辑cpu平均占有率

    cpu_info={
        'cpu_percent': cpu_percent,
        'per_logicalcpu_percent': per_logicalcpu_percent,
        'logical_cpu_percent': logical_cpu_percent,
    }
    return cpu_info

# 监控内存信息
def mem():
    mem = psutil.virtual_memory()  # 查看内存信息:(total,available,percent,used,free)
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

# 监控网络流量
def network():
    network = psutil.net_io_counters()  # 查看网络流量的信息；(bytes_sent, bytes_recv, packets_sent, packets_recv, errin, errout, dropin, dropout)
    # print(network)
    network_sent = int(psutil.net_io_counters()[0] / 8 / 1024)  # 每秒接受的kb
    network_recv = int(psutil.net_io_counters()[1] / 8 / 1024)
    network_info = {
        'network_sent': network_sent,
        'network_recv': network_recv
    }
    return network_info                #当前的网络 I/O与前面的网络 I/O之差，除以时间间隔实现网速。

# 间隔一定时间(10秒)，输出当前的CPU状态信息
def all_msg():
    msg = []
    now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')      # 当前时间。append之后是['2019-03-21 15:31:39']
    # now_time = datetime.datetime.strptime(now_time, '%Y-%m-%d %H:%M:%S')  # append之后是[datetime.datetime(2019, 3, 21, 15, 29, 42)]
    msg.append(now_time)                                                 # 获取时间点 (f0)
    cpu_info = cpu()
    msg.append(cpu_info['per_logicalcpu_percent'])                          # 所有逻辑cpu使用率,单位：%                                              #
    mem_info = mem()
    msg.append(mem_info['mem_per'])                                       # 内存使用率(f2),单位：%
    network_info = network()
    msg.append(network_info['network_sent'])                              # 网络流量接收的量（MB）(f6)
    msg.append(network_info['network_recv'])                              # 网络流量发送的量（MB） (f7)
    return msg                     #列表顺序为添加的顺序，分别为：当前时间，cpu使用率，内存使用率，网络流量接收的量，网络流量发送的量（MB）


def write_txt(lis, filename):
    with open(filename, 'a') as f:
        for item in lis:
            f.write("%s " % item)
        f.write("\n")                #换行

def read_txt(filename):
    data = []    # 创建一个空列表用来存储数据
    with open(filename, 'r') as f:               # 打开txt文件并读取每一行
        lines = f.readlines()
    for line in lines:                              # 从每一行中解析出数据并添加到列表中
        numbers = line.strip().split(' ')                        # 移除行尾的空格和换行符，然后使用空格分割数据
        date_time = numbers[0]+" "+numbers[1]
        #data.append([number for number in numbers])        # 将数据转换为整数并添加到列表中
        data.append([date_time] + [int(number) for number in numbers[2:]])
    return data

def draw(draw_list):
    # 提取列表中的x和y值
    x_values = [item for item in range(0,len(draw_list))]
    y1_values = [item[1] for item in draw_list]
    y2_values = [item[2] for item in draw_list]

    # 创建折线图
    plt.plot(x_values, y1_values, label='cpu')
    plt.plot(x_values, y2_values, label='memory')

    # 图例和标题
    plt.legend()                          #添加图例
    plt.title('Computer performance monitoring')                #添加标题
    plt.xlabel('time(s)')                 #坐标轴标签
    plt.ylabel('ratio(%)')                #坐标轴标签
    plt.xlim([0,132])                    # 设置x轴范围
    plt.ylim([0, 101])                    # 设置y轴范围
    plt.grid(True)                         # 显示网格
    plt.show()                            # 显示图形
def main():
    n = 0                                             #统计的次数（初始为1）
    statistics_interval=120                           #统计的时间为120秒（结束为120）
    sleep_interval=1                                  #休眠的间隔为1秒（步长为1）
    draw_list=[]
    while (1):
        msg = all_msg()
        draw_list.append(msg)
        print(msg)                                    # 实时打印每个秒写入txt的数据。
        write_txt(msg, 'cpu_output.txt')
        time.sleep(sleep_interval)                    # 每隔1秒，统计一次当前计算机的使用情况。
        n += 1
        if (n >= statistics_interval):                 #跳出循环
            print("共统计了 %s 次"%n,"分别为：当前时间，cpu使用率，内存使用率，网络流量接收的量，网络流量发送的量（MB）")
            break
    #draw(draw_list)                                    #画出结果


if __name__ == '__main__':
    main()

"""
# 发邮件进行实时报告计算机的状态
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from email.header import Header
def send_email(info):
    sender = '***@qq.com'
    recevier = '***@qq.com'
    subject = 'Warning'
    username = '***@qq.com'
    password = '***'  # 相应的密码
    msg = MIMEText(info, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = sender
    msg['To'] = recevier
    smtp = smtplib.SMTP()
    smtp.connect('smtp.qq.com')
    smtp.login(username, password)
    smtp.sendmail(sender, recevier, msg.as_string())
    smtp.quit()
# 主函数调用，调用其他信息
def main():
    cpu_info = cpu()
    mem_info = mem()
    disk_info = disk()
    network_info = network()
    info = ''' 
                监控信息 
        ========================= 
        cpu使用率： : %s,
        ========================= 
        内存总大小（MB） : %s, 
        内存使用大小（MB） : %s, 
        内存使用率 : %s,
        =========================
        C盘使用率: %s, 
        D盘使用率: %s,
        E盘使用率: %s,
        =========================
        网络流量接收的量（MB） : %s, 
        网络流量发送的量（MB）: %s,
    ''' % (cpu_info,
          mem_info['mem_total'], mem_info['mem_used'], mem_info['mem_per'],
          disk_info['c_per'], disk_info['d_per'], disk_info['e_per'],
          network_info['network_sent'], network_info['network_recv'])
    send_email(info)
main()
"""


"""
# 监控磁盘使用率
def disk():
    c_per = int(psutil.disk_usage('C:')[3])  # 查看c盘的使用信息：总空间，已用，剩余，占用比;
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
print("系统磁盘信息：" + str(io))

for i in io:
    try:
        o = psutil.disk_usage(i.device)
        ioo=psutil.disk_io_counters()
        print(ioo)
    except Exception as e:
        pass
    print("%s盘总容量："%i.device + str(int(o.total / (1024.0 * 1024.0 * 1024.0))) + "G")
    print("已用容量：" + str(int(o.used / (1024.0 * 1024.0 * 1024.0))) + "G")
    print("可用容量：" + str(int(o.free / (1024.0 * 1024.0 * 1024.0))) + "G")
"""