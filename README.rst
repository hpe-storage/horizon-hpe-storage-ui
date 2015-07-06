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

Installation instructions
-------------------------

Begin by cloning the horizon-ssmc-link repository to your OpenStack root directory:

    git clone https://github.com/hp-storage/horizon-ssmc-link.git

To enable it in Horizon::

    cp ../horizon-ssmc-link/ssmc-link-ui/enabled/_110_ssmc_link_*.py openstack_dashboard/local/enabled


Starting the app
----------------

If everything has gone according to plan, you should be able to run::

    ./run_tests.sh --runserver 0.0.0.0:8080

and have the application start on port 8080. The horizon dashboard will
be located at http://localhost:8080/
