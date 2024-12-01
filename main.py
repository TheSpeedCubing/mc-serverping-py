import ipaddress
import json
import socket
import struct
import sys
import time
import traceback
import dns.resolver


def is_ip_address(string):
    try:
        ipaddress.ip_address(string)
        return True
    except ValueError:
        return False


def read_varint(sock):
    result = 0
    for byte_index in range(5):
        b = sock.recv(1)
        if len(b) == 0:
            raise IOError("varint error")
        result |= (b[0] & 0x7F) << 7 * byte_index
        if not b[0] & 0x80:
            break
    return result


def write_varint(buffer, value):
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            b |= 0x80
        buffer.append(b)
        if not value:
            break


def to_minecraft_color_code(c):
    color_map = {
        "black": "0",
        "dark_blue": "1",
        "dark_green": "2",
        "dark_aqua": "3",
        "dark_red": "4",
        "dark_purple": "5",
        "gold": "6",
        "gray": "7",
        "dark_gray": "8",
        "blue": "9",
        "green": "a",
        "aqua": "b",
        "red": "c",
        "light_purple": "d",
        "yellow": "e",
        "white": "f"
    }
    return color_map.get(c.lower(), None)


def findtext(o, s, color):
    if 'color' in o:
        color = "§" + to_minecraft_color_code(o['color'])
        s += color

    s += o['text']

    if 'extra' in o:
        for extra in o['extra']:
            s = findtext(extra, s, color)
    return s


def connect(hostname, port):
    socket_conn = socket.socket()
    try:
        start = time.time()
        print("Connecting to " + hostname + ":" + str(port))
        socket_conn.connect((hostname, port))
        ping = int((time.time() - start) * 1000)
        print("Connected.")
        print()

        # handshake
        hs = bytearray()
        write_varint(hs, 0)
        write_varint(hs, protocol)
        write_varint(hs, len(hostname))
        hs.extend(hostname.encode('utf-8'))
        hs.extend(struct.pack('>h', port))
        write_varint(hs, 1)

        handshake = bytearray()
        write_varint(handshake, len(hs))
        handshake.extend(hs)

        # status req
        write_varint(handshake, 1)
        write_varint(handshake, 0)

        socket_conn.sendall(handshake)

        # status res
        packet_len = read_varint(socket_conn)
        packet_id = read_varint(socket_conn)
        length = read_varint(socket_conn)

        data = b''
        while len(data) < length:
            received_bytes = socket_conn.recv(length - len(data))
            if not received_bytes:
                break
            data += received_bytes

        # ping req
        ping_request = bytearray()
        write_varint(ping_request, 9)
        write_varint(ping_request, 1)
        ping_request.extend(struct.pack('<Q', int(time.time() * 1000)))
        socket_conn.sendall(ping_request)

        # ping res
        packet_len = read_varint(socket_conn)
        packet_id = read_varint(socket_conn)

        socket_conn.close()

        print("----------------------------------")
        print("Result:")
        print(str(ping) + " ms")
        print()

        jsonstr = data.decode('utf-8')
        jsondata = json.loads(jsonstr)
        print(jsondata)
        print()

        result_version = jsondata['version']['name']
        print('Version: ' + result_version)
        print()

        result_protocol = jsondata['version']['protocol']
        print('Protocol: ' + str(result_protocol))
        print()

        player_max = jsondata['players']['max']
        print('Player Max: ' + str(player_max))
        print()

        player_online = jsondata['players']['online']
        print('Player Online: ' + str(player_online))
        print()

        if 'sample' in jsondata['players']:
            print('Player Samples: ')
            for i in jsondata['players']['sample']:
                print(i['id'] + "    " + i['name'])
            print()

        if 'favicon' in jsondata:
            print("Favicon: " + jsondata['favicon'])
            print()

        if isinstance(jsondata['description'], str):
            print("Description: \"" + jsondata['description'] + "\"")
            print()
        else:
            print("Description: \"" + findtext(jsondata['description'], "", "") + "\"")
            print()

        if 'modinfo' in jsondata:
            print("Modinfo: " + jsondata['modinfo']['type'])
            print()

    except Exception as e:
        print(e)
        print(traceback.format_exc())
    finally:
        socket_conn.close()


# start
def_hostname = sys.argv[1]
def_port = int(sys.argv[2])
protocol = int(sys.argv[3])

print("hostname: " + def_hostname)
print("port: " + str(def_port))
print("protocol: " + str(protocol))
print("----------------------------------")
print("Looking up for DNS...")
dns_list = []

result_hostname = None
result_port = None

if is_ip_address(def_hostname):
    result_hostname = def_hostname
    result_port = def_port
else:
    try:
        srv_records = dns.resolver.resolve("_minecraft._tcp." + def_hostname, "SRV")
        if srv_records:
            srv_record = srv_records[0]
            result_hostname = str(srv_record.target)[:-1]
            result_port = srv_record.port

            print("SRV Record found: " + str(srv_record)[:-1])

            dns_list.append(srv_record)

        while True:
            try:
                cname_records = dns.resolver.resolve(result_hostname, "CNAME")
                if cname_records:
                    for r in cname_records:
                        print("CNAME Record found: " + str(r))
                        dns_list.append(str(r))
                        result_hostname = str(r.target)[:-1]
                else:
                    break
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                break

        a_records = dns.resolver.resolve(result_hostname)
        if a_records:
            for r in a_records:
                print("A Record found: " + str(r)[:-1])
                dns_list.append(str(r))
            result_hostname = str(a_records[0])

    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
        pass

print("----------------------------------")
print("Final DNS Result: " + result_hostname + ":" + str(result_port))
print("----------------------------------")

connect(result_hostname, result_port)
