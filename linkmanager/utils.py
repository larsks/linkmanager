import hmac
import hashlib

def sign_address (address, key):
    d = hmac.HMAC(key, msg=address, digestmod=hashlib.sha256)
    return d.hexdigest()

