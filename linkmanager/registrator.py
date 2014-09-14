import logging
import multiprocessing
import requests
import time


class Registrator (multiprocessing.Process):
    def __init__(self, address, etcd_client, ttl=30, prefix='links'):
        super(Registrator, self).__init__()
        self.log = logging.getLogger('Registrator')
        self.address = address
        self.ttl = ttl
        self.prefix = prefix
        self.client = etcd_client

    def run(self):
        self.log.info('starting registrator for address %s',
                      self.address)
        while True:
            self.log.debug('registering address %s', self.address)
            try:
                self.client.set('%s/%s' % (self.prefix, self.address),
                                self.address, ttl=self.ttl)
            except requests.RequestException as error:
                self.log.warn('failed to register: %s',
                              error)

            time.sleep(max(1, (self.ttl/2)-2))


