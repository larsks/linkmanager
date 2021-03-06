#!/usr/bin/python

import argparse
import logging
import netifaces
import os

from .registrator import Registrator
from .monitor import Monitor
from .etcd import Etcd

LOG = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--bridge', '-b',
                   default='obr0',
                   help='Name of OVS bridge to manage')
    p.add_argument('--etcd-server', '-s',
                   default='http://localhost:4001',
                   help='URL to etcd server')
    p.add_argument('--device', '-d',
                   default='eth0',
                   help='Device from which to discover local address')
    p.add_argument('--address', '-a',
                   default=None,
                   help='Use an explicit address')
    p.add_argument('--prefix', '-p',
                   default='links',
                   help='Use this key path in etcd')
    p.add_argument('--ttl', '-t',
                   type=int,
                   default=30,
                   help='Expiration time for host registrations')
    p.add_argument('--secret', '-S',
                   help='Used to sign addresses in etcd')


    p.add_argument('--verbose', '-v',
                   action='store_const',
                   const=logging.INFO,
                   dest='loglevel')
    p.add_argument('--debug', '-D',
                   action='store_const',
                   const=logging.DEBUG,
                   dest='loglevel')

    p.set_defaults(loglevel=logging.WARN)
    return p.parse_args()


def get_my_address(device):
    address = netifaces.ifaddresses(
        device)[netifaces.AF_INET][0]['addr']
    LOG.info('got address %s from device %s',
             address, device)

    return address


def main():
    args = parse_args()
    logging.basicConfig(
        level=args.loglevel)

    # disable debug logging from imported
    # modules.
    for mod in ['requests', 'urllib3']:
        l = logging.getLogger(mod)
        l.setLevel(logging.WARN)

    if not args.address:
        args.address = get_my_address(args.device)

    LOG.info('using address %s', args.address)

    client = Etcd(args.etcd_server)

    reg = Registrator(args.address, client,
                      prefix=args.prefix,
                      ttl=args.ttl,
                      key=args.secret)
    monitor = Monitor(args.address, client,
                      prefix=args.prefix,
                      ttl=args.ttl,
                      key=args.secret)

    reg.start()
    monitor.start()

    reg.join()
    monitor.join()

if __name__ == '__main__':
    main()
