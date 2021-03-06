===============================
horizon-hpe-storage-ui
===============================

Hewlett Packard Enterprise Storage Dashboard

* Free software: Apache license

Overview
---------

This plug-in extends the OpenStack Horizon Dashboard and provides useful features for OpenStack environments that use HPE 3PAR for backend storage.

This plug-in adds an "HPE Storage" panel to the Admin dashboard, and provides diagnostic and discover tools to help administrators better manage their OpenStack Cinder environment and HPE 3PAR StoreServ backend storage arrays.

Key features:

* Validate OpenStack Cinder configuration file (cinder.conf) entries to ensure they are properly specified.
* Validate required software packages and drivers are installed on Cinder and Nova nodes.
* Provide detailed Horizon views of all HPE Storage Arrays configured for Cinder backend storage.
* Provide a direct link between OpenStack volumes and their associated detail views in the HPE storage management console (HPE 3PAR SSMC).
* Query Nova nodes for volume paths and associated attached Cinder volumes.

Requirements
------------

The following packages are required for this plug-in:

* OpenStack Barbican (https://pypi.python.org/pypi/python-barbicanclient)
* HPE Storage Diagnostic Tool (https://pypi.python.org/pypi/cinderdiags)

Both of these packages will be installed automatically when this plug-in is installed.

This plug-in is only intended for use on systems running OpenStack Horizon.

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

    
After reloading the Horizon dashboard in your browser, log-in as an "Admin" user. If the plug-in was successfully loaded, you should see a new "HPE Storage" panel listed at the bottom of the "Admin" section.

Uninstalling the plug-in
------------------------

Uninstall the python package and remove the config files::

    sudo pip uninstall horizon-hpe-storage-ui
    rm horizon/openstack_dashboard/local/enabled/*_hpe_storage_admin_panel.*

