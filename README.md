This is a simple tool to maintain a vxlan overlay network among a
group of hosts.  It was designed for use with Kubernetes and relies on
etcd to handle host discovery.

When you run Linkmanager, it will start two processes:

- One will register the current host in etcd at regular intervals.
  These registrations have an associated TTL so that if the host goes
  down, the registration will expire and participating hosts will tear
  down the associated VXLAN links.

- The other watches the registry for updates, and creates or removes
  VXLAN links as appropriate.


## Synopsis

    usage: linkmanager [-h] [--bridge BRIDGE] [--etcd-server ETCD_SERVER]
                       [--device DEVICE] [--address ADDRESS] [--prefix PREFIX]
                       [--ttl TTL] [--secret SECRET] [--verbose] [--debug]

## Options

    -h, --help            show this help message and exit
    --bridge BRIDGE, -b BRIDGE
                          Name of OVS bridge to manage
    --etcd-server ETCD_SERVER, -s ETCD_SERVER
                          URL to etcd server
    --device DEVICE, -d DEVICE
                          Device from which to discover local address
    --address ADDRESS, -a ADDRESS
                          Use an explicit address
    --prefix PREFIX, -p PREFIX
                          Use this key path in etcd
    --ttl TTL, -t TTL     Expiration time for host registrations
    --secret SECRET, -S SECRET
                          Used to sign addresses in etcd
    --verbose, -v
    --debug, -D

## Security

All hosts participating in the overlay network must use the same value
for `--secret`.  This used to generate a SHA256 HMAC signature on
registrations in etcd.

## Example usage

Starting `linkmanager`:

    /usr/bin/linkmanager -v \
      -s http://10.0.0.2:4001 \
      -b obr0 \
      --secret g1wzkgjbnxc9nfmfg763dRNibLXoqffJ

Output in system log:

    systemd[1]: Starting Linkmanager VXLAN link builder...
    systemd[1]: Started Linkmanager VXLAN link builder.
    linkmanager[7206]: INFO:linkmanager.main:got address 10.0.0.5 from device eth0
    linkmanager[7206]: INFO:linkmanager.main:using address 10.0.0.5
    linkmanager[7206]: INFO:Registrator:starting registrator for address 10.0.0.5
    linkmanager[7206]: INFO:Monitor:starting monitor for address 10.0.0.5
    linkmanager[7206]: INFO:Manager:adding link vxlan-0-4 to 10.0.0.4
    ovs-vsctl[7239]: ovs|00001|vsctl|INFO|Called as ovs-vsctl --may-exist add-port obr0 vxlan-0-4 -- set interface vxlan-0-4 type=vxlan options:remote_ip=10.0.0.4

Resulting OVS configuration:

    # ovs-vsctl show
    ab2fa1e0-29e0-4f39-bdbf-6d0a73d3e99a
        Bridge "obr0"
            Port "obr0"
                Interface "obr0"
                    type: internal
            Port "vxlan-0-4"
                Interface "vxlan-0-4"
                    type: vxlan
                    options: {remote_ip="10.0.0.4"}
        ovs_version: "2.3.0"

