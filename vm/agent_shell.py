#!/usr/bin/python3
import base64
import agent
import time
import logging
import sys
import os
import shlex

log = logging.getLogger("agent_shell")
logging.basicConfig(stream=sys.stderr)

def agent_execute(agent_path):
	with agent.QemuAgent(agent_path) as q:
		log.debug("Connected")
		while True:
			command = input(">")
			if command == "exit":
				break
			cmd = shlex.split(command)
			if len(cmd) == 0:
				continue
			log.debug(f"command={cmd}")
			try:
				pid = q.guest_exec(cmd[0], arg=cmd[1:], capture_output=True).get('pid')
			except Exception as e:
				print(e)
				continue
			if pid is None:
				return
			while True:
				ret = q.guest_exec_status(pid)
				encoded_ret = ret.get('out-data')
				status = ret.get('exitcode')
				text_ret = base64
				log.debug(f"(status: {status}, Exited: {ret.get('exited')})")
				if encoded_ret is not None:
					print(base64.b64decode(encoded_ret).decode('ascii', errors='ignore'))
				if ret.get('exited'):
					break
				time.sleep(1)

if __name__ == "__main__":
	if os.getenv('AGENT_DEBUG') == '1':
		log.setLevel('DEBUG')
	if len(sys.argv) > 1:
		agent_execute(sys.argv[1])
