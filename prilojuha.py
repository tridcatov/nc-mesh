#!/bin/python

from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange, ServiceInfo

import logging
import netifaces
import socket
import subprocess
from time import sleep

interface = "eth0"
gateway = ""


def set_gateway(name, hop):
    global gateway
    gateway = name
    print("Cleaning routing\n")
    print(cmd("route del default"))

    octets = hop.split(".")
    octets[3] = str(int(octets[3]) + 1)
    address = ".".join(octets)
    print("Setting ip address to %s" % (address))
    print(cmd("ifconfig eth0 " + address))

    print("Gateway has been set to %s\n" % (gateway))
    print(cmd("route add default gw " + hop))


def remove_gateway():
    print("Gateway shutted down, panica!\n")
    print(cmd("route del default"))


def cmd(cmd):
    return subprocess.Popen(cmd, shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                            ).stdout.read().decode()


def get_ip_address():
    return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']


def get_hostname_from_servicename(name, service_type):
    return name.split(service_type)[0]


def on_service_state_change(zeroconf, service_type, name, state_change):
    global gateway
    service_hostname = get_hostname_from_servicename(name, service_type)
    print("Announced event from host %s\n" % (service_hostname))

    if state_change is ServiceStateChange.Added:
        info = zeroconf.get_service_info(service_type, name)
        address = socket.inet_ntoa(info.address)
        isGw = info.properties["gateway".encode()]

        print("Added device %s, gateway %s" % (address, isGw))

        if (address != get_ip_address() and isGw is True):
            set_gateway(service_hostname, address)

    print(gateway)

    if state_change is ServiceStateChange.Removed and \
            service_hostname == gateway:
        remove_gateway()

    print("\n")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    zeroconf = Zeroconf()
    browser = ServiceBrowser(zeroconf, "_nc-mesh._tcp.local.",
                             handlers=[on_service_state_change])

    hostname = socket.gethostname().split(".")[0]
    serviceType = "_nc-mesh._tcp.local."

    cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
    cmd("iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE")
    properties = {"gateway": "true"}
    info = ServiceInfo(serviceType, hostname + "." + serviceType,
                       socket.inet_aton(get_ip_address()), 6666,
                       properties=properties)

    zeroconf.register_service(info)

    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        zeroconf.unregister_service(info)
        cmd("iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE")
        zeroconf.close()
