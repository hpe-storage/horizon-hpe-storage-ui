# plugin.sh - DevStack plugin.sh dispatch script horizon-ssmc-link

APP_LINK_DIR=$(cd $(dirname $BASH_SOURCE)/.. && pwd)

function install_horizon-ssmc-link {
    sudo pip install --upgrade ${APP_LINK_DIR}
    cp -a ${APP_LINK_DIR}/horizon_ssmc_link/enabled/* ${DEST}/horizon/openstack_dsahboard/enabled/
    python ${DEST}/horizon/manage.py compress --force
}

if is_service_enabled horizon-ssmc-link; then

    if [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Installing HP Horizon-SSMC-LINK UI"
        install_horizon-ssmc-link
    fi
fi