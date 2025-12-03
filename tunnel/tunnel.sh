#!/bin/bash

set -e

DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SSHCONTROL=${DIR}/ssh-control

id=$(cat ${DIR}/id)
if [ ! -f id ]; then
        echo "Error: missing 'id' file" >&2
        exit 1
fi

set +e
config=$(curl -f -s https://sammcloud.com/tunnel/${id}/config.json)
if [ "$?" != "0" ]; then
        echo "Configuration not found in the cloud." >&2
        exit 1
fi
set -e
up=$(    echo ${config} | jq -r ".up")
port=$(  echo ${config} | jq -r ".port")
server=$(echo ${config} | jq -r ".server")
user=$(  echo ${config} | jq -r ".user")

if [ "${up}" == "1" ] && [ ! -f ${SSHCONTROL} ]; then
        set +e
        ssh -l${user} -q -f -N -T -o StrictHostKeyChecking=no \
                -o UserKnownHostsFile=/dev/null \
                -o ControlMaster=yes \
                -S ${SSHCONTROL} \
                -R ${port}:localhost:22 ${server}
        if [ "$?" != "0" ]; then
                echo "Unable to start ssh tunnel" >&2
                exit 1
        fi
        set -e
elif [ "${up}" == "0" ] && [ -f ${SSHCONTROL}]; then
        ssh -S ${SSHCONTROL} -O close ${server}
fi

