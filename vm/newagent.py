import socket, json, sys, select, os
from time import time, sleep
import logging

max_delta_seconds=120


class QemuAgent:
    def __init__(self, sockpath):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.s.connect(sockpath)
        self.seconds = 1

    def close(self):
        self.s.close()

    def flush(self):
        _c_read, _, _ = select.select([self.s], [], [], self.seconds)
        if len(_c_read) > 0:
            data = _c_read[0].recv(1024)
            print(data)

    def send(self, dict_message):
        self.flush()
        self.s.send((json.dumps(dict_message) + '\r\n').encode('ascii'))
        logging.debug("Sending: " + json.dumps(dict_message) + '\r\n')
        data = ""

        while True:
            _c_read, _, _ = select.select([self.s], [], [], self.seconds)
            if len(_c_read) == 0:
                break
            data += _c_read[0].recv(1024).decode('ascii')
        logging.debug("Receiving: " + data)
        return data
        
    def guest_get_time(self):
        get_time = { "execute": "guest-get-time" }
        data = self.send(get_time)
        t = json.loads(data)
        return t.get('return', 0) / 1000000000

    def guest_set_time(self, time):
        set_time = {
            "execute": "guest-set-time", 
            "arguments": { 
                "time":  int(time * 1000000000)
            }
        }
        data = self.send(set_time)
        return data

    def sync_time(s):
        vmtime = get_time_seconds(s)
        curtime = time()
        delta = (curtime - vmtime)
        if delta > max_delta_seconds:
            _ = set_time_seconds(s, curtime)

def main(sockpath):
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        print("fork failed %d (%s)" % (e.errno, e.strerror))
        sys.exit(1)

    while True:
        if os.path.exists(sockpath):
            break
        sleep(10)

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sockpath)

    try:
        while True:
            sync_time(s)
            flush(s, 60)
    except:
        pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise TypeError("must define config file")
    main(sys.argv[1])
