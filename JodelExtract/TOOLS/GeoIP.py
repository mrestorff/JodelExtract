#!/usr/bin/env python2
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

""" This module abstracts the interface to several geoIP services """

import requests

LOCATION_RETRIES = 5
verbose = False


def print_verbose(message):
    if verbose:
        print message


def get_location(service=None):
    """Get the current location from either any or a specified service"""

    if (service is not None):
        services = [service]
    else:
        services = GeoIPServicesType.services

    location = None

    for service in services:
        print_verbose("Trying service " + service.url)
        for _try in range(0, LOCATION_RETRIES):
            try:
                location = service.func()
                if (location is not None):
                    return location
            except RuntimeError as e:
                print_verbose("Connection to service " + service.url + " failed :" + str(e) + "(" + str(_try) + "/" + str(LOCATION_RETRIES) + ")")

    if (location is None):
        print "Could not contact any IP location service."
        print "Returning nonsense location"
        location = {'city': 'None', 'country': 'None', 'loc_accuracy': 1337, 'loc_coordinates': {'lat': 0, 'lng': 0}}

    print location

    return location


def _get_ip_api():
    """Private function to get the location from ip-api.com"""
    try:
        r = requests.get(GeoIPServicesType.ipapi.url)
    except requests.exceptions.ConnectionError:
        raise RuntimeError('Connection failed')

    if (r.status_code == 200):
        j = r.json()
        try:
            # convert ip-api.com's JSON reply format to internal rep
            city = j['city']
            country_code = j['countryCode']
            latitude = j['lat']
            longitude = j['lon']
            return {'city': city, 'country': country_code, 'loc_accuracy': 100, 'loc_coordinates': {'lat': latitude, 'lng': longitude}}
        except KeyError:
            msg = j.get('message')
            if msg is not None:
                print "Request failed: " + msg
            else:
                print "Request failed: Unkown reason"
            raise RuntimeError('Request failed')
    else:
        msg = "Request failed: " + r.status_code
        print msg
        raise RuntimeError(msg)


def _get_nekudo():
    """Private function to get the location from nekudo.com"""
    try:
        r = requests.get(GeoIPServicesType.nekudo.url)
    except requests.exceptions.ConnectionError:
        raise RuntimeError('Connection failed')

    if (r.status_code == 200):
        j = r.json()
        try:
            # convert nekudo's JSON reply format to internal rep
            city = j['city']
            if (city == False):
                raise AttributeError('No city in reply')
            country_code = j['country']['code']
            latitude = j['location']['latitude']
            longitude = j['location']['longitude']
            return {'city': city, 'country': country_code, 'loc_accuracy': 100, 'loc_coordinates': {'lat': latitude, 'lng': longitude}}
        except KeyError as e:
            msg = j.get('message')
            if msg is not None:
                print "Request failed: " + msg
            else:
                print "Request failed: Unkown reason"
            raise RuntimeError('Request failed')
        except AttributeError as e:
            print_verbose(e)
            raise RuntimeError('Request failed')
    else:
        msg = "Request failed: " + r.status_code
        print msg
        raise RuntimeError(msg)


class GeoIPServicesType:

    class GeoIPService:

        def __init__(self, func, url):
            self.func = func
            self.url = url

    ipapi = GeoIPService(_get_ip_api, 'http://ip-api.com/json')       # FIXME doesn't support HTTPS, find other provider...
    nekudo = GeoIPService(_get_nekudo, 'http://geoip.nekudo.com/api/')  # FIXME doesn't support HTTPS, find other provider...
    services = [ipapi, nekudo]
