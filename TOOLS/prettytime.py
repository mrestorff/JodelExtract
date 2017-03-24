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

import datetime as dt
import dateutil.parser


def pretty(timestamp):
    try:
        ts = dateutil.parser.parse(timestamp)
    except Exception as e:
        print "Invalid timestamp"
        raise e

    now = dt.datetime.now(tz=ts.tzinfo)

    delta = now - ts

    if ((now - ts) > dt.timedelta(days=30 * 12)):
        return str(round(delta.days / 365.0, 1)) + "Y"
    elif ((now - ts) > dt.timedelta(days=30)):
        return str(round(delta.days / 30.0, 1)) + "M"
    elif ((now - ts) > dt.timedelta(hours=24)):
        return str(delta.days) + "d"
    elif ((now - ts) > dt.timedelta(minutes=59)):
        return str(round(delta.seconds / 3600.0, 1)) + "h"
    elif ((now - ts) > dt.timedelta(seconds=59)):
        return str(round(delta.seconds / 60.0, 1)) + "m"
    else:
        return str(delta.seconds) + "s"
