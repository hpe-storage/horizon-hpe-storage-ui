===============================
horizon-hpe-storage-ui
===============================

Hewlett Packard Enterprise Storage Dashboard

* Free software: Apache license

Overview
---------

This plug-in extends the OpenStack Horizon Dashboard and provides useful features for
OpenStack environments that use HPE 3PAR for backend storage.

This plug-in adds an "HPE Storage" panel to the Admin dashboard. When this panel is selected,
the associated window will have tabs to manage/view HPE Storage related data. The tabs
are as follows:

"3PAR SSMC Links"
Feature on this panel will allow an admin user to associate an instance of HPE 3PAR SSMC
(HPE storage management software for the 3PAR) with an OpenStack storage backend (as
defined by /etc/cinder/cinder.conf). Once this association is in place, links will be
provided in the Horizon volumes table that the user can click on to directly jump to the
volume data page in the associated SSMC panel. The data shown in the SSMC panel provides
much more detail than what is shown in Horizon.

"Cinder Diagnostics & Discovery"
Here the user enters configuration params for accessing cinder.conf files - what system(s)
they are located on and access credentials. Once completed, a diagnostic test can be
run to validate the users config.conf file(s). Checks are made to ensure the backend storage
systems are accessible, credentials are correct, and specified CPG's exist. During the
execution of the tests, backend storage systems are discovered and queried.

"Backend Storage Systems"
As a result of the cinder.conf diagnostic tests, a list of backend storage systems are
discovered. The results are shown in this panel. Along with general information about the
system (name, serial number, software versions, etc), the panel also shows license
information and cinder host capabilities (capacity, QOS support, max number of volumes, etc).

Requirements
------------

The OpenStack Barbican service is required for this plug-in.
(see https://wiki.openstack.org/wiki/Barbican)

The HPE Storage Diagnostic Tool must be installed to enable the "Cinder Diagnostics" features of this plug-in.
(see https://pypi.python.org/pypi/cinderdiags). This should be done automatically during
the install of the "horizon-hpe-storage-ui" package.

This plug-in is only intended for use on systems running Horizon.

Installation instructions
-------------------------

In a Devstack environment, add the following to your Devstack local.conf file::

    enable_plugin barbican https://github.com/openstack/barbican.git
    enable_plugin horizon-hpe-storage-ui https://github.com/hpe-storage/horizon-hpe-storage-ui.git


Or, to add to existing OpenStack deployment::

    cd horizon
    cd ..
    # create new package directory at same root path as Horizon
    git clone https://github.com/hpe-storage/horizon-hpe-storage-ui.git
    # install package
    cd horizon-hpe-storage-ui
    sudo pip install --upgrade .
    # copy configuration file so that Horizon loads the plug-in
    cp -a horizon_hpe_storage/enabled/* ../horizon/openstack_dashboard/local/enabled

    # re-start apache server running Horizon
    cd ../horizon
    sudo service apache2 restart

    
After reloading the Horizon dashboard in your browser, log-in as an "Admin" user. If the plug-in
was successfully loaded, you should see a new "HPE Storage" panel listed at the bottom of the "Admin"
section.

Uninstalling the plug-in
------------------------

Uninstall the python package and remove the config files::

    sudo pip uninstall horizon-hpe-storage-ui
    rm horizon/openstack_dashboard/local/enabled/*_hpe_storage_admin_panel.*

