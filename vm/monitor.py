import asyncio
from qemu.qmp import QMPClient
import os
import sys

async def main(vmname, *args):
	qmp = QMPClient(vmname)
	sockfile = os.path.join(vmname, f"{vmname}.monitor")
	if not os.path.exists(sockfile):
		raise TypeError(f"Socket file {sockfile} doesn't exist")
	await qmp.connect(sockfile)

	if len(args) < 1:
		raise TypeError("Missing command")

	if args[0] == "query-status":
		await query_status(qmp)

async def query_status(qmp):
	res = await qmp.execute('query-status')
	print(f"VM status: {res['status']}")

	await qmp.disconnect()

if __name__ == "__main__":
	if len(sys.argv) < 2 or not os.path.isdir(sys.argv[1]):
		raise TypeError("Invalid VM.")
	print(sys.argv)
	asyncio.run(main(*sys.argv[1:]))
