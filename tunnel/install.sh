#!/bin/bash

INSTALL_PATH=/opt/samm_tunnel
USER=tunneluser

uid=$(id -u)
if [ "${uid}" != "0" ]; then
	echo "Must be 'root' to install this tool" >&2
	exit 1
fi

if [ -d ${INSTALL_PATH} ]; then
	exit 0
fi

mkdir -p ${INSTALL_PATH}
if ! id ${USER} 2> /dev/null then
	useradd --home-dir ${INSTALL_PATH} --create-home --shell /sbin/nologin ${USER}
	sudo -u ${USER} ssh-keygen -t rsa -b 2048 -q -f ${INSTALL_PATH}/.ssh/id_rsa -N ""
	sudo -u ${USER} uuidgen > ${INSTALL_PATH}/id
fi
uid=$(sudo -u ${USER} id -u)
gid=$(sudo -u ${USER} id -g)
cp tunnel.sh ${INSTALL_PATH}
chown ${uid} ${INSTALL_PATH}/tunnel.sh
chgrp ${gid} ${INSTALL_PATH}/tunnel.sh
chmod +x ${INSTALL_PATH}/tunnel.sh

if [ -f /etc/cron.d/samm_tunnel ]; then
	exit 0
fi
cat <<EOF > /etc/cron.d/samm_tunnel
PATH=/usr/lib/sysstat:/usr/sbin:/usr/sbin:/usr/bin:/sbin:/bin
*/5 * * * * ${USER} ${INSTALL_PATH}/tunnel.sh
EOF