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
    localnet=$(get_aws_internal_ip)
    if [ $? -gt 0 ]; then
        fatal "Specified --aws but it seems like we are not running on AWS."
    fi
fi

# Replace configuration
rm -rf ${ASTERISK_HOME}/etc/asterisk/*
cp -r ${SCRIPT_DIR}/config/* ${ASTERISK_HOME}/etc/asterisk/.

# TODO(langep): Replacements here.
sed -i -e "s|%%ASTERISK_HOME%%|${ASTERISK_HOME}|g" ${ASTERISK_HOME}/etc/asterisk/asterisk.conf
sed -i -e "s|%%LOCALNET%%|${localnet}|g" ${ASTERISK_HOME}/etc/asterisk/sip.conf

# TODO(langep): Modify this for external asterisk server
sed -i -e "s|%%EXTERNHOST%%|;|g" ${ASTERISK_HOME}/etc/asterisk/sip.conf

chown -R asterisk ${ASTERISK_HOME}

warn "Change default password and peer [1000] password in "
warn "${ASTERISK_HOME}/etc/asterisk/sip.conf."
