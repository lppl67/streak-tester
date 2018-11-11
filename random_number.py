import random
import hashlib
import hmac
import secrets


def create_seed():
    return secrets.token_hex(32)


def hashed_seed(seed):
    hashed = str(hashlib.sha256(str(seed).encode('utf-8')).hexdigest())
    return hashed


def roll_dice(server, client):
    index = 0
    hasher = hmac.new(bytes(str(server), "ascii"), bytes(str(client), "ascii"), hashlib.sha512).hexdigest()
    lucky = int(hasher[index * 5:index * 5 + 5], 16)
    while lucky >= 999_999:
        index += 1
        lucky = int(hasher[index * 5:index * 5 + 5], 16)
        if index * 5 + 5 > 128:
            lucky = 99.99
            break
    lucky %= 10_000
    lucky /= 100
    return lucky
