#!bin/sh

DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

id=$(cat ${DIR}/id)
if [ ! -f id ]; then
        echo "Error: missing 'id' file" >&2
        exit 1
fi

PIDFILE=${DIR}/tunnel.pid
config=$(curl -s https://sammcloud.com/tunnel/${id}/config.json)
up=$(    echo ${config} | jq ".up")
port=$(  echo ${config} | jq ".port")
server=$(echo ${config} | jq ".server")
process_running="0"
current_pid=""
if [ -f ${PIDFILE} ]; then
        current_pid=$(cat ${PIDFILE})
        if ps -p ${current_pid} > /dev/null; then
                process_running="1"
        else
                rm ${PIDFILE}
                current_pid=""
        fi
fi

if [ ${up} == "1" ] && [ ${process_running} == "0" ]; then
        ssh -l${user} -N -T -R ${port}:localhost:22 ${server} &
        echo "$!" > /tmp/tunnel.pid
elif [ ${up} == "0" ] && [ ${process_running} == "1" ]; then
        kill ${current_pid}
        rm ${PIDFILE}
fi

