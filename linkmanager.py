#!/usr/bin/python

import os
import sys
import argparse
import requests
import multiprocessing
import time
import netifaces
import logging
import subprocess


LOG = logging.getLogger(__name__)


def registrator(args):
    while True:
        LOG.debug('registering address %s', args.address)
        res = requests.put('%s/v2/keys/%s/%s' % (args.etcd_server,
                                                 args.keyspace,
                                                 args.address),
                           data={'value': args.address,
                                 'ttl': args.ttl})
        time.sleep(args.ttl/2)


def ovs_bridge_exists(bridge):
    try:
        subprocess.check_call([
            'ovs-vsctl', 'br-exists', bridge])
    except subprocess.CalledProcessError:
        return False

    return True


def ovs_create_link(args, remote_addr):
    linkname = 'vxlan-%s' % '_'.join(remote_addr.split('.')[-2:])

    LOG.debug('creating ovs port %s', linkname)
    subprocess.check_output([
        'ovs-vsctl', '--may-exist',
        'add-port', args.bridge, linkname,
        '--',
        'set', 'interface', linkname, 'type=vxlan',
        'options:remote_ip=%s' % remote_addr
    ])


def ovs_remove_link(args, remote_addr):
    linkname = 'vxlan-%s' % '_'.join(remote_addr.split('.')[-2:])

    LOG.debug('removing ovs port %s', linkname)
    subprocess.check_output([
        'ovs-vsctl', '--if-exists',
        'del-port', args.bridge, linkname
    ])


def linkbuilder(args):
    active_links = set()

    while True:
        res = requests.get('%s/v2/keys/%s' % (args.etcd_server,
                                             args.keyspace))
        data = res.json()
        links = data['node'].get('nodes', [])
        LOG.debug('found %d links', len(links))
        found_links = set()
        for link in links:
            addr = link['value']
            LOG.debug('found link %s', addr)
            if addr == args.address:
                LOG.debug('%s is me (ignoring)', addr)
                continue

            found_links.add(addr)

        remove_links = []
        for link in active_links:
            if link not in found_links:
                LOG.info('removing link for %s' % link)
                remove_links.append(link)

        for link in remove_links:
            active_links.remove(link)
            ovs_remove_link(args, link)

        for link in found_links:
            if link not in active_links:
                LOG.info('adding link for %s' % link)
                active_links.add(link)
                ovs_create_link(args, link)

        # wait for updates
        requests.get('%s/v2/keys/%s' % (args.etcd_server,
                                        args.keyspace),
                     params={'wait': 'true',
                             'recursive': 'true'})


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--bridge', '-b',
                   default='obr0')
    p.add_argument('--etcd-server', '-s',
                   default='http://localhost:4001')
    p.add_argument('--device', '-d',
                   default='eth0')
    p.add_argument('--address', '-a',
                   default=None)
    p.add_argument('--keyspace', '-k',
                   default='links')
    p.add_argument('--ttl', '-t',
                   type=int,
                   default=30)

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


def main():
    args = parse_args()
    logging.basicConfig(
        level=args.loglevel)

    if not ovs_bridge_exists(args.bridge):
        LOG.error('ovs bridge %s does not exist', args.bridge)
        sys.exit(1)

    for mod in ['requests', 'urllib3']:
        l = logging.getLogger(mod)
        l.setLevel(logging.WARN)

    if not args.address:
        args.address = netifaces.ifaddresses(
            args.device)[netifaces.AF_INET][0]['addr']

    LOG.info('got address = %s', args.address)

    p0 = multiprocessing.Process(target=registrator,
                                 args=(args,))
    p0.start()

    p1 = multiprocessing.Process(target=linkbuilder,
                                 args=(args,))
    p1.start()

    p0.join()
    p1.join()


if __name__ == '__main__':
    main()
