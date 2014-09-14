import requests
import json


class Etcd(object):
    def __init__(self, endpoint='http://localhost:4001'):
        self.endpoint = endpoint

    def set(self, key, value, ttl=None):
        uri = '%s/v2/keys/%s' % (self.endpoint, key)
        data = {'value': value}
        if ttl is not None:
            data['ttl'] = ttl

        res = requests.put(uri, data=data)
        res.raise_for_status()
        return res.json()

    def append(self, key, value, ttl=None):
        uri = '%s/v2/keys/%s' % (self.endpoint, key)
        data = {'value': value}
        if ttl is not None:
            data['ttl'] = ttl

        res = requests.post(uri, data=data)
        res.raise_for_status()
        return res.json()

    def mkdir(self, key, ttl=None):
        uri = '%s/v2/keys/%s' % (self.endpoint, key)
        data = {'dir': True}
        if ttl is not None:
            data['ttl'] = ttl

        res = requests.put(uri, data=data)
        res.raise_for_status()
        return res.json()

    def rmdir(self, key, recursive=False):
        uri = '%s/v2/keys/%s?dir=true&recursive=%s' % (
            self.endpoint, key,
            'true' if recursive else 'false',
        )
        res = requests.delete(uri)

        res.raise_for_status()
        return res.json()

    def get(self, key, recursive=False):
        uri = '%s/v2/keys/%s?recursive=%s' % (
            self.endpoint,
            key,
            'true' if recursive else 'false',
        )
        res = requests.get(uri)
        res.raise_for_status()
        return res.json()

    def wait(self, key, recursive=False):
        uri = '%s/v2/keys/%s?wait=true&recursive=%s' % (
            self.endpoint,
            key,
            'true' if recursive else 'false',
        )
        res = requests.get(uri)
        res.raise_for_status()
        return res.json()

    def get_all(self, key):
        uri = '%s/v2/keys/%s' % (self.endpoint, key)
        res = requests.get(uri)
        res.raise_for_status()
        data = res.json()

        return data['node'].get('nodes', [])

    def delete(self, key):
        uri = '%s/v2/keys/%s' % (self.endpoint, key)
        res = requests.delete(uri)
        res.raise_for_status()
        return res.json()


if __name__ == '__main__':
    c = Etcd()

