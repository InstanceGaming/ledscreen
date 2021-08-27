

def unix_get_ip_address(filter_if_name: str):
    import fcntl
    import socket
    import struct

    if_name_bytes = bytes(filter_if_name[:15], 'UTF-8')
    if_name_packed = struct.pack('256s', if_name_bytes)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ioctl_result = fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        if_name_packed
    )
    return socket.inet_ntoa(ioctl_result[20:24])


def get_ip_address(filter_if_name: str):
    from netifaces import AF_INET, ifaddresses
    interface = ifaddresses(filter_if_name)
    protocol = interface[AF_INET]
    return protocol[0]['addr']
