import json
import sys
import os
import logging
from subprocess import Popen, PIPE, TimeoutExpired
import shutil
import pathlib
import time
import select

log = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr)
images_path=os.path.abspath("images")
qemu_path="/opt/homebrew/bin"

class VirtualMachine:
	def __init__(self, name):
		if not isinstance(name, str):
			raise TypeError("name must be str")


		self.name = name
		self.dir = os.path.abspath(name)

		if not os.path.isdir(self.dir):
			raise Exception("VM doesn't exist")

		self.specs_file = os.path.join(self.dir, "specs.json")
		if not os.path.isfile(self.specs_file):
			raise TypeError("specs_file doesn't exist")
		with open(self.specs_file, "r") as f:
			self.specs = json.load(f)

		self.arch = self.specs.get('arch', "qemu-system-aarch64")
		self.qemu_bin = os.path.join(qemu_path, self.arch)
		if not os.path.isfile(self.qemu_bin):
			raise Exception("Invalid arch")

		self.drives = []
		i=0
		for drive in self.specs.get("drives"):
			hd = HardDrive(drive, i, self.name)
			if not hd.exists():
				hd.create()
			self.drives += [ hd ]
			i += 1

		self.nics = []
		i=0
		for nic_spec in self.specs.get("netdev"):
			self.nics += [ Nic(nic_spec, i) ]
			i += 1

		self.metadata = Metadata(self.specs.get("metadata"), self.dir)

	def cleanup(self):
		self.metadata.delete()
		for drive in self.drives:
			drive.delete()

	def data(self):
		qemu_cmd = [self.qemu_bin]
		if self.specs.get('arch') == "qemu-system-aarch64":
			qemu_cmd += [ 
				"-machine", "virt,highmem=on",
				"-accel", "hvf",
				"-cpu", "host",
				"-bios", "QEMU_EFI.fd",
				#"-drive", "file=/opt/homebrew/Cellar/qemu/8.0.3/share/qemu/edk2-aarch64-code.fd,if=pflash,format=raw"
				#"-serial", "chardev:console1"
			]
		elif self.specs.get('arch') == "qemu-system-x86_64":
			qemu_cmd += [ 
				"-machine", "q35",
				#"-device", "isa-serial,chardev=console1",
			]
		qemu_cmd += [
			"-smp", self.specs.get("cpus", "1"),
			"-m", self.specs.get("ram", "1G"),
			"-nodefaults",
		]
		for drive in self.drives:
			qemu_cmd += drive.data()

		for nic in self.nics:
			qemu_cmd += nic.data()

		qemu_cmd += self.metadata.data()

		if "bios" in self.specs and self.specs['bios'] == 'uefi':
			qemu_cmd += [
				#"-pflash", "/opt/homebrew/Cellar/qemu/8.0.3/share/qemu/edk2-x86_64-code.fd",
				"-drive", "file=/opt/homebrew/Cellar/qemu/8.0.3/share/qemu/edk2-x86_64-code.fd,if=pflash,format=raw"
			]

		if "video" not in self.specs:
			qemu_cmd += [
				"-nographic",
				"-vga", "none",
			]
		else:
			qemu_cmd += [
				"-display", "cocoa",
				"-device", self.specs["video"]
			]

		if "cdrom" in self.specs:
			isofile = os.path.abspath(os.path.join(images_path, self.specs['cdrom'].get('iso')))
			if not os.path.isfile(isofile):
				raise TypeError("ISO file doesn't exist.")
			qemu_cmd += [
				"-cdrom", isofile
			]

		qemu_cmd += [
			"-boot", "order=c",
			"-rtc", "base=utc,clock=host",

			# Serial PCI bus virtio-serial-pci is the same as virtio-serial
			"-device", "virtio-serial-pci,max_ports=4",

			"-chardev", "stdio,id=console1",
			"-serial", "chardev:console1",

			"-chardev", f"socket,path={os.path.join(self.dir, self.name)}.agent,server=on,wait=off,id=agent0",
			"-device", "virtserialport,chardev=agent0,name=org.qemu.guest_agent.0",

			"-mon", "chardev=mon0,mode=control,pretty=off",
			"-chardev", f"socket,path={os.path.join(self.dir, self.name)}.monitor,server=on,wait=off,id=mon0",

			"-device", "pcie-root-port,id=pcie.1",
		]
		return qemu_cmd

	def run(self):
		qemu_cmd = self.data()
		log.debug(" ".join(qemu_cmd))
		log.debug(os.getcwd())
		res = Popen(qemu_cmd, stdout=PIPE, stderr=PIPE)
		polling = select.poll()
		polling.register(res.stdout, select.POLLIN)
		polling.register(res.stderr, select.POLLIN)
		registered_pipes = 2
		while registered_pipes > 0:
			outs = polling.poll(1)
			for out, event in outs:
				if out == res.stdout.fileno():
					lines = res.stdout.readlines(1)
				elif out == res.stderr.fileno():
					lines = res.stderr.readlines(1)
				else:
					continue
				for line in lines:
					try:
						print(line.decode('ascii', errors='ignore').rstrip())
					except:
						pass
				if (event & select.POLLHUP) == select.POLLHUP:
					polling.unregister(out)
					registered_pipes -= 1
			if res.poll() is not None:
				break
		res.wait()
		return res.returncode

class HardDrive:
	def __init__(self, spec, index, vm_dir):
		if not isinstance(spec, dict):
			raise TypeError("Parameter spec must be dictionary.")
		baseimage = spec.get("baseimage")
		self.baseimage = None
		if baseimage is not None:
			baseimage = os.path.abspath(os.path.join(images_path, baseimage))
			if os.path.isfile(baseimage):
				self.baseimage = baseimage

		self.size = spec.get("size", "1G")
		self.id = spec.get("file")
		self.bustype = spec.get("bustype", "virtio-blk")
		if self.id is None:
			raise TypeError("file not defined")
		self.file = os.path.abspath(os.path.join(vm_dir, self.id))
		self.index = index

	def exists(self):
		return os.path.isfile(self.file)

	def data(self):
		if not self.exists():
			return []
		drivedata = []
		if self.bustype == 'scsi-hd':
			drivedata += ["-device", "virtio-scsi-pci"]
		if self.bustype == 'ide-hd':
			drivedata += [
				#"-device", "piix3-ide",
				"-drive",  f"file={self.file},if=ide,id={self.id},cache=writeback",
				#"-device", f"{self.bustype},drive={self.id},bootindex={self.index},bus=ide.0"
			]
			return drivedata

		drivedata += [ 
			"-drive",  f"file={self.file},if=none,id={self.id},cache=writeback",
			"-device", f"{self.bustype},drive={self.id},bootindex={self.index}"
		]
		return drivedata

	def create(self):
		cmd = [ "qemu-img", "create", "-f", "qcow2" ]
		if self.baseimage is not None:
			cmd += [ "-b", self.baseimage, "-F", "qcow2" ]
		cmd += [ self.file ]
		if self.size is not None:
			cmd += [ self.size ]
		log.debug("Command: %s", str(cmd))
		res = Popen(cmd, stdout=PIPE, stderr=PIPE)
		res.wait()
		log.debug("Image creation: %s", res.communicate()[0].decode('ascii').rstrip())
		if res.returncode is not None and res.returncode != 0:
			log.error("Error(%s) creating image: %s", 
				res.returncode, res.communicate()[1].decode('ascii').rstrip())
			raise Exception("Unable to create HardDrive")

	def delete(self):
		if os.path.isfile(self.file):
			os.remove(self.file)
			log.debug("Deleted %s", self.file)

class Nic:
	def __init__(self, specs, index):
		if not isinstance(specs, dict):
			raise TypeError("specs must be dictionary")
		self.mac = specs.get("mac")
		self.type = specs.get("type", "vmnet-host")
		self.index = index
		self.sock = specs.get("sock")
		self.id = f"mynet{self.index}"
		self.netdev = self.id
		self.devtype = specs.get("devtype", "e1000")
		self.ifname = specs.get("ifname")

	def get(self, key):
		value = getattr(self, key)
		if value is not None:
			return f"{key}={value}"
		return None

	def param_netdev(self):
		out = []
		out.append(self.type)
		out.append(self.get("id"))
		if self.sock is not None:
			out.append(self.get("sock"))
		if self.type == 'vmnet-bridged':
			out.append(self.get("ifname"))
		return ",".join(out)

	def param_device(self):
		out = []
		out.append(self.devtype)
		out.append(self.get("netdev"))
		out.append(self.get("mac"))
		return ",".join(out)

	def data(self):
		if self.mac is None:
			return []
		return [
			"-netdev", self.param_netdev(),
			"-device", self.param_device()
		]

class Metadata:
	def __init__(self, specs, vm_dir):
		if specs is None:
			self.floppy_path = None
			return
		floppy_file = specs.get("file", "floppy.img")
		self.floppy_dev = None
		self.floppy_path = os.path.join(vm_dir, floppy_file)
		mf = specs.get("meta-data")
		self.metadata_file = None
		if mf is not None:
			mf = os.path.abspath(os.path.join(vm_dir, mf))
			if os.path.isfile(mf):
				self.metadata_file = mf
		uf = specs.get("user-data")
		self.userdata_file = None
		if uf is not None:
			uf = os.path.abspath(os.path.join(vm_dir, uf))
			if os.path.isfile(uf):
				self.userdata_file = uf
		nc = specs.get("network-config")
		self.network_file = None
		if nc is not None:
			nc = os.path.abspath(os.path.join(vm_dir, nc))
			if os.path.isfile(nc):
				self.network_file = nc

	def create(self):
		cmd = ["dd", "if=/dev/zero", f"of={self.floppy_path}", "bs=512", "count=2880" ]
		log.debug(f"Command: %s", str(cmd))
		res = Popen(cmd, stdout=PIPE, stderr=PIPE)
		stdout, stderr = res.communicate(timeout=10)
		log.debug("Creating floppy: %s", stdout.decode('ascii').rstrip())
		if res.returncode is not None and res.returncode != 0:
			raise Exception("Error(%s) creating floppy %s" % 
				(res.returncode, stderr.decode('ascii').rstrip()))

	def attach(self):
		cmd = [ "hdiutil", "attach", "-nomount", self.floppy_path ]
		log.debug("Command: %s", str(cmd))
		res = Popen(cmd, stdout=PIPE, stderr=PIPE)
		stdout, stderr = res.communicate(timeout=10)
		if res.returncode != 0:
			raise Exception(stderr.decode('ascii').rstrip())
		self.floppy_dev = stdout.decode('ascii').rstrip()
		log.debug("Attaching floppy: '%s'", self.floppy_dev)
		if res.returncode is not None and res.returncode != 0:
			raise Exception("Error(%s) attaching floppy '%s'" %
				(res.returncode, stderr.decode('ascii').rstrip()))
		retry=0
		while True:
			if retry == 10:
				raise TimeoutError("Error attaching floppy '%s'." % self.floppy_dev)
			if pathlib.Path(self.floppy_dev).is_block_device():
				break
			retry += 1
			time.sleep(1)

	def format(self):
		cmd = [ "diskutil", "eraseVolume", "MS-DOS", "CIDATA", self.floppy_dev ]
		log.debug("Command: %s", str(cmd))
		res = Popen(cmd, stdout=PIPE, stderr=PIPE)
		stdout, stderr = res.communicate(timeout=10)
		log.debug("Formatting floppy: %s", self.floppy_dev)
		if res.returncode is not None and res.returncode != 0:
			raise Exception("Error(%s) formatting floppy %s" %
				(res.returncode, res.communicate()[1].decode('ascii').rstrip()))


	def mount(self):
		cmd = [ "diskutil", "mount", self.floppy_dev ]
		log.debug("Command: %s", str(cmd))
		res = Popen(cmd, stdout=PIPE, stderr=PIPE)
		stdout, stderr = res.communicate(timeout=10)
		log.debug("Mounting floppy: %s", self.floppy_dev)
		if res.returncode is not None and res.returncode != 0:
			raise Exception("Error(%s) mounting floppy %s" %
				(res.returncode, res.communicate()[1].decode('ascii').rstrip()))

	def copy_files(self):
		if self.metadata_file is not None and os.path.isfile(self.metadata_file):
			shutil.copyfile(self.metadata_file, "/Volumes/CIDATA/meta-data")
			log.debug("Copied %s", self.metadata_file)
		if self.userdata_file is not None and os.path.isfile(self.userdata_file):
			shutil.copyfile(self.userdata_file, "/Volumes/CIDATA/user-data")
			log.debug("Copied %s", self.userdata_file)
		if self.network_file is not None and os.path.isfile(self.network_file):
			shutil.copyfile(self.network_file, "Volumes/CIDATA/network-config")
			log.debug("Copied %s", self.network_file)

	def unmount(self):
		cmd = [ "hdiutil", "detach", self.floppy_dev ]
		log.debug("Command: %s", str(cmd))
		res = Popen(cmd, stdout=PIPE, stderr=PIPE)
		stdout, stderr = res.communicate(timeout=10)
		log.debug("Unounting floppy: %s", self.floppy_dev)
		if res.returncode is not None and res.returncode != 0:
			raise Exception("Error(%s) unmounting floppy %s" %
				(res.returncode, stderr.decode('ascii').rstrip()))
		self.floppy_dev = None

	def delete(self):
		if self.floppy_dev is not None:
			self.unmount()
		if os.path.isfile(self.floppy_path):
			log.debug("Deleting file %s", self.floppy_path)
			os.remove(self.floppy_path)

	def do(self):
		if self.floppy_path is None:
			return
		if os.path.isfile(self.floppy_path):
			return
		try:
			self.create()
			self.attach()
			self.format()
			self.mount()
			self.copy_files()
			self.unmount()
		except:
			self.delete()
			raise

	def data(self):
		if self.floppy_path is None:
			return []
		self.do()
		return [ "-drive", f"file={self.floppy_path},if=virtio,format=raw,media=cdrom" ]

def main(argv):
	if len(argv) < 2:
		log.error("Invalid number of parameters.")
		exit(1)

	log.setLevel("DEBUG")
	vm_name=argv[1]
	if len(argv) > 2 and argv[2] == 'ephemeral':
		ephemeral = True
	else:
		ephemeral = False

	vm = VirtualMachine(vm_name)
	ret = vm.run()
	if ephemeral:
		vm.cleanup()
	sys.exit(ret)

if __name__ == '__main__':
	main(sys.argv)

