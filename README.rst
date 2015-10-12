=================
horizon-ssmc-link
=================

HP Storage Dashboard

* Free software: Apache license

Overview
========

This plug-in extends the OpenStack Horizon Dashboard.

It adds an "HP Storage" panel to the Admin dashboard. When this panel is selected,
the associated window will have tabs to manage/view HP Storage related data. One of
these tabs will be labeled "SSMC Links", which will allow an admin user
to associate an HP 3PAR SSMC instance with an OpenStack storage backend (as defined
by /etc/cinder/cinder.conf).

Requirements
============

The OpenStack Barbican service is required for this plug-in.
(see https://wiki.openstack.org/wiki/Barbican)

This plug-in is only intended for use on systems running Horizon.

Installation instructions
=========================

With Devstack
------------
Add the following to your Devstack local.conf file

::

    enable_plugin horizon-ssmc-link https://github.com/hp-storage/horizon-ssmc-link.git

With Horizon
------------

::

    git clone http://github.com/openstack/horizon.git
    git clone https://github.com/hp-storage/horizon-ssmc-link.git
    cd horizon
    ./run_tests.sh -f
    cp ./openstack_dashboard/local/local_settings.py.example ./opentstack_dashboard/local/local_settings.py
    pushd ../horizon-ssmc-link
    ../horizon/tools/with_venv.sh pip install --upgrage .
    cp -a horizon_ssmc_link/enabled/* ../horizon/openstack_dashboard/local/enabled
    popd

    # Start test server
    ./run_tests.sh --runserver 127.0.0.1:18000

    
After reloading the Horizon dashboard in your browser, log-in as an "Admin" user. If the plug-in
was successfully loaded, you should see a new "HP Storage" panel listed at the bottom of the "Admin"
section.

Uninstalling the plug-in
------------------------

Uninstall the python package and remove the config files::

    sudo pip uninstall horizon-ssmc-link
    rm horizon/openstack_dashboard/local/enabled/_*_ssmc_link_admin_panel.*

