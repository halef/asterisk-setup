#!/usr/bin/env bash
set -e # Abort on error

# Locate this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load heler.sh functions
source ${SCRIPT_DIR}/helper.sh

# Set paramaters
# TODO(langep): Make parameters configurable or read from environment
ASTERISK_HOME=/opt/asterisk


if [ "$1" == "--aws" ]; then
    localnet=$(get_aws_vpc_cidr)
    if [ $? -gt 0 ]; then
        fatal "Specified --aws but it seems like we are not running on AWS."
    fi
else
    localnet=$1
fi

if [[ -z $2 ]]; then
    external_host=;
else
    external_host="externhost = $2"
fi

# Replace configuration
rm -rf ${ASTERISK_HOME}/etc/asterisk/*
cp -r ${SCRIPT_DIR}/conf/* ${ASTERISK_HOME}/etc/asterisk/.

sed -i -e "s|%%ASTERISK_HOME%%|${ASTERISK_HOME}|g" ${ASTERISK_HOME}/etc/asterisk/asterisk.conf
sed -i -e "s|%%LOCALNET%%|${localnet}|g" ${ASTERISK_HOME}/etc/asterisk/sip.conf

sed -i -e "s|%%EXTERNHOST%%|${external_host}|g" ${ASTERISK_HOME}/etc/asterisk/sip.conf

chown -R asterisk ${ASTERISK_HOME}

warning "Change default password and peer [1000] password in "
warning "${ASTERISK_HOME}/etc/asterisk/sip.conf."
