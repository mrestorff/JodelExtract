#!/usr/bin/env python2

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
        return str(int(round(delta.days / 365.0, 1))) + " years ago"
    elif ((now - ts) > dt.timedelta(days=30)):
        return str(int(round(delta.days / 30.0, 1))) + " months ago"
    elif ((now - ts) > dt.timedelta(hours=24)):
        return str(delta.days) + " days ago"
    elif ((now - ts) > dt.timedelta(minutes=59)):
        return str(int(round(delta.seconds / 3600.0, 1))) + " hours ago"
    elif ((now - ts) > dt.timedelta(seconds=59)):
        return str(int(round(delta.seconds / 60, 0))) + " minutes ago"
    elif ((now - ts) < dt.timedelta(seconds=59)) and ((now - ts) > dt.timedelta(seconds=1)):
        return str(int(round(delta.seconds, 0))) + " seconds ago"
    else:
        return "less than a second ago"
