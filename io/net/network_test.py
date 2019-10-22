#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: 2016 IBM
# Author: Prudhvi Miryala <mprudhvi@linux.vnet.ibm.com>
# Author: Narasimhan V <sim@linux.vnet.ibm.com>
#

"""
check the statistics of interface, test big ping
test lro and gro and interface
"""

import time
import hashlib
import paramiko
import netifaces
from avocado import main
from avocado import Test
from avocado.utils.software_manager import SoftwareManager
from avocado.utils import process
from avocado.utils import distro
from avocado.utils import genio
from avocado.utils import configure_network


class NetworkTest(Test):
    '''
    To test different types of pings
    '''

    def setUp(self):
        '''
        To check and install dependencies for the test
        '''
        smm = SoftwareManager()
        pkgs = ["ethtool", "net-tools"]
        detected_distro = distro.detect()
        if detected_distro.name == "Ubuntu":
            pkgs.extend(["openssh-client", "iputils-ping"])
        elif detected_distro.name == "SuSE":
            pkgs.extend(["openssh", "iputils"])
        else:
            pkgs.extend(["openssh-clients", "iputils"])
        for pkg in pkgs:
            if not smm.check_installed(pkg) and not smm.install(pkg):
                self.cancel("%s package is need to test" % pkg)
        interfaces = netifaces.interfaces()
        interface = self.params.get("interface")
        if interface not in interfaces:
            self.cancel("%s interface is not available" % interface)
        self.iface = interface
        self.ipaddr = self.params.get("host_ip", default="")
        self.netmask = self.params.get("netmask", default="")
        configure_network.set_ip(self.ipaddr, self.netmask, self.iface)
        self.peer = self.params.get("peer_ip")
        if not self.peer:
            self.cancel("No peer provided")
        self.switch_name = self.params.get("switch_name", '*', default="")
        self.userid = self.params.get("userid", '*', default="")
        self.password = self.params.get("password", '*', default="")
        self.port_id = self.params.get("port_id", default="")
        if not self.port_id:
            self.cancel("user should specify port id")
        if not self.ping_check("-c 2"):
            self.cancel("No connection to peer")
        self.mtu = self.params.get("mtu", default=1500)
        self.switch_login(self.switch_name, self.userid, self.password)

    def switch_login(self, ip, username, password):
        '''
        Login method for remote fc switch
        '''
        self.tnc = paramiko.SSHClient()
        self.tnc.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.tnc.connect(ip, username=username, password=password,
                         look_for_keys=False, allow_agent=False)
        print("SSH connection established to " + ip)
        self.remote_conn = self.tnc.invoke_shell()
        print("Interactive SSH session established")
        assert self.remote_conn
        self.remote_conn.send("iscli" + '\n')

    def _send_only_result(self, command, response):
        output = response.decode("utf-8").splitlines()
        if command in output[0]:
            output.pop(0)
        output.pop()
        output = [element.lstrip() + '\n' for element in output]
        response = ''.join(output)
        response = response.strip()
        self.log.info(''.join(response))
        return ''.join(response)

    def run_switch_command(self, command, timeout=300):
        '''
        Run command method for running commands on fc switch
        '''
        self.prompt = "#"
        self.log.info("Running the %s command on fc/nic switch", command)
        if not hasattr(self, 'tnc'):
            self.fail("telnet connection to the fc/nic switch not yet done")
        self.remote_conn.send(command + '\n')
        response = self.remote_conn.recv(1000)
        return self._send_only_result(command, response)

    def test_switch_port(self):
        '''
        switch port enable and disable test
        '''
        self.log.info("Enabling the privilege mode")
        self.run_switch_command("enable")
        self.log.info("Entering configuration mode")
        self.run_switch_command("conf t")
        cmd = "interface port %s" % self.port_id
        self.run_switch_command(cmd)
        self.run_switch_command("shutdown")
        time.sleep(5)
        if self.ping_check("-c 5"):
            self.fail("pinging after disable port")
        self.run_switch_command("no shutdown")
        time.sleep(5)
        if not self.ping_check("-c 5"):
            self.fail("ping test failed")
        self.run_switch_command("end")

    def test_mtu_set(self):
        '''
        set mtu size
        '''
        if not self.set_mtu_peer(self.mtu):
            self.fail("Failed to set mtu in peer")
        time.sleep(10)
        if not self.set_mtu_host(self.mtu):
            self.fail("Failed to set mtu in host")
        time.sleep(10)

    def test_gro(self):
        '''
        Test GRO
        '''
        ro_type = "gro"
        ro_type_full = "generic-receive-offload"
        if not self.receive_offload_state(ro_type_full):
            self.fail("Could not get state of %s" % ro_type)
        if self.receive_offload_state(ro_type_full) == 'fixed':
            self.fail("Can not change the state of %s" % ro_type)
        self.receive_offload_toggle_test(ro_type, ro_type_full)

    def test_lro(self):
        '''
        Test LRO
        '''
        ro_type = "lro"
        ro_type_full = "large-receive-offload"
        if not self.receive_offload_state(ro_type_full):
            self.fail("Could not get state of %s" % ro_type)
        if self.receive_offload_state(ro_type_full) == 'fixed':
            self.fail("Can not change the state of %s" % ro_type)
        self.receive_offload_toggle_test(ro_type, ro_type_full)

    def test_ping(self):
        '''
        ping to peer machine
        '''
        if not self.ping_check("-c 5"):
            self.fail("ping test failed")

    def test_floodping(self):
        '''
        Flood ping to peer machine
        '''
        if not self.ping_check("-c 1000 -f"):
            self.fail("flood ping test failed")

    def test_ssh(self):
        '''
        Test ssh
        '''
        cmd = "ssh %s \"echo hi\"" % self.peer
        if process.system(cmd, shell=True, ignore_status=True) != 0:
            self.fail("unable to ssh into peer machine")

    def test_scp(self):
        '''
        Test scp
        '''
        process.run("dd if=/dev/zero of=/tmp/tempfile bs=1024000000 count=1",
                    shell=True)
        md_val1 = hashlib.md5(open('/tmp/tempfile', 'rb').read()).hexdigest()

        cmd = "timeout 600 scp /tmp/tempfile %s:/tmp" % self.peer
        ret = process.system(cmd, shell=True, verbose=True, ignore_status=True)
        if ret != 0:
            self.fail("unable to copy into peer machine")

        cmd = "timeout 600 scp %s:/tmp/tempfile /tmp" % self.peer
        ret = process.system(cmd, shell=True, verbose=True, ignore_status=True)
        if ret != 0:
            self.fail("unable to copy from peer machine")

        md_val2 = hashlib.md5(open('/tmp/tempfile', 'rb').read()).hexdigest()
        if md_val1 != md_val2:
            self.fail("Test Failed")

    def test_jumbo_frame(self):
        '''
        Test jumbo frames
        '''
        if not self.ping_check("-i 0.1 -c 30 -s %d" % (int(self.mtu) - 28)):
            self.fail("jumbo frame test failed")

    def test_statistics(self):
        '''
        Test Statistics
        '''
        rx_file = "/sys/class/net/%s/statistics/rx_packets" % self.iface
        tx_file = "/sys/class/net/%s/statistics/tx_packets" % self.iface
        rx_before = genio.read_file(rx_file)
        tx_before = genio.read_file(tx_file)
        self.ping_check("-c 5")
        rx_after = genio.read_file(rx_file)
        tx_after = genio.read_file(tx_file)
        if (rx_after <= rx_before) or (tx_after <= tx_before):
            self.log.debug("Before\nrx: %s tx: %s" % (rx_before, tx_before))
            self.log.debug("After\nrx: %s tx: %s" % (rx_after, tx_after))
            self.fail("Statistics not incremented properly")

    def test_mtu_set_back(self):
        '''
        Test set mtu back to 1500
        '''
        if not self.set_mtu_host('1500'):
            self.fail("Failed to set mtu in host")
        if not self.set_mtu_peer('1500'):
            self.fail("Failed to set mtu in peer")

    def ping_check(self, options):
        '''
        Checks if the ping to peer works. Returns True if it works.
        Returns False otherwise.
        '''
        cmd = "ping -I %s %s %s" % (self.iface, options, self.peer)
        if process.system(cmd, shell=True, verbose=True,
                          ignore_status=True) != 0:
            return False
        return True

    def set_mtu_peer(self, mtu):
        '''
        set mtu size in peer
        '''
        cmd = "ssh %s \"ip addr show\"" % self.peer
        peer_interface = ""
        try:
            for line in process.system_output(cmd,
                                              shell=True).decode("utf-8") \
                                                         .splitlines():
                if self.peer in line:
                    peer_interface = line.split()[-1]
        except process.CmdError:
            self.log.debug("failed to get info of peer interface")
            return False
        if not peer_interface:
            self.log.debug("failed to get info of peer interface")
            return False
        cmd = "ssh %s \"ip link set %s mtu %s\"" % (self.peer,
                                                    peer_interface,
                                                    mtu)
        try:
            process.system(cmd, shell=True)
        except process.CmdError:
            self.log.debug("setting mtu value %s in peer failed", mtu)
            return False
        else:
            return True

    def set_mtu_host(self, mtu):
        '''
        set mtu size in host
        '''
        con_cmd = "ip link set %s mtu %s" % (self.iface, mtu)
        try:
            process.system(con_cmd, shell=True)
        except process.CmdError:
            self.log.debug("setting mtu value %s in host failed", mtu)
            return False
        else:
            return True

    def receive_offload_toggle_test(self, ro_type, ro_type_full):
        '''
        Check to toggle the LRO and GRO
        '''
        for state in ["off", "on"]:
            if not self.receive_offload_state_change(ro_type,
                                                     ro_type_full, state):
                self.fail("%s %s failed" % (ro_type, state))
            if not self.ping_check("-c 5"):
                self.fail("ping failed in %s %s" % (ro_type, state))

    def receive_offload_state_change(self, ro_type, ro_type_full, state):
        '''
        Change the state of LRO / GRO to specified state
        '''
        cmd = "ethtool -K %s %s %s" % (self.iface, ro_type, state)
        if process.system(cmd, shell=True, ignore_status=True) != 0:
            return False
        if self.receive_offload_state(ro_type_full) != state:
            return False
        return True

    def receive_offload_state(self, ro_type_full):
        '''
        Return the state of LRO / GRO.
        If the state can not be changed, we return 'fixed'.
        If any other error, we return ''.
        '''
        cmd = "ethtool -k %s" % self.iface
        output = process.system_output(cmd, shell=True,
                                       ignore_status=True).decode("utf-8")
        for line in output.splitlines():
            if ro_type_full in line:
                if 'fixed' in line.split()[-1]:
                    return 'fixed'
                return line.split()[-1]
        return ''

    def test_promisc(self):
        '''
        promisc mode testing
        '''
        cmd = "ip link set %s promisc on" % self.iface
        if process.system(cmd, shell=True, ignore_status=True) != 0:
            self.fail("failed to enable promisc mode")
        self.test_ping()
        cmd = "ip link set %s promisc off" % self.iface
        if process.system(cmd, shell=True, ignore_status=True) != 0:
            self.fail("failed to disable promisc mode")
        self.test_ping()

    def tearDown(self):
        '''
        Remove the files created
        '''
        configure_network.unset_ip(self.iface)
        if 'scp' in str(self.name.name):
            process.run("rm -rf /tmp/tempfile")
            cmd = "timeout 600 ssh %s \" rm -rf /tmp/tempfile\"" % self.peer
            process.system(cmd, shell=True, verbose=True, ignore_status=True)


if __name__ == "__main__":
    main()