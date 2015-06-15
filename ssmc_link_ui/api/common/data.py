from openstack_dashboard.api import base

class SSMCLinkSession(base.APIResourceWrapper):
    _attrs = ['token', 'tenant_id', 'cinder_url', 'barbican_url']


class SSMCLinkEndpoint(base.APIResourceWrapper):
    _attrs = ['backend_name', 'uname', 'pwd']


