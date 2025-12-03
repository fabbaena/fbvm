import socket, json, sys, select, os
from time import time, sleep
from base64 import b64encode
from datetime import datetime
import logging

max_delta_seconds=120
log = logging.getLogger(__name__)

logging.basicConfig(stream=sys.stderr)

class QemuAgent:
    def __init__(self, sockpath, debug=False):
        if not os.path.exists(sockpath):
            raise TypeError(f"Socket path {sockpath} doesn't exist")
        self._sockpath = sockpath
        if debug:
            log.setLevel("DEBUG")

    def __enter__(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self._sockpath)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sock:
            self.sock.close()

    def send(self, message):
        if not isinstance(message, dict):
            raise TypeError("Message must be a dictionary")
        msg = json.dumps(message)
        log.debug(msg)
        self.sock.send((msg + '\r\n').encode('ascii'))
        data = ""
        while True:
            outs, _, _ = select.select([self.sock], [], [], 1)
            if len(outs) == 0:
                break
            temp = self.sock.recv(1024).decode('ascii')
            data += temp
        log.debug("\"%s\"", data)
        if data is None or len(data) == 0:
            raise Exception("Host Disconnected")

        out = json.loads(data)
        if "error" in out:
            e = out['error']
            raise Exception("%s: %s" % 
                (e.get("class", "UnknownClass"), e.get("desc", "No Description")))
        if "return" in out:
            return out['return']
        raise Exception("Invalid output: %s", out)

    def guest_exec(self, path, arg=[], env=[], input_data=None, capture_output=None):
        if not isinstance(path, str):
            raise TypeError("path must be str")
        if not isinstance(arg, list):
            raise TypeError("arg must be list")
        if not isinstance(env, list):
            raise TypeError("env must be list")
        if input_data is not None and not isinstance(input_data, bytes):
            raise TypeError("input_data must be bytes")
        if capture_output is not None and not isinstance(capture_output, bool):
            raise TypeError("capture_output must be bool")

        message = {
            "execute": "guest-exec",
            "arguments": {
                "path": path
            }
        }
        if len(arg) > 0:
            message["arguments"]["arg"] = arg
        if len(env) > 0:
            message["arguments"]["env"] = env
        if input_data is not None:
            message["arguments"]["input-data"] = b64encode(input_data)
        if capture_output is not None:
            message["arguments"]["capture-output"] = capture_output
        return self.send(message)

    def guest_exec_status(self, pid):
        message = {
            "execute": "guest-exec-status",
            "arguments": {
                "pid": pid
            }
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_file_close(self, handle):
        if not isinstance(handle, int):
            raise TypeError("handle must be int")
        message = {
            "execute": "guest-file-close",
            "arguments": {
                "handle": handle
            }
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_file_flush(self, handle):
        if not isinstance(handle, int):
            raise TypeError("handle must be int")
        message = {
            "execute": "guest-file-read",
            "arguments": {
                "handle": handle
            }
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_file_open(self, path, mode="r"):
        if not isinstance(path, str):
            raise TypeError("path must be str")
        if not isinstance(mode, str):
            raise TypeError("mode must be str")
        message = {
            "execute": "guest-file-open",
            "arguments": {
                "path": path,
                "mode": mode
            }
        }
        ret = self.send(message)
        if not isinstance(ret, int):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_file_read(self, handle, count=None):
        if not isinstance(handle, int):
            raise TypeError("handle must be int")
        if count is not None and not isinstance(count, int):
            raise TypeError("count must be int")
        message = {
            "execute": "guest-file-read",
            "arguments": {
                "handle": handle
            }
        }
        if count is not None:
            message['count'] = count
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_file_seek(self, handle, offset, whence):
        if not isinstance(handle, int):
            raise TypeError("handle must be int")
        if not isinstance(offset, int):
            raise TypeError("offset must be int")
        if not isinstance(whence, int):
            raise TypeError("whence must be int")
        whence_values = [
            "set",
            "cur",
            "end"
            ]
        message = {
            "execute": "guest-file-seek",
            "arguments": {
                "handle": handle,
                "offset": offset,
                "whence": whence
            }
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_file_write(self, handle, buf_b64, count=None):
        if not isinstance(handle, int):
            raise TypeError("handle must be int")
        if not isinstance(buf_b64, str):
            raise TypeError("buf_b64 must be str")
        if count is not None and not isinstance(count, int):
            raise TypeError("count must be int")
        message = {
            "execute": "guest-file-write",
            "arguments": {
                "handle": handle,
                "buf-b64": buf_b64,
            }
        }
        if count is not None:
            message['count'] = count
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_fsfreeze_freeze(self):
        pass
    def guest_fsfreeze_freeze_list(self):
        pass
    def guest_fsfreeze_status(self):
        pass
    def guest_fsfreeze_thaw(self):
        pass
    def guest_fstrim(self):
        pass
    def guest_get_devices(self):
        message = {
            "execute": "guest-get-devices"
        }
        return self.send(message)

    def guest_get_disks(self):
        message = {
            "execute": "guest-get-disks",
        }
        ret = self.send(message)
        if not isinstance(ret, list):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_get_fsinfo(self):
        message = {
            "execute": "guest-get-fsinfo",
        }
        ret = self.send(message)
        if not isinstance(ret, list):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_get_host_name(self):
        message = {
            "execute": "guest-get-host-name",
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_get_memory_block_info(self):
        pass
    def guest_get_memory_blocks(self):
        pass
    def guest_get_osinfo(self):
        message = {
            "execute": "guest-get-osinfo"
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_get_time(self):
        message = {
            "execute": "guest-get-time"
        }
        ret = self.send(message)
        if not isinstance(ret, int):
            raise Exception("Invalid message from guest: %s" % ret)
        return datetime.fromtimestamp(ret / 1000000000)

    def guest_get_timezone(self):
        message = {
            "execute": "guest-get-timezone"
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_get_users(self):
        message = {
            "execute": "guest-get-users"
        }
        ret = self.send(message)
        if not isinstance(ret, list):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_get_vcpus(self):
        message = {
            "execute": "guest-get-vcpus",
        }
        ret = self.send(message)
        if not isinstance(ret, list):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_info(self):
        message = {
            "execute": "guest-info",
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_network_get_interfaces(self):
        message = {
            "execute": "guest-network-get-interfaces",
        }
        ret = self.send(message)
        if not isinstance(ret, list):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_ping(self):
        message = {
            "execute": "guest-ping"
        }
        out = False
        try:
            ret = self.send(message)
            if not isinstance(ret, dict):
                raise Exception("Invalid message from guest: %s" % ret)
            out = True
        except:
            pass
        return out

    def guest_set_memory_blocks(self):
        pass
    def guest_set_time(self, t):
        if not isinstance(t, datetime):
            raise TypeError("time must be datetime")
        message = {
            "execute": "guest-set-time",
            "arguments": {
                "time": int(t.timestamp() * 1000000000)
            }
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_set_user_password(self, username, password, crypted):
        if not isinstance(username, str):
            raise TypeError("username must be str")
        if not isinstance(password, str):
            raise TypeError("password must be b64 encoded str")
        if not isinstance(crypted, bool):
            raise TypeError("crypted must be bool")
        message = {
            "execute": "guest-set-user-password",
            "arguments": {
                "username": username,
                "password": password,
                "crypted": crypted
            }
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_set_vcpus(self):
        pass
    def guest_shutdown(self):
        message = {
            "execute": "guest-shutdown"
        }
        return self.send(message)

    def guest_ssh_add_authorized_keys(self, username, keys, reset=False):
        if not isinstance(username, str):
            raise TypeError("username must be str")
        if not isinstance(keys, list):
            raise TypeError("keys must be a list of str")
        if not isinstance(reset, bool):
            raise TypeError("reset must be bool")
        message = {
            "execute": "guest-ssh-add-authorized-keys",
            "arguments": {
                "username": username,
                "keys": keys,
                "reset": reset
            }
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_ssh_get_authorized_keys(self, username):
        if not isinstance(username, str):
            raise TypeError("username must be str")
        message = {
            "execute": "guest-ssh-get-authorized-keys",
            "arguments": {
                "username": username
            }
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_ssh_remove_authorized_keys(self, username, keys):
        if not isinstance(username, str):
            raise TypeError("username must be str")
        if not isinstance(keys, list):
            raise TypeError("keys must be a list of str")
        message = {
            "execute": "guest-ssh-remove-authorized-keys",
            "arguments": {
                "username": username,
                "keys": keys
            }
        }
        ret = self.send(message)
        if not isinstance(ret, dict):
            raise Exception("Invalid message from guest: %s" % ret)
        return ret

    def guest_suspend_disk(self):
        pass
    def guest_suspend_hybrid(self):
        pass
    def guest_suspend_ram(self):
        pass
    def guest_sync(self):
        pass
    def guest_sync_delimited(self):
        pass

def flush(s, seconds):
    _c_read, _, _ = select.select([s], [], [], seconds)
    if len(_c_read) > 0:
        _ = _c_read[0].recv(1024)


def get_time_seconds(s):
    flush(s, 1)
    get_time = { "execute": "guest-get-time" }
    s.send((json.dumps(get_time) + '\r\n').encode('ascii'))
    data = s.recv(1024).decode('ascii')
    t = json.loads(data)
    return t.get('return', 0) / 1000000000

def set_time_seconds(s, t):
    flush(s, 1)
    t = time()
    set_time = {
        "execute": "guest-set-time", 
        "arguments": { 
            "time":  int(t * 1000000000)
        }
    }
    s.send((json.dumps(set_time) + '\r\n').encode('ascii'))
    data = s.recv(1024).decode('ascii')
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
