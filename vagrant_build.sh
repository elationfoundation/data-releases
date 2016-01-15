#!/usr/bin/env bash
#
# This file is part of data-releases, a listing of public data releases by federal agencies.
# Copyright © 2016 seamus tuohy, <s2e (at) seamustuohy.com>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the included LICENSE file for details.

# Setup

#Bash should terminate in case a command or chain of command finishes with a non-zero exit status.
#Terminate the script in case an uninitialized variable is accessed.
#See: https://github.com/azet/community_bash_style_guide#style-conventions
set -e
set -u

# TODO remove DEBUGGING
set -x

# Read Only variables

#readonly PROG_DIR=$(readlink -m $(dirname $0))
#readonly readonly PROGNAME=$(basename )
#readonly PROGDIR=$(readlink -m $(dirname ))


main() {
    dependencies
    pip_three_install "icalendar"
    pip_three_install "iso8601"
}

dependencies() {
    apt_install "python3"
    apt_install "python3-pip"
}

apt_install(){
    local package="${1}"
    local installed=$(dpkg --get-selections \
                               | grep -v deinstall \
                               | grep -E "^${package}\s+install"\
                               | grep -o "${package}")
    if [[ "${installed}" = ""  ]]; then
        echo "Installing ${package} via apt-get"
        apt-get -y install "${package}"
        echo "Installation of ${package} completed."
    else
        echo "${package} already installed. Skipping...."
    fi
}

pip_three_install(){
    local package="${1}"
    local installed=$(pip3 list \
                             | grep -E "^${package}\s\([0-9\.]*\)$" \
                             | grep -o "${package}")
    if [[ "${installed}" = ""  ]]; then
        echo "Installing ${package} via python pip3"
        sudo -u vagrant sudo pip3 install "${package}"
        echo "Installation of ${package} completed."
    else
        echo "${package} already installed. Skipping...."
    fi
}


cleanup() {
    # put cleanup needs here
    exit 0
}

trap 'cleanup' EXIT


main
