===============================
horizon-hpe-storage-ui
===============================

Hewlett Packard Enterprise Storage Dashboard

* Free software: Apache license

Overview
---------

This plug-in extends the OpenStack Horizon Dashboard.

It adds an "HPE Storage" panel to the Admin dashboard. When this panel is selected,
the associated window will have tabs to manage/view HPE Storage related data. One of
these tabs will be labeled "3PAR SSMC Links", which will allow an admin user
to associate an HPE 3PAR SSMC instance with an OpenStack storage backend (as defined
by /etc/cinder/cinder.conf).

Requirements
------------

The OpenStack Barbican service is required for this plug-in.
(see https://wiki.openstack.org/wiki/Barbican)

The HPE Storage Diagnostic Tool must be installed to enable the "Cinder Diagnostics" features of this plug-in.
(see https://pypi.python.org/pypi/cinderdiags)

This plug-in is only intended for use on systems running Horizon.

Installation instructions
-------------------------

In a Devstack environment, add the following to your Devstack local.conf file::

    enable-plugin barbican https://github.com/openstack/barbican.git
    enable_plugin horizon-hpe-storage-ui https://github.com/hpe-storage/horizon-hpe-storage-ui.git


Or, to add to an existing Horizon virtual environment::

    cd horizon
    cd ..
    # create new package directory at same root path as Horizon
    git clone https://github.com/hpe-storage/horizon-hpe-storage-ui.git
    # install package
    cd horizon-hpe-storage-ui
    ../horizon/tools/with_venv.sh pip install --upgrade .
    # copy configuration file so that Horizon loads the plug-in
    cp -a horizon_hpe_storage/enabled/* ../horizon/openstack_dashboard/local/enabled

    # re-start Horizon. One way is to start a test server -
    cd ../horizon
    ./run_tests.sh --runserver 127.0.0.1:18000

    
After reloading the Horizon dashboard in your browser, log-in as an "Admin" user. If the plug-in
was successfully loaded, you should see a new "HPE Storage" panel listed at the bottom of the "Admin"
section.

Uninstalling the plug-in
------------------------

Uninstall the python package and remove the config files::

    sudo pip uninstall horizon-hpe-storage-ui
    rm horizon/openstack_dashboard/local/enabled/_999_hpe_storage_admin_panel.*

