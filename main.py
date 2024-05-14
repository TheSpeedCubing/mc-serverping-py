import json
import socket
import struct
import time
import traceback

import dns.resolver

def read_varint(sock):
    result = 0
    for i in range(5):
        b = sock.recv(1)
        if len(b) == 0:
            raise IOError("?")
        result |= (b[0] & 0x7F) << 7 * i
        if not b[0] & 0x80:
            break
    return result


def write_varint(bytes, value):
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            b |= 0x80
        bytes.append(b)
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

def findText(o, s, color):
    if 'color' in o:
        color = "§" + to_minecraft_color_code(o['color'])
        s += color

    s += o['text']

    if 'extra' in o:
        for e in o['extra']:
            s = findText(e.getAsJsonObject(), s, color);
    return s

# configuration
hostname = "speedcubing.top"
port = 25565
protocol = 47

print("hostname: " + hostname)
print("port: " + hostname)
print("protocol: " + str(protocol))
print("----------------------------------")
print("Looking up for DNS...")
dns_list = []


try:
    srv_records = dns.resolver.resolve("_minecraft._tcp." + hostname, "SRV")
    if srv_records:
        srv_record = srv_records[0]
        srv_hostname = str(srv_record.target)[:-1]
        srv_port = srv_record.port

        print("SRV Record found: " + str(srv_record))

        dns_list.append(srv_record)
        srv = True

        cname_records = []
        try:
            cname_records = dns.resolver.resolve(srv_hostname, "CNAME")
            if cname_records:
                for i in cname_records:
                    print("CNAME Record found: " + str(i))
                dns_list.extend(cname_records)
                srv_hostname = str(cname_records[-1].target) if cname_records != [] else srv_hostname
        except:
            pass
    try:
        a_records = dns.resolver.resolve(srv_hostname)
        if a_records:
            for i in a_records:
                print("A Record found: " + str(i))
            dns_list.extend(a_records)
            srv_hostname = str(a_records[0])
    except Exception as e:
        pass
except:
    pass

print("----------------------------------")
print("Final DNS Result: " + srv_hostname + ":" + str(srv_port))
print("----------------------------------")

try:
    socket_conn = socket.socket()
    start = time.time()
    print("Connecting to " + srv_hostname + ":" + str(srv_port))
    socket_conn.connect((srv_hostname, srv_port))
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
        r = socket_conn.recv(length - len(data))
        if not r:
            break
        data += r

    # ping req
    ping_request = bytearray()
    write_varint(ping_request,9)
    write_varint(ping_request,1)
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

    jsonStr = data.decode('utf-8')
    jsonData = json.loads(jsonStr)
    print(jsonData)
    print()

    result_versionName = jsonData['version']['name']
    print('Version: ' + result_versionName)
    print()

    result_protocol = jsonData['version']['protocol']
    print('Protocol: ' + str(result_protocol))
    print()

    playerMax = jsonData['players']['max']
    print('Player Max: ' + str(playerMax))
    print()

    playerOnline = jsonData['players']['online']
    print('Player Online: ' + str(playerOnline))
    print()

    if 'sample' in jsonData['players']:
        print('Player Samples: ')
        for i in jsonData['players']['sample']:
            print(i['id'] + "    " + i['name'])
        print()

    if 'favicon' in jsonData:
        print("Favicon: " + jsonData['favicon'])
        print()

    if isinstance(jsonData['description'], str):
        print("Description: \"" + jsonData['description'] + "\"")
        print()
    else:
        print("Description: \"" + findText(jsonData['description'], "", "") + "\"")
        print()

    if 'modinfo' in jsonData:
        print("Modinfo: " + jsonData['modinfo']['type'])
        print()

except Exception as e:
    print(e)
    print(traceback.format_exc())
finally:
    socket_conn.close()
