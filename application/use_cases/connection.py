from time import sleep
from shlex import split

from application.ports.os import OS
from inetman import RunPONConfigParser

CONNECT_WAIT_TIMEOUT = 60

def is_connected(os: OS, iface: str) -> bool:
    return os.iface_exists(iface)


def connect(os: OS, config: RunPONConfigParser, iface: str, wait: bool) -> None:
    if not is_connected(os, iface):
        os.run(split(config.getValue('on', None, 'pon')))
        if wait:
            waited = 0
            while not is_connected(os, iface) and waited < CONNECT_WAIT_TIMEOUT:
                sleep(1)
                waited += 1
            if waited >= CONNECT_WAIT_TIMEOUT and not is_connected(os, iface):
                raise TimeoutError('Interface did not appear within timeout')


def disconnect(os: OS, config: RunPONConfigParser, iface: str) -> None:
    if is_connected(os, iface):
        os.run(split(config.getValue('off', None, 'poff')))
