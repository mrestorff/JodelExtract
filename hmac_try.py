#!/usr/bin/env python2

# TOOLS - An Open JOdel Client
# Copyright (C) 2016  Christian Fibich
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

""" A script which tests if registration works with the given or
    default HMAC paramters. Exits with 0 if successful or 1 otherwise """

import TOOLS.Connection
import TOOLS.Config
import os
import sys

if __name__ == '__main__':
    hmac_secret = None

    if len(sys.argv) == 5:
        hmac_secret = sys.argv[1]
        user_agent_string = sys.argv[2]
        x_client_type = sys.argv[3]
        x_api_version = sys.argv[4]
        app_config = TOOLS.Config.ConfigType(hmac_secret,None,user_agent_string,x_client_type,x_api_version)
    else:
        print "Using default configuration."
        app_config = None

    id_bytes = os.urandom(32)
    id_bytes_str = ["%02x" % (ord(byte)) for byte in id_bytes]

    conn = TOOLS.Connection.Connection(app_config=app_config,uid=''.join(id_bytes_str))
    rv = conn.register()

    if (rv is False):
        print "Server rejected the request."
        sys.exit(1)
    else:
        print "All fine."
        sys.exit(0)
