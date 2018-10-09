#!/usr/bin/env bash
set -e # Abort on error

# Locate this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set paramaters
# TODO(langep): Make parameters configurable
download_location=/usr/local/src/asterisk
install_location=/opt/asterisk
version=14.7.8
archive=asterisk-${version}.tar.gz
unpacked_dir_name=asterisk-${version}
download_url=https://downloads.asterisk.org/pub/telephony/asterisk/old-releases/$archive


# Cleanup trap in case of error
cleanup() {
    if [ $? -ne 0 ]; then
        # TODO(langep): Conditional cleanup based on where error happend
        rm -rf "$install_location"
    fi
}

trap cleanup EXIT

# Load heler.sh functions
source ${SCRIPT_DIR}/helper.sh

# Check for root user
require_root

# Update packages and install dependencies
apt-get update
apt-get install -y --no-install-recommends wget whois build-essential \
    ncurses-dev uuid-dev libjansson-dev libxml2-dev libsqlite3-dev \
    libssl-dev

# Make download and install directories
mkdir -p "$download_location" "$install_location"

# Download and unpack the source archive
pushd "$download_location"
if [ ! -f "$archive" ]; then # Download if not exists
    wget -O "$archive" "$download_url"
fi
tar -xvf "$archive"

pushd "$unpacked_dir_name"

# Compile and install
./configure --prefix=${install_location}
make -j 4
make install

# Create group and user for asterisk if they don't exist
if ! check_group asterisk; then
    groupadd asterisk
fi

if ! check_user asterisk; then
    useradd -r -s /bin/false -g asterisk asterisk
fi

cp ${SCRIPT_DIR}/init.d/asterisk.init-debian /etc/init.d/asterisk
chmod +x /etc/init.d/asterisk
sed -i -e "s|%%ASTERISK_HOME%%|${install_location}|g" /etc/init.d/asterisk
update-rc.d asterisk defaults

chown -R asterisk $install_location

echo "export ASTERISK_HOME=${install_location}" >> /etc/bash.bashrc

info "Installation complete."
info "Run 'source /etc/bash.bashrc'"
info "Then run '${SCRIPT_DIR}/update-conf.sh [--aws]' next."

