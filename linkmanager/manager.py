#!/usr/bin/python

import logging
import subprocess
import re


re_ip = re.compile('^\d{,3}\.\d{,3}\.\d{,3}\.\d{,3}$')


def vsctl(*args):
    output = subprocess.check_output(
        ('ovs-vsctl',) + args)
    return output.strip()


def ovs_bridge_exists(bridge):
    try:
        vsctl('br-exists', bridge)
    except subprocess.CalledProcessError:
        return False

    return True


class Link(object):
    def __init__(self, remote_addr, iface=None):
        assert re_ip.match(remote_addr), (
               '%s is not a valid ip address' % remote_addr)
        self.remote_addr = remote_addr

        if iface is None:
            iface = 'vxlan-%s-%s' % (
                tuple(remote_addr.split('.')[2:]))

        self.iface = iface

    def __str__(self):
        return '<Link %s to %s>' % (
            self.iface, self.remote_addr)

    def __repr__(self):
        return str(self)


class Manager(object):
    def find_active_links(self):
        ifaces = vsctl('list-ifaces', self.bridge)
        for iface in ifaces.split():
            remote_addr = vsctl('get', 'interface',
                                iface, 'options:remote_ip')
            remote_addr = remote_addr[1:-1]
            self.log.debug('found link %s to %s',
                           iface,
                           remote_addr)
            link = Link(remote_addr, iface)
            self._active_links[remote_addr] = link

    def __init__(self, bridge='obr0'):
        assert ovs_bridge_exists(bridge)
        self.log = logging.getLogger('Manager')
        self.bridge = bridge
        self._active_links = {}
        self.find_active_links()

    def add_link(self, remote_addr):
        if remote_addr in self._active_links:
            link = self._active_links[remote_addr]
            self.log.warn('link %s is already active for %s',
                          link.iface, link.remote_addr)
            return

        link = Link(remote_addr)
        self.log.info('adding link %s to %s',
                      link.iface,
                      link.remote_addr)
        vsctl('--may-exist',
              'add-port', self.bridge, link.iface,
              '--',
              'set', 'interface', link.iface, 'type=vxlan',
              'options:remote_ip=%s' % link.remote_addr
              )
        self._active_links[link.remote_addr] = link

    def remove_link(self, target):
        link = self._active_links[target.remote_addr]
        self.log.info('removing link %s to %s',
                      link.iface,
                      link.remote_addr)
        if link.iface != target.iface:
            self.log.warn('link name mismatch: target=%s, active=%s',
                          target.iface,
                          link.iface)

        vsctl('del-port', self.bridge, link.iface)
        del self._active_links[target.remote_addr]

    def remove_all_links(self):
        self.log.info('removing all links')
        for link in self._active_links.values():
            self.remove_link(link)

    def has_link(self, remote_addr):
        return remote_addr in self._active_links

    @property
    def active_links(self):
        return self._active_links.values()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.remove_all_links()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    l = Manager()
