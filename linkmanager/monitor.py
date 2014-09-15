import json
import logging
import multiprocessing
import requests
import time

from .manager import Manager
from .utils import sign_address


class Monitor (multiprocessing.Process):
    def __init__(self, address, etcd_client,
                 bridge='obr0',
                 ttl=30,
                 prefix='links',
                 key=None):

        super(Monitor, self).__init__()
        self.log = logging.getLogger('Monitor')
        self.address = address
        self.ttl = ttl
        self.prefix = prefix
        self.client = etcd_client
        self.bridge = bridge
        self.key = key if key is not None else ''

    def run(self):
        self.log.info('starting monitor for address %s',
                      self.address)
        with Manager(self.bridge) as manager:
            while True:
                try:
                    hosts = (json.loads(x['value']) for x in
                                self.client.get_all('%s/' % self.prefix))
                    host_addr = set()

                    for host in hosts:
                        self.log.debug('found host %s', host['address'])

                        # verify the signature
                        checksig = sign_address(host['address'], self.key)
                        if host['sig'] != checksig:
                            self.log.warn('bad signature for %s',
                                          host['address'])
                            continue

                        # don't try to link to ourself.
                        if host['address'] == self.address:
                            self.log.debug('skipping %s (mine)',
                                           host['address'])
                            continue

                        # record all valid addresses
                        host_addr.add(host['address'])

                        # add missing links
                        if not manager.has_link(host['address']):
                            manager.add_link(host['address'])

                    # remove any links to hosts that are no
                    # longer registered.
                    for link in manager.active_links:
                        if not link.remote_addr in host_addr:
                            manager.remove_link(link)
                except requests.RequestException as error:
                    self.log.warn('error communicating with etcd: %s',
                                  error)

                try:
                    self.client.wait('%s/' % self.prefix, recursive=True)
                    self.log.debug('waking up!')
                except requests.RequestException as error:
                    time.sleep(self.ttl/2)

