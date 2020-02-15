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
# Author: Bimurti Bidhibrata Pattjoshi <bbidhibr@in.ibm.com>
#

"""
Test the different tools
"""

from avocado import main
from avocado import Test
from avocado.utils import process
from avocado import skipUnless

IS_POWER_VM = 'pSeries' in open('/proc/cpuinfo', 'r').read()


class DisrtoTool(Test):
    '''
    to test different type of tool
    '''

    def setUp(self):
        '''
        get all parameters
        '''
        self.option = self.params.get("test_opt", default='').split(",")
        self.tool = self.params.get("tool", default='')
        self.interface = self.params.get("interface", default='')
        self.location_code = self.params.get("location_code", default='')

    @skipUnless(IS_POWER_VM,
                "supported only on PowerVM platform")
    def lsslot(self, option):
        '''
        run lsslot
        '''
        cmd = "lsslot"
        if option == "pci":
            cmd = "%s -d %s" % (cmd, option)
        else:
            cmd = "%s -c %s" % (cmd, option)
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status != 0:
            self.fail("Failed to display hot plug slots")

    def netstat(self, option):
        '''
        run netstat
        '''
        cmd = "netstat -%s" % option
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status != 0:
            self.fail("Failed to monitoring network connections")

    def lsprop(self, option):
        '''
        run lsprop
        '''
        if option == "r":
            cmd = "lsprop --%s" % option
        else:
            cmd = "lsprop -%s" % option
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status != 0:
            self.fail("lsprop failed")

    def lsvio(self, option):
        '''
        run lsvio aaplicable only for PowerVM
        '''
        cmd = "lsvio -%s" % option
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status != 0:
            self.fail("lsvio failed")

    def lsdevinfo(self, option):
        '''
        run lsdevinfo
        '''
        cmd = "lsdevinfo -%s" % option
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status != 0:
            self.fail("lsdevinfo failed")

    def usys(self, tool, option, interface, location_code):
        '''
        run usysident
        '''
        if option == "-P -s identify -l":
            cmd = "%s %s -l %s " % (tool, option, location_code)
        elif option == "-t -s normal -d":
            cmd = "%s %s -d %s " % (tool, option, interface)
        elif option == "-P -s normal -l":
            cmd = "%s %s -l %s " % (tool, option, location_code)
        else:
            cmd = "%s %s -d %s " % (tool, option, interface)

        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status != 0:
            self.fail("%s option %s failed" % (tool, option))
    
    def usysattn(self, option, interface, location_code):
        self.usys(self.tool, option, interface, location_code)
        return
 
    def usysident(self, option, interface, location_code):
        self.usys(self.tool, option, interface, location_code)
        return

    def ofpathname(self, option):
        '''
        run ofpathname aaplicable only for PowerVM
        '''
        cmd = "ofpathname -%s" % option
        result = process.run(cmd, shell=True, ignore_status=True)
        if result.exit_status != 0:
            self.fail("ofpathname failed")

    def test(self):
        '''
        test different distro tools
        '''
        if self.tool == "lsslot":
            for val in self.option:
                self.lsslot(val)
        elif self.tool == "netstat":
            for val in self.option:
                self.netstat(val)
        elif self.tool == "lsprop":
            for val in self.option:
                self.lsprop(val)
        elif self.tool == "lsvio":
            for val in self.option:
                self.lsvio(val)
        elif self.tool == "lsdevinfo":
            for val in self.option:
                self.lsdevinfo(val)
        elif self.tool == "usysident":
            for val in self.option:
                self.usysident(val, self.interface, self.location_code)
        elif self.tool == "usysattn":
            for val in self.option:
                self.usysattn(val, self.interface, self.location_code)
        elif self.tool == "ofpathname":
            for val in self.option:
                self.ofpathname(val)



if __name__ == "__main__":
    main()
