#!/bin/bash

USER=tunneluser

uid=$(id -u)
if [ "${uid}" != "0" ]; then
	echo "Must be 'root' to install this tool" >&2
	exit 1
fi

if ! id ${USER} 2> /dev/null; then
	echo "User doesn't exist. Can't uninstall"
	exit 0
fi

userdel -r ${USER}
if [ -f /etc/cron.d/samm_tunnel ]; then
	rm /etc/cron.d/samm_tunnel
fi
