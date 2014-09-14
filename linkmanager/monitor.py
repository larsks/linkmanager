import logging
import multiprocessing
import requests
import time

from .manager import Manager

class Monitor (multiprocessing.Process):
    def __init__(self, address, etcd_client,
                 bridge='obr0',
                 ttl=30,
                 prefix='links'):

        super(Monitor, self).__init__()
        self.log = logging.getLogger('Monitor')
        self.address = address
        self.ttl = ttl
        self.prefix = prefix
        self.client = etcd_client
        self.bridge = bridge

    def run(self):
        self.log.info('starting monitor for address %s',
                      self.address)
        with Manager(self.bridge) as manager:
            while True:
                try:
                    hosts = set(x['value'] for x in
                                self.client.get_all('%s/' % self.prefix))

                    for host in hosts:
                        self.log.debug('found host %s', host)
                        if host == self.address:
                            continue

                        if not manager.has_link(host):
                            manager.add_link(host)

                    for link in manager.active_links:
                        if not link.remote_addr in hosts:
                            manager.remove_link(link)
                except requests.RequestException as error:
                    self.log.warn('error communicating with etcd: %s',
                                  error)

                try:
                    self.client.wait('%s/' % self.prefix, recursive=True)
                    self.log.debug('waking up!')
                except requests.RequestException as error:
                    time.sleep(self.ttl/2)

