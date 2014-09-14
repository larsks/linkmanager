#!/usr/bin/python

import argparse
import hmac
import json
import logging
import multiprocessing
import netifaces
import os
import re
import requests
import subprocess
import sys
import time


RE_IP = re.compile('^\d{,3}\.\d{,3}\.\d{,3}\.\d{,3}$')
LOG = logging.getLogger(__name__)


def registrator(args):
    while True:
        LOG.debug('registering address %s', args.address)
        try:
            res = requests.put('%s/v2/keys/%s/%s' % (args.etcd_server,
                                                     args.keyspace,
                                                     args.address),
                               data={'value': args.address,
                                     'ttl': args.ttl})
            res.raise_for_status()
        except requests.HTTPError as error:
            LOG.warn('received error %d (%s) trying to contact etcd',
                     error.response.status_code,
                     error.response.reason)
        except requests.RequestException as error:
            LOG.warn('unable to connect to etcd: %s',
                     error)
        # sleep for a little less than 1/2 the ttl before re-registering.
        time.sleep(max(1, (args.ttl/2)-2))


def ovs_bridge_exists(bridge):
    try:
        subprocess.check_call([
            'ovs-vsctl', 'br-exists', bridge])
    except subprocess.CalledProcessError:
        return False

    return True


def ovs_create_link(args, remote_addr):
    linkname = 'vxlan-%s' % '_'.join(remote_addr.split('.')[-2:])

    LOG.info('creating ovs port %s', linkname)
    subprocess.check_output([
        'ovs-vsctl', '--may-exist',
        'add-port', args.bridge, linkname,
        '--',
        'set', 'interface', linkname, 'type=vxlan',
        'options:remote_ip=%s' % remote_addr
    ])


def ovs_remove_link(args, remote_addr):
    linkname = 'vxlan-%s' % '_'.join(remote_addr.split('.')[-2:])

    LOG.info('removing ovs port %s', linkname)
    subprocess.check_output([
        'ovs-vsctl', '--if-exists',
        'del-port', args.bridge, linkname
    ])


def interface_exists(iface):
    return iface in netifaces.interfaces()


def find_registered_links(args):
    res = requests.get('%s/v2/keys/%s' % (args.etcd_server,
                                          args.keyspace))

    res.raise_for_status()

    data = res.json()
    links = data.get('node', {}).get('nodes', [])
    LOG.debug('found %d links', len(links))
    found_links = set()
    for link in links:
        addr = link['value']
        LOG.debug('found link %s', addr)
        if addr == args.address:
            LOG.debug('%s is me (ignoring)', addr)
            continue

        found_links.add(addr)

    return found_links


def wait_for_updates(args):
        # wait for updates
        LOG.debug('sleeping for new links')
        try:
            requests.get('%s/v2/keys/%s' % (args.etcd_server,
                                            args.keyspace),
                         params={'wait': 'true',
                                 'recursive': 'true'})
        except requests.RequestException as error:
            LOG.warn('unable to connect to etcd: %s',
                     error)
            time.sleep(args.ttl/2)

        LOG.debug('waking up for new links')


def linkbuilder(args):
    active_links = set()

    try:
        while True:
            try:
                registered_links = find_registered_links(args)
            except requests.RequestException as error:
                LOG.warn('unable to connect to etcd: %s',
                         error)
                time.sleep(args.ttl/2)
                continue

            remove_links = []
            for link in active_links:
                if link not in registered_links:
                    LOG.debug('going to remove link for %s' % link)
                    remove_links.append(link)

            for link in remove_links:
                active_links.remove(link)
                ovs_remove_link(args, link)

            for link in registered_links:
                if link not in active_links:
                    LOG.debug('going to add link for %s' % link)
                    active_links.add(link)
                    ovs_create_link(args, link)

            wait_for_updates(args)
    finally:
        for link in active_links:
            ovs_remove_link(args, link)


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

    p.add_argument('--secret', '-S',
                   default=os.environ.get('LINKMANAGER_SECRET'))

    p.set_defaults(loglevel=logging.WARN)
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(
        level=args.loglevel)

    if not interface_exists(args.device):
        LOG.error('network device %s does not exist', args.device)
        sys.exit(1)

    if not ovs_bridge_exists(args.bridge):
        LOG.error('ovs bridge %s does not exist', args.bridge)
        sys.exit(1)

    for mod in ['requests', 'urllib3']:
        l = logging.getLogger(mod)
        l.setLevel(logging.WARN)

    if not args.address:
        args.address = netifaces.ifaddresses(
            args.device)[netifaces.AF_INET][0]['addr']
        LOG.info('got address %s from device %s',
                 args.address, args.device)

    LOG.info('using address %s', args.address)

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
