# -*- coding: utf-8 -*-
"""
deploy_vsphere_template_with_nuage is a script which allows you to deploy (or clone) a VM template (or VM) and connect it to a Nuage VSP subnet.

This can be done through either specifying all parameters through CLI, or by selecting them from lists.

Check the examples for several combinations of arguments

--- Usage ---
Run 'python deploy_vsphere_template_with_nuage.py -h' for an overview

--- Documentation ---
http://github.com/nuagenetworks/vspk-examples/blob/master/docs/deploy_vsphere_template_with_nuage.md

--- Author ---
Philippe Dellaert <philippe.dellaert@nuagenetworks.net>

--- Examples ---
---- Deploy a template in a given Resource Pool and Folder, with given Nuage VM metadata and a fixed IP ----
python deploy_vsphere_template_with_nuage.py -n Test-02 --nuage-enterprise csp --nuage-host 10.167.43.64 --nuage-user csproot -S -t TestVM-Minimal-Template --vcenter-host 10.167.43.24 --vcenter-user root -r Pool -f Folder --nuage-vm-enterprise VMware-Integration --nuage-vm-domain Main --nuage-vm-zone "Zone 1" --nuage-vm-subnet "Subnet 0" --nuage-vm-ip 10.0.0.123 --nuage-vm-user vmwadmin

---- Deploy a template, for the Nuage VM metadata show menus to select values from ----
python deploy_vsphere_template_with_nuage.py -n Test-02 --nuage-enterprise csp --nuage-host 10.167.43.64 --nuage-user csproot -S -t TestVM-Minimal-Template --vcenter-host 10.167.43.24 --vcenter-user root
"""