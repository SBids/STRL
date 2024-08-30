
from mn_wifi.topo import Topo
from mininet.log import setLogLevel, info
from mininet.node import CPULimitedHost
from minindn.apps.app_manager import AppManager
from minindn.apps.nfd import Nfd
from minindn.helpers.nfdc import Nfdc
from minindn.wifi.minindnwifi import MinindnWifi
from minindn.util import MiniNDNWifiCLI, getPopen
from time import sleep
import subprocess
import shutil
import os
import sys
import itertools

_F_NAME = "transfer_"
parent_folder = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
rl_path = os.path.join(parent_folder, 'rl/basefor1.py')

all_nodes = {
    "sta1": {"position": (10,10,0)},
    "sta2": {"position": (30,10,0)},
    "sta3": {"position": (30,30,0)},
    "sta4": {"position": (10,30,0)},
    "sta5": {"position": (0,0,0)},
    "sta6": {"position": (40,40,0)},
    "sta7": {"position": (0,20,0)},
    "sta8": {"position": (0,40,0)},
    "sta9": {"position": (20,40,0)},
    "sta10": {"position": (40,20,0)},
    "sta11": {"position": (40,0,0)},
    "sta12": {"position": (20,0,0)},
    "sta13": {"position": (20,10,0)}
}
accessPoint = {"ap1": {"position": (20,20,0), "range": 100, "mode":'g'}}

def get_first_n_items(dictionary, n):
    return dict(itertools.islice(dictionary.items(), n))

def sendFile(node, prefix, file):  
    fname = file.split("/")[-1].split(".")[0]
    publised_under = "{}/{}".format(prefix, fname)
    info ("Publishing file: {}, under name: {} \n".format(fname, publised_under))
    cmd = 'ndnputchunks -s 100 {} < {} > putchunks.log 2>&1 &'.format(publised_under, file)
    print(f"Send File: {cmd}")
    node.cmd(cmd)
    sleep(10)

def receiveFile(node, prefix, filename, full_filename):
    file_prefix = filename.split('.')[0]
    info ("Fetching file: {} \n".format(full_filename))
    cmd = 'ndncatchunks -v -p cubic --log-cwnd log-cwnd --log-rtt log-rtt {}/{} > {} 2> catchunks-{}-{}.log &'.format(prefix, file_prefix, full_filename, full_filename, filename)
    print(f"Received File: {cmd}")
    node.cmd(cmd)

if __name__ == '__main__':
    setLogLevel('info')
    subprocess.run(["mn", "-c"]) # ensures that any existing Mininet network is terminated before the script proceeds with setting up a new network topology.
    sleep (1)
    shutil.rmtree('/tmp/minindn/', ignore_errors=True) # utility functions in python to remove a directory tree
    os.makedirs("/tmp/minindn/", exist_ok=True)
    topo = Topo() # creates an instance of the Topo class, 
    #which is provided by the Mininet-WiFi library. The Topo class is used to define the network topology in a Mininet-WiFi simulation.
    if len(sys.argv) < 2:
        print ("Missing argument for the number of consumers")
        exit() 
    number_of_consumers = int(sys.argv[1])
    nodes = get_first_n_items(all_nodes, number_of_consumers+1) # get n+1 nodes from all nodes
    # this topo setup only works for this experiment, 1 ap and x number of stations
    _s = []
    _ap = []
    for station in nodes:
        _s.append(topo.addStation(name=station, position=nodes[station]['position']))

    for ap in accessPoint:
        _ap.append(topo.addAccessPoint(ap, **accessPoint[ap]))

    optsforlink1  = {'bw':100, 'delay':'5ms', 'loss':0, 'mode': 'g'} # bandwidth of link, delay of the link, packet loss percentage

    for s in _s:
        topo.addLink(s, _ap[0], **optsforlink1) #adds a wireless link between the current station s and the first access point (_ap[0]).
        # topo.addLink(s, _ap[0], delay='5ms')
        #creates a network topology with wireless stations and an access point. 
        # It then adds wireless links between each station and the first access point, with link characteristics defined by the optsforlink1 dictionary

    # creating instance of MinindnWifi with wireless network topology defined by the topo object.
    ndnwifi = MinindnWifi(topo=topo)
    args = ndnwifi.args
    args.ifb = True # enabling itermediate functional block which is linux kernel module used for traffic shaping and quality of service puropose
    args.host = CPULimitedHost # host used in network emulation is a host class that limits the CPU usaage of the emulated hosts, 
    #useful for simulating scenarios with resource-constrained devices.
    
    testFile = os.path.join(parent_folder, "files/{}.dat".format(_F_NAME))
    i = 1024
    for node in ndnwifi.net.stations:
        i = i*2
        cmd = "echo {} > {}".format(i, "seed") #creates a shell command that writes the value of i to a file named "seed". The file "seed" will have the value of i (e.g., 2048, 4096, 8192, etc.).
        node.cmd(cmd) #execute the command on the station. This allows running Linux shell commands on the emulated hosts.
        node.cmd("sysctl net.ipv4.ipfrag_time = 10") #sets the value of the net.ipv4.ipfrag_time parameter to 10 on the station.
        node.cmd("sysctl net.ipv4.ipfrag_high_thresh = 26214400") #sets the value of the net.ipv4.ipfrag_high_thresh parameter to 26214400 on the station. This parameter is related to the high threshold for IPv4 packet fragmentation
    sleep(1)
    producers_prefix = {"sta1" : "/producer/sta1"}
    ndnwifi.start()
    info("Starting NFD ")
    print()
    nfds = AppManager(ndnwifi, ndnwifi.net.stations, Nfd, logLevel='DEBUG')
    sleep(2)

    mcast = "224.0.23.170"
    producers = [ndnwifi.net[x] for x in producers_prefix.keys()]
    consumers = [y for y in ndnwifi.net.stations if y.name not in [x.name for x in producers]]
    print ("producers: ", producers)
    print ("consumers: ", consumers)
    print("RL path: ", rl_path)
    # nlsrc advertises prefix/withdraw prefixes and route status
    
    for c in consumers:
        Nfdc.registerRoute (c, "/producer", mcast)
        sleep(2)
        print(c.name)
        c.cmd("/usr/bin/python {} > reinforcement-{}.log 2>&1 &".format(rl_path, c.name))
        print(rl_path, c.name)
        sleep(5) #changed to 5 from 10
        print("The consumer slept for 5 ms") 
    for p in producers:
        # sleep (1)
        print ("starting producer {}".format(p))
        p.cmd("/usr/bin/python {} > reinforcement-{}.log 2>&1 &".format(rl_path, p.name))

        sleep(5)#changed to 5 from 10
        print("The producer slept for 10 ms before sending the file !!!")
        # sendFile(p, producers_prefix[p.name], testFile)


    # for c in consumers:
    #     # sleep(random.uniform(0, 1) % 0.02) # sleep at max 20ms
    #     for p in producers:
    #         receiveFile(c, producers_prefix[p.name], p.name+".txt")

    base_path = "/home/bidhya/workspace/STRL/files/"
    file_list = [
        "transfer3.dat",
        # "transfer_2.dat",
        # "transfer_.dat"
        ]
    for file in file_list:
        producer_0 = producers[0]
        producer_name = producer_0.name

        sendFile(p, producers_prefix[producer_name], base_path + file)

        for c in consumers:
            receiveFile(c, producers_prefix[producer_name], file, producer_name + ".txt")

    

    MiniNDNWifiCLI(ndnwifi.net)
    
 
    # sleep(60)
    ndnwifi.stop()


    
