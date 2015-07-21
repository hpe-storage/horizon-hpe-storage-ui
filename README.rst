===============================
horizon-ssmc-link
===============================

HP Storage Dashboard

* Free software: Apache license

Overview
---------

This plug-in extends the OpenStack Horizon Dashboard.

It adds an "HP Storage" panel to the Admin dashboard. When this panel is selected,
the associated window will have tabs to manage/view HP Storage related data. One of
these tabs will be labeled "Backend SSMC Endpoints", which will allow an admin user
to associate an HP 3PAR SSMC instance with an OpenStack storage backend (as defined
by /etc/cinder/cinder.conf).

Requirements
------------

The OpenStack Barbican service is required for this plug-in.


Installation instructions
-------------------------

Create a virtual environment and install Horizon dependencies::

    cd horizon
    python tools/install_venv.py

Set up your ``local_settings.py`` file::

    cp openstack_dashboard/local/local_settings.py.example openstack_dashboard/local/local_settings.py

Open up the copied ``local_settings.py`` file in your preferred text
editor. You will want to customize several settings:

-  ``OPENSTACK_HOST`` should be configured with the hostname of your
   OpenStack server. Verify that the ``OPENSTACK_KEYSTONE_URL`` and
   ``OPENSTACK_KEYSTONE_DEFAULT_ROLE`` settings are correct for your
   environment. (They should be correct unless you modified your
   OpenStack server to change them.)

Install horizon-ssmc-link with all dependencies in your virtual environment::

    tools/with_venv.sh pip install -i https://testpypi.python.org/pypi horizon_ssmc_link

To enable it in Horizon, from your Horizon directory, copy and paste the
following commands into your shell to create a horizon to SSMC config file::

    cd openstack_dashboard/local/enabled
    cat <<EOF > _150_ssmc_link.py
    PANEL_DASHBOARD = 'admin'
    PANEL_GROUP = 'admin'
    PANEL = 'ssmc_link'
    ADD_PANEL = 'horizon_ssmc_link.storage_panel.panel.SSMCLink'
    ADD_INSTALLED_APPS = ['horizon_ssmc_link.storage_panel']
    UPDATE_HORIZON_CONFIG = {
        'customization_module': 'horizon_ssmc_link.overrides',
    }
    EOF
    cd ../../..

Starting the app
----------------

If everything has gone according to plan, you should be able to run::

    ./run_tests.sh --runserver 0.0.0.0:8080

and have the application start on port 8080. The horizon dashboard will
be located at http://localhost:8080/
