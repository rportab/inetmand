from application.use_cases import connection
from inetman import config
from infrastructure.output.os import LinuxOSImpl

# this is intended to be used when called from another program in the same computer
# adjust to your convenience
# logging.basicConfig(level=logging.DEBUG, filename='/var/log/inetmand.log')

def connected() -> bool:
    return connection.is_connected(
        os=LinuxOSImpl(),
        iface=config.getValue('check_interface'),
    )

def connect(wait:bool) -> None:
    connection.connect(
        os=LinuxOSImpl(),
        config=config,
        wait=wait,
        iface=config.getValue('check_interface'),
    )

def disconnect() -> None:
    connection.disconnect(
        os=LinuxOSImpl(),
        config=config,
        iface=config.getValue('check_interface'),
    )
