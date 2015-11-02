# plugin.sh - DevStack plugin.sh dispatch script horizon-hpe-storage-ui

APP_LINK_DIR=$(cd $(dirname $BASH_SOURCE)/.. && pwd)

function install_horizon-hpe-storage-ui {
    sudo pip install --upgrade ${APP_LINK_DIR}
    cp -a ${APP_LINK_DIR}/horizon_hpe_storage/enabled/* ${DEST}/horizon/openstack_dashboard/local/enabled
    python ${DEST}/horizon/manage.py compress --force
}

if is_service_enabled horizon-hpe-storage-ui; then

    if [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Installing Horizon HPE Storage UI"
        install_horizon-hpe-storage-ui
    fi
fi