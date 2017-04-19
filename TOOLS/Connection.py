# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Jodel Server connection methods by Malte Restorff             #
# Original by Christian Fibich                                  #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
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

"""
TOOLS/Connection.py
Main connection class and helper constants and types
"""

import os
import sys
import re
import base64
import urllib
import json
import hmac
import hashlib
import datetime as dt
import enum
import keyring
import requests
import warnings
import functools
import webbrowser
import TOOLS.Config
import TOOLS.GeoIP
import TOOLS.Config as cfg
import main

CFG_DIR = ".jodel"
CFG_FILE = "jodel.cfg"
API_URL_BASE = 'api.go-tellm.com'
API_URL = 'https://' + API_URL_BASE + '/api/'
CAPTCHA_BASE_URL = 'https://s3-eu-west-1.amazonaws.com/jodel-image-captcha/'

RGEO_URL = 'https://nominatim.openstreetmap.org/search'
LOCATION_RETRIES = 5

# see https://wiki.python.org/moin/PythonDecoratorLibrary#Generating_Deprecation_Warnings
# see http://code.activestate.com/recipes/391367-deprecated/
def deprecated(func):
    """ This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used. """

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.warn("Call to deprecated function {}.".format(func.__name__),
                  category=Warning, stacklevel=2)
        return func(*args, **kwargs)
    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func


class APIMethodsType:
    """ This class hold the parameters of the different API methods. """

    class APIMethod:
        """
        This inner class is the 'type' of a single API method with the
        following parameters

            method   A HTTP method
            url      An URL path, which is appended to the API base URL
            expect   The HTTP code to expect, omit if 200 is OK
            noauth   Do not include an 'AUTHORIZATION BEARER' header in the request, omit of it should be included
            postfix  The postfix to apply after the Post ID

            payload  A flag, set to True if Connection._api_request() for
                     this method expects a variable reference which contents
                     it shall include as JSON payload into the request.
                     If this flag is set to True, Connection._api_request()
                     expects the variable reference specified by the keyword argument payload=<reference>
            postid   A flag, set to True if Connection._api_request() for
                     this method expects a post ID to include into the request URL.
                     If this flag is set to True, Connection._api_request()
                     expects the post ID specified by the keyword argument postid=<reference>
            country  A flag, set to True if Connection._api_request() for
                     this method expects a country ID to include into the request URL.
                     If this flag is set to True, Connection._api_request()
                     expects the country ID specified by the keyword argument country=<reference>
        """

        def __init__(self, method, url, payload=None, expect=200, postid=None,country=None, postfix=None, noauth=None, get_parameters=None, version='v2'):
            self.method = method
            self.url = url
            self.payload = payload
            self.expect = expect
            self.postid = postid
            self.country = country
            self.postfix = postfix
            self.noauth = noauth
            self.get_parameters = get_parameters
            self.version = version
            self.parameters = {'payload': self.payload,'postid': self.postid,'country': self.country,'get_parameters': self.get_parameters}

        def getParameter(self, name):
            return self.parameters.get(name)

        def getParameters(self):
            return self.parameters

    set_position          = APIMethod(method='PUT', url='users/location', payload=True, expect=204)
    register              = APIMethod(method='POST', url='users/', payload=True, noauth=True)
    get_karma             = APIMethod(method='GET', url='users/karma/')
    get_config            = APIMethod(method='GET', url='user/config/', version='v3')
    get_posts             = APIMethod(method='GET', url='posts/location/', get_parameters=True)
    get_combo             = APIMethod(method='GET', url='posts/location/combo/',version='v3',get_parameters=True)
    get_popular           = APIMethod(method='GET', url='posts/location/popular/', get_parameters=True) #new
    get_discussed         = APIMethod(method='GET', url='posts/location/discussed/', get_parameters=True) #new
    get_images            = APIMethod(method='GET', url='pictures/location', version='v3', get_parameters=True) #new
    get_popular_images    = APIMethod(method='GET', url='pictures/location/popular', version='v3', get_parameters=True) #new
    get_discussed_images  = APIMethod(method='GET', url='pictures/location/discussed', version='v3', get_parameters=True) #new
    get_country_posts     = APIMethod(method='GET', url='feed/country/', country=True)
    get_post              = APIMethod(method='GET', url='posts/', postid=True)
    get_post_details      = APIMethod(method='GET', url='posts/', postid=True, version='v3', postfix='details') #new
    share                 = APIMethod(method='POST', url='posts/', postid=True, version='v3', postfix='share/') #new
    get_my_posts          = APIMethod(method='GET', url='posts/mine/')
    get_my_replies        = APIMethod(method='GET', url='posts/mine/replies/')
    get_my_votes          = APIMethod(method='GET', url='posts/mine/votes/')
    get_my_combo          = APIMethod(method='GET', url='posts/mine/combo/')
    get_my_popular        = APIMethod(method='GET', url='posts/mine/popular/')
    get_my_discussed      = APIMethod(method='GET', url='posts/mine/discussed/')
    delete_post           = APIMethod(method='DELETE', url='posts/', postid=True, expect=204)
    upvote                = APIMethod(method='PUT', url='posts/', postid=True, postfix='upvote/')
    pin                   = APIMethod(method='PUT', url='posts/', postid=True, postfix='pin/')
    downvote              = APIMethod(method='PUT', url='posts/', postid=True, postfix='downvote/')
    unpin                 = APIMethod(method='PUT', url='posts/', postid=True, postfix='unpin/')
    new_post              = APIMethod(method='POST', url='posts/', payload=True)
    get_channel           = APIMethod(method='GET', url='posts/channel/combo',get_parameters=True,version='v3')
    get_channel_discussed = APIMethod(method='GET', url='posts/channel/discussed',get_parameters=True,version='v3',) #new
    get_channel_recent    = APIMethod(method='GET', url='posts/channel',get_parameters=True,version='v3') #new
    get_channel_popular   = APIMethod(method='GET', url='posts/channel/popular',get_parameters=True,version='v3') #new
    follow_channel        = APIMethod(method='PUT', url='user/followChannel',get_parameters=True,version='v3',expect=204)
    unfollow_channel      = APIMethod(method='PUT', url='user/unfollowChannel',get_parameters=True,version='v3',expect=204)
    get_pinned            = APIMethod(method='GET', url='posts/mine/pinned/')
    recommended_chnls     = APIMethod(method='GET', url='user/recommendedChannels', version='v3')
    get_user_config       = APIMethod(method='GET', url='user/config', version='v3')
    get_captcha           = APIMethod(method='GET', url='user/verification/imageCaptcha', version='v3')
    post_captcha          = APIMethod(method='POST', url='user/verification/imageCaptcha', version='v3')
    get_hashtag_combo     = APIMethod(method='GET', url='posts/hashtag/combo', get_parameters=True, version='v3')
    get_hashtag_recent    = APIMethod(method='GET', url='posts/hashtag', get_parameters=True, version='v3')
    get_hashtag_popular   = APIMethod(method='GET', url='posts/hashtag/popular', get_parameters=True, version='v3')
    get_hashtag_discussed = APIMethod(method='GET', url='posts/hashtag/discussed', get_parameters=True, version='v3')

class PostType(enum.Enum):
    """Enumeration describing the post filter.
    ALL       are the most recent posts
    POPULAR   speaks for itself
    DISCUSSED speaks for itself
    COMBO     is a combination of the most recent and popular posts
    COUNTRY   just here to be orthogonal with the requests supported by
              the API
    """
    ALL = 1
    POPULAR = 2
    DISCUSSED = 3
    COMBO = 4
    COUNTRY = 5


class Connection(object):
    """
    This class manages the connection to the Jodel/Tellm REST API.
    It also manages the unique client ID, which is randomly generated, and stored
    in the file ~/.jodel/jodel.cfg.
    Since the API employs HMAC, Connection.py appends the required
    headers to each message. Apparently, this is, up to now, only required
    when registering a new client ID.
    """
    verbose = False
    SSL_VERIFY = True

    def print_verbose(self, message):
        """Prints only if the verbose property is set"""
        #if self.verbose:
        if cfg.CONNECTION_VERBOSE:
            print message

    def __init__(self, location=None, citycc=None, uid=None, app_version=None, app_config=None):
        """
        Location may be supplied as a dict required by the location-requiring methods:
            {'city':city, 'country':cc, 'loc_accuracy':100, 'loc_coordinates': {'lat':lat, 'lng':lon}}
            citycc is the selected city name and its cc separated by a comma,as in: citycc="Oulu,FI"
        Use uid to supply an own unique ID to use for this connection.
        """
        if app_version is None:
            app_version = TOOLS.Config.APP_VERSION

        # The app config holds the user agent string, and the parameters for HMAC
        self.app_config = app_config

        try:
            if app_config is None:
                self.app_config = TOOLS.Config.APP_CONFIG[app_version]
        except KeyError:
            raise KeyError('No config for this app version present.')

        self.session = requests.Session()
        self.imgsession = requests.Session()
        self.session.headers['User-Agent'] = self.app_config.user_agent

        # The device_uid is calcuated from the Android ID, IMEI, Telephone number, Social Security number and whatnot
        # Since it is a SHA256 Hash we may just generate a 32 byte number
        # randomly
        if uid is None:
            self.device_uid = _get_uid()
        else:
            self.device_uid = uid

        self.print_verbose("Using device UID " + self.device_uid)

        # priorities: supplied location, supplied city, cc, location from IP
        self.location = location

        if self.location is None and citycc is not None:
            self.print_verbose("Getting location from citycc...")
            self.location = self._location_from_citycc(citycc)

        if self.location is None:
            self.location = TOOLS.GeoIP.get_location()
            self.print_verbose("No location specified. Using GeoIP")

        self.location['name'] = self.location['city']

        # get config from API
        self.jodel_config = self.get_config()

        if self.jodel_config is False:
            raise ValueError("Could not get config from API")

        self.print_verbose("\n User Config from API: "+str(self.jodel_config)+"\n")

        # Captcha Verification [not working]
        # TODO: Activate Captcha Verification
        #if self.jodel_config['verified'] is False:
        #    print "Captcha verification necessary."
        #    self.verify_captcha()
        #else:
        #    print "Account is verified."

        pos = self.set_position()

        if pos is None or pos is False:
            raise ValueError("Connection Failed")

    def verify_captcha(self):
        captcha  = self.get_captcha()
        prompt = 'Open\n\n\t'+captcha['image_url']+'\n\nin a browser and enter the images of the racoons (left to right, starting with 0) separated with spaces.'
        possible_solution = None

        # first try filename matching
        rv = re.match('.*/(.*).png', captcha['image_url'])
        if (rv):
            captchakey = rv.groups(1)[0]
            possible_solution_entry = TOOLS.Config.CAPTCHA_DICT.get(captchakey)
            if possible_solution_entry is not None:
                reply = self.post_captcha(captcha['key'],possible_solution_entry['solution'])
                if reply['verified'] is True:
                    print "Captcha found in name table"
                    return
                else:
                    print "Name matching verification failed"
        # then try matching the image using MD5 sum
        captcha_reply = requests.get(captcha['image_url'])
        if (captcha_reply.ok):
            md = hashlib.md5()
            md.update(captcha_reply.content)
            for key in TOOLS.Config.CAPTCHA_DICT:
                possible_solution_entry = TOOLS.Config.CAPTCHA_DICT[key]
                if possible_solution_entry['md5'] == md.hexdigest():
                    reply = self.post_captcha(captcha['key'],possible_solution_entry['solution'])
                    if reply['verified'] is True:
                        print "Captcha found in MD5 table."
                        return
                    else:
                        print "MD5 matching verification failed"
                        break

        print "Captcha not found in TOOLS.Config.CAPTCHA_DICT. Please solve and update."
        ok = False

        while ok is not True:
            # FIXME: Introduce captcha function with UI after choosing location
            webbrowser.open(captcha['image_url'], new=2)
            rv = raw_input(prompt+'\n> ')
            try:
               solution = [int(i,10) for i in rv.split(' ')]
               ok = True
            except ValueError as e:
               print "Invalid input, try again"

        reply = self.post_captcha(captcha['key'],solution)

        if reply['verified'] is False:
            raise ValueError("Could not Verify")

    def _location_from_citycc(self, citycc):
        """
        Parse supplied City, Countrycode combination in the form of "Hamburg, DE"
        and fetch it's physical coordinates from a reverse geo lookup service.
        """
        try:
            city, cc = citycc.split(",")
        except ValueError as valueError:
            print "City and CC not correctly specified: '" + citycc + "': " + str(valueError)
            return None

        for _try in range(0, LOCATION_RETRIES):
            try:
                r = requests.get(RGEO_URL + '?' + urllib.urlencode({'format': 'json', 'city': city, 'countrycodes': cc}))
            except requests.exceptions.ConnectionError as connectionError:
                print "Connection failed (" + str(_try) + "/" + str(LOCATION_RETRIES) + "): " + str(connectionError)
                continue
            if r.ok:
                j = r.json()
                if len(j) == 0:
                    print "Location search returned nothing."
                    return None
                    break
                elif len(j) > 1:
                    self.print_verbose("Location search returned more results than expected. Choosing first...")
                try:
                    # use ip-api.com's JSON reply format
                    lat = j[0]['lat']
                    lon = j[0]['lon']
                    self.print_verbose("Location chosen: "+j[0]['display_name']+". Coordinates: lat "+lat+" / long "+lon+"\n")
                    return {'city': city.lstrip(),'country': cc.lstrip(),'loc_accuracy': 0,'loc_coordinates': {'lat': lat,'lng': lon}}
                except KeyError:
                    msg = j.get('message')
                    if msg is not None:
                        print "Request failed: " + msg + " (" + str(_try) + "/" + str(LOCATION_RETRIES) + ")"
                    else:
                        print "Request failed: Unkown reason (" + str(_try) + "/" + str(LOCATION_RETRIES) + ")"
            else:
                print "Request failed! " + r.status_code + " (" + str(_try) + "/" + str(LOCATION_RETRIES) + ")"
        return None

    def get_location_string(self):
        return self.location['city'] + ', ' + self.location['country']

    def get_location_city(self):
        return self.location['city']

    def _get_access_token_dict(self):
        """
        Retrieve a valid access token and its parameters (token_type and
        expriation_date are used later on. First, the configuration file
        is checked, a new one is requested from the API if no file is
        present or the token in the file is expired.
        An access token is needed for Bearer Authorization.
        It is sent with every request but the POST request to API_URL/users/

        cfg is a dict holding the access token and its parameters:
        # 'access_token'    : the token code itself
        # 'expiration_date' : the UNIX timestamp with which the token expires
        # 'token_tyoe'      : the kind of authorization to use the token with
        """

        cfg = None
        home_path = os.path.expanduser('~')
        cfg_dir_path = os.path.join(home_path, CFG_DIR)
        cfg_path = os.path.join(home_path, CFG_DIR, CFG_FILE)
        if os.path.exists(cfg_path) and os.path.isfile(cfg_path):
            with open(cfg_path, 'r') as f:
                cfg = json.load(f)
                try:
                    ts = dt.datetime.fromtimestamp(cfg['expiration_date'])
                    now = dt.datetime.now()
                    if (ts - now) > dt.timedelta(days=1):
                        self.print_verbose("Token valid until: " + str(ts))
                        return cfg
                except ValueError as valueError:
                    print valueError
                except KeyError as keyError:
                    print keyError
                except TypeError as typeError:
                    print typeError
        else:
            print "No configuration file found..."

        if not os.path.exists(cfg_dir_path):
            try:
                os.mkdir(cfg_dir_path)
            except OSError as osError:
                print "Cannot create cfg directory " + cfg_dir_path + ": " + str(osError)

        if cfg is None:
            # register and get token
            cfg = self.register()
            # create file
        else:
            # update file
            cfg = self.register()

        if cfg is False:
            print "Registering failed"
            sys.exit(-1)
        elif cfg.get('access_token') is None:
            print "Still could not register"
            sys.exit(-1)

        # update cfg file
        try:
            with open(cfg_path, 'w') as f:
                json.dump(cfg, f)
        except IOError as ioerror:
            print "Updating " + cfg_path + " failed: " + str(ioerror)
            print "Record this data for yourself:" + str(cfg)

        return cfg

    def _authorize(self):
        """ Adds or updates the authorization header of the session """
        access_token_dict = self._get_access_token_dict()
        try:
            self.session.headers['Authorization'] = access_token_dict['token_type'] + ' ' + access_token_dict['access_token']
        except TypeError as typeError:
            print "Could not get access token: " + str(access_token_dict) + ": " + str(typeError)
            return False
        except KeyError as keyError:
            print "Could not get access token: " + str(access_token_dict) + ": " + str(keyError)
            return False
        return True

    def set_position(self, location=None):
        """
        Set the poster's location in the REST API

        location: The location to change to. If this is not specified, the location
        property of the Connection object is used.
        """

        if location is None:
            location = self.location

        self.print_verbose("Setting position to " + str(location) + "\n")
        request_data = {'location': location}
        return self._api_request(TOOLS.Connection.APIMethodsType.set_position,payload=request_data)

    def register(self, location=None):
        """
        Register the Connection object's client uid with the REST API.
        This API method is a POST request and expects an access token dict
        as payload of the response.
        """
        if location is None:
            location = self.location
        request_data = {'client_id': self.app_config.client_id,'device_uid': self.device_uid,'location': self.location}
        self.print_verbose("register")
        register_data = self._api_request(TOOLS.Connection.APIMethodsType.register,payload=request_data)
        self.print_verbose(register_data)
        return register_data

    def karma(self):
        """ Retrieve the client uid's karma value from the REST API """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_karma)

    def my_posts(self):
        # TODO: update list on my_posts() return parameters
        """
        Retrieve a list of the client uid's posts.
        The list is embedded in a dict as follows:

        {posts:[list of posts],some_other_key:value, ...}

        One post is defined by a dict and contains the following relevant fields:

        'post_id'       : A unique hex string denoting this post
        'image_url'     : Present, if this post contains an image
        'message'       : This post's payload. Depending on the app version, contains more or less meaningless data when 'image_url' is present.
        'image_headers' : The headers necessary to retrieve this iamge
        'children'      : List of post dicts describing answers to this post.
        'num_children'  : The number of posts in the children list.
        'creator'       : 'own' if this is a post created by this client_uid,'friend' else
        'votes'         : The number of upvotes this post accumulated
        Children (Answers)
        '': ???
        """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_my_posts)

    def get_config(self):
        """ Retrieves this client_uid's config """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_config)

    def my_combo_posts(self):
        """ Retrieves this client_uid's mixed posts, returned as dict in the same form as by my_posts()"""
        return self._api_request(TOOLS.Connection.APIMethodsType.get_my_combo)

    def my_popular_posts(self):
        """ Retrieves this client_uid's most upvoted posts, returned as dict in the same form as by my_posts()"""
        return self._api_request(TOOLS.Connection.APIMethodsType.get_my_popular)

    def my_discussed_posts(self):
        """ Retrieves this client_uid's most replied posts, returned as dict in the same form as by my_posts()"""
        return self._api_request(TOOLS.Connection.APIMethodsType.get_my_discussed)

    def my_replies(self):
        """ Retrieves this client_uid's replies to posts, returned as dict in the same form as by my_posts()"""
        return self._api_request(TOOLS.Connection.APIMethodsType.get_my_replies)

    def my_voted_posts(self):
        """ Retrieves the posts this client_uid voted on, returned as dict in the same form as by my_posts()"""
        return self._api_request(TOOLS.Connection.APIMethodsType.get_my_votes)

    def get_captcha(self):
        """ Retrieves image to be Captcha'd for account verification """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_captcha)

    def post_captcha(self,key,answer):
        """ Sends Captcha response for account verification """
        return self._api_request(TOOLS.Connection.APIMethodsType.post_captcha,payload={'key':key, 'answer':answer})

    def my_pinned_posts(self):
        """ Retrieves the posts this client_uid pinned, returned as dict in the same form as by my_posts()"""
        return self._api_request(TOOLS.Connection.APIMethodsType.get_pinned)

    # MAIN FEED METHODS #
    def combo_posts(self):
        """
        Retrieves a combination of this location's most recent and most upvoted posts, returned as dict:
        {'posts': [{'recent': ...}, {'discussed': ...}, {'popular': ...}]}
        """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_combo,get_parameters={'lat': self.location['loc_coordinates']['lat'], 'lng': self.location['loc_coordinates']['lng'], 'stickies':'false'})

    def recent_posts(self, after_post_id): #new
        """
        Retrieves the most recent posts after post_id xyz, returned as dict in the same form as by my_posts().
        If 'after' is a post_id, the posts after that post will be displayed.
        """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_posts,get_parameters={'after': after_post_id, 'lat': self.location['loc_coordinates']['lat'], 'lng': self.location['loc_coordinates']['lng'], 'home':'false'})

    def popular_posts(self, after_post_id): #new
        """ Retrieves this location's most upvoted posts, returned as dict in the same form as by my_posts() """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_popular,get_parameters={'after': after_post_id, 'lat': self.location['loc_coordinates']['lat'], 'lng': self.location['loc_coordinates']['lng'], 'home':'false'})

    def discussed_posts(self, after_post_id): #new
        """ Retrieves this location's most commented posts, returned as dict in the same form as by my_posts() """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_discussed,get_parameters={'after': after_post_id, 'lat': self.location['loc_coordinates']['lat'], 'lng': self.location['loc_coordinates']['lng'], 'home':'false'})

    # IMAGE FEED METHODS #
    def recent_images(self, after_post_id): #new
        """ Retrieves the most recent images after post_id xyz, returned as dict in the same form as by my_posts()"""
        return self._api_request(TOOLS.Connection.APIMethodsType.get_images, get_parameters={'after': after_post_id, 'limit': None, 'home':'false'})

    def popular_images(self, after_post_id): #new
        """ Retrieves the most popular images after post_id xyz, returned as dict in the same form as by my_posts()"""
        return self._api_request(TOOLS.Connection.APIMethodsType.get_popular_images, get_parameters={'after': after_post_id, 'limit': None, 'home':'false'})

    def discussed_images(self, after_post_id): #new
        """ Retrieves the most discussed images after post_id xyz, returned as dict in the same form as by my_posts()"""
        return self._api_request(TOOLS.Connection.APIMethodsType.get_discussed_images, get_parameters={'after': after_post_id, 'limit': None, 'home':'false'})

    # CHANNEL METHODS #
    def get_channel(self, channel, after_post_id): #new
        """ Retrieves posts containing a given hashtag """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_channel,get_parameters={'channel': channel, 'after': after_post_id})

    def get_channel_popular(self, channel, after_post_id): #new
        """ Retrieves popular posts containing a given hashtag """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_channel_popular,get_parameters={'channel': channel, 'after': after_post_id})

    def get_channel_discussed(self, channel, after_post_id): #new
        """ Retrieves discussed posts containing a given hashtag """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_channel_discussed,get_parameters={'channel': channel, 'after': after_post_id})

    def get_channel_recent(self, channel, after_post_id): #new
        """ Retrieves recent posts containing a given hashtag """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_channel_recent,get_parameters={'channel': channel, 'after': after_post_id})

    def follow_channel(self,channel):
        """ Follows a given hashtag """
        return self._api_request(TOOLS.Connection.APIMethodsType.follow_channel,get_parameters={'channel': channel})

    def unfollow_channel(self,channel):
        """ Unfollows a given hashtag """
        return self._api_request(TOOLS.Connection.APIMethodsType.unfollow_channel,get_parameters={'channel': channel})

    def get_hashtag(self, hashtag, after_post_id):
        """ Calls the API Method getRecentHashtagPosts """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_hashtag, get_parameters={'hashtag': hashtag, 'after': after_post_id})

    def get_hashtag_combo(self, hashtag):
        """ Retrives a combo for the given hashtag """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_hashtag_combo, get_parameters={'hashtag': hashtag})

    def get_hashtag_popular(self, hashtag, after_post_id):
        """ Retrives the popular posts for the given hashtag """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_hashtag_popular, get_parameters={'hashtag': hashtag, 'after': after_post_id})

    def get_hashtag_discussed(self, hashtag, after_post_id):
        """ Retrives the discussed posts for the given hashtag """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_hashtag_discussed, get_parameters={'hashtag': hashtag, 'after': after_post_id})

    def get_hashtag_recent(self, hashtag, after_post_id):
        """ Retrives the recent posts for the given hashtag """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_hashtag_recent, get_parameters={'hashtag': hashtag, 'after': after_post_id})

    def get_user_config(self):
        """ Retrieves user's configuration """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_user_config)

    def country_feed(self):
        """ Retrieves this location's countries posts. Just here for orthogonality. """
        # NOTE: check if this works => doesn't work with these parameters
        return self._api_request(TOOLS.Connection.APIMethodsType.get_country_posts,country=self.location['country'])

    def delete_post(self, postid):
        """ Try to delete the post with the given post id """
        return self._api_request(TOOLS.Connection.APIMethodsType.delete_post,postid=postid)

    def particular_post(self, postid):
        """ Retrieves a single post and its replies, returned as dict in the same form as by my_posts() """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_post,postid=postid)

    def particular_post_details(self, postid, reply=None, details='true', reversed='false'): #new
        """
        Retrieves a single post and a maximum of 50 replies, returned as dict in the form:
        {
            "next": unix_timestamp_in_milliseconds,
            "remaining": remaining_comments_currently_not_shown,
            "readonly": boolean {True, False},
            "shareable": boolean {True, False},
            "replies": [{reply1_here_see_my_posts()_for_format}, {reply2,...}],
            "details": {post_details_see_my_posts()_for_format}
        }
        'next':         is a Unix timestamp (milliseconds), used for the 'reply' parameter in this function
        'remaining':    the remaining replies that are currently not shown (get them via 'reply')
        """
        return self._api_request(TOOLS.Connection.APIMethodsType.get_post_details, postid=postid, get_parameters={'details': details, 'reply': reply, 'reversed': reversed})

    def share(self, postid): # TODO: Implement share function in GUI
        """ Share the post with the given postid """
        return self._api_request(OJOC.Connection.APIMethodsType.share, postid=postid)

    def upvote(self, postid):
        """ Upvote the post with the given postid """
        return self._api_request(TOOLS.Connection.APIMethodsType.upvote,postid=postid)

    def pin(self, postid):
        """ Pin the post with the given postid """
        return self._api_request(TOOLS.Connection.APIMethodsType.pin,postid=postid)

    def downvote(self, postid):
        """ Downvote the post with the given postid """
        return self._api_request(TOOLS.Connection.APIMethodsType.downvote,postid=postid)

    def unpin(self, postid):
        """ Unpin the post with the given postid """
        return self._api_request(TOOLS.Connection.APIMethodsType.unpin,postid=postid)

    def recommended_channels(self):
        """ Retrieves channels recommended for the user """
        return self._api_request(TOOLS.Connection.APIMethodsType.recommended_chnls)

    def new_post(self,message,color='DD5F5F',image_data=None,ancestor=None,name=None):
        """ Post a new post to the API.
            message:    The message text to post
            color:      Hex color of the post. Only some colors are accepted by the API, the others are converted
                        to a random color:
                        Allowed are: '06A3CB', '8ABDB0', '9EC41C', 'DD5F5F', 'FF9908', 'FFBA00'
            image_data: Binary data of an image (JPEG) to post. This data will be base64 encoded and included in
                        the post request
            ancestor:   Post ID of a post to which the new post is a reply
            name:       Name to be used while posting. Apparently, only geographic names near the coordinates included
                        in the request are accepted.
        """
        if not self._authorize():
            print "Authorization error."
            return None

        location = self.location
        if name != '':
            location['name'] = name
        else:
            location['name'] = location['city']

        request_data = {'color': color,'location': location,'message': message}
        if ancestor is not None:
            request_data['ancestor'] = ancestor

        if image_data is not None:
            request_data['image'] = base64.b64encode(image_data)

        return self._api_request(TOOLS.Connection.APIMethodsType.new_post,payload=request_data)

    def _api_request(self, action, **kwargs):
        """ Perform a request to the REST API.
            The action is a dict from the APIMethodsType Class.
            The kwargs need to contain the parameters required by that
            method. """

        if action is None:
            return None

        params = {}

        for parameter_name in action.getParameters().keys():
            arg = kwargs.get(parameter_name)
            # if the argument is not contained in the parameter list
            # set to default from the class
            if arg is None:
                params[parameter_name] = action.getParameter(parameter_name)
                if params[parameter_name] is True:
                    raise Exception('Expected parameter '+parameter_name)
            else:
                params[parameter_name] = arg

        url = API_URL + action.version + '/'+ action.url

        if action.postid is not None:
            url += params['postid'] + '/'

        if action.country is not None:
            url += params['country'] + '/'

        postfix = action.postfix
        if postfix is not None:
            url += postfix

        self.print_verbose("Trying request to " + url)

        self.print_verbose("Get params: "+str(params['get_parameters']))

        if action.noauth:
            req = requests.Request(action.method, url, headers={'Authorization': None}, json=params['payload'])
        else:
            if not self._authorize():
                print "Authorization error."
                return None
            req = requests.Request(action.method, url, json=params['payload'], params=params['get_parameters'])

        try:
            prep_req = self.session.prepare_request(req)
            prep_req.headers = _sign_request(prep_req,self.app_config)

            rep = self.session.send(prep_req,verify=self.SSL_VERIFY)

            if rep.status_code == action.expect:
                self.print_verbose("Request to " + url + " successful (" + str(rep.status_code) + ")")
                if rep.status_code == 204:
                    return True
                try:
                    return rep.json()
                except ValueError as valueError:
                    print str(valueError) + ': ' + url
                    return None
            else:
                print "Request to " + url + " failed:"
                print "Status code: " + str(rep.status_code)
                print "Text: " + rep.text
                return False
        except requests.exceptions.ConnectionError as connectionError:
            print "Sending request failed: " + str(connectionError)
            return False


def _get_uid():
    """
    Trys to get the device_uid from the system's keyring.
    If this fails, generates a new one and stores it in the keyring.
    This is not optimal for headless systems...
    """

    device_uid = keyring.get_password("jodel", "device_uid")
    if device_uid is None:
        try:
            # device UID is a SHA256 hash
            # generate a random one here
            print "Generating new device_uid"
            id_bytes = os.urandom(32)
            id_bytes_str = ["%02x" % (ord(byte)) for byte in id_bytes]
            device_uid = ''.join(id_bytes_str)
            keyring.set_password("jodel", "device_uid", device_uid)
        except NotImplementedError as e:
            print "Keyring is not implemented: " + str(e)
            # Fail if there is no keyring
            sys.exit(1)
    return device_uid


def _sign_request(prep_req,app_config):
    """ Performs HMAC signing of a prepared request object. """

    # Requesting the first access token must now be done with a HMAC signed request
    #
    # Signing works as follows:
    #
    # 1. Retrieve a _secret_ for HMAC
    #    This is done by using an opaque C++ library in the original
    #    Android app. The app's signature hash is fed into the
    #    library and a secret falls out.
    #
    # 2. Stringify the request. this is done using the following scheme:
    #
    #    <METHOD>%<URL-BASE>%<PORT>%<PATH-with-trailing-slash>%<BEARER-token-if-exists>%<T-Z-UTC-timestamp>%<LIST-of-GET-keys-and-vals-separated-by-percent>%<REQUEST-DATA>
    #
    # 3. Calculate the HMAC-SHA1 digest of the stringified request
    #
    # 4. Add the headers 'X-Client-Type', 'X-Api-Version' and 'X-Authorization'
    #    'X-Authorization' has the value 'HMAC <uppercase hex representation of HMAC digest>'
    #
    # 5. Send the request with the headers

    # Collect the parameters over which to calculate the HMAC
    headers = prep_req.headers
    body = prep_req.body
    url = prep_req.url
    method = prep_req.method

    timestamp = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    authheader = headers.get('Authorization')
    if authheader is not None:
        auth = (authheader.split(" "))[1]
    else:
        auth = ""

    parameter_start = url.find('?')
    if parameter_start == -1:
        parameters = ""
        path_end = len(url)
    else:
        parameters = re.sub('[&=]', '%', url[parameter_start + 1:])
        path_end = parameter_start

    # do black signing magic -- HMAC
    # 7 -> "https://"

    path_start = url.find('/', 8)

    if path_start == -1 or path_start == path_end:
        path = ""
    else:
        path = url[path_start:path_end]

    if body is None:
        body = ""

    # Construct the base for the HMAC hash: A percent-sign separated string containing the
    # paramters
    message = method.upper() + "%" + API_URL_BASE + "%" + str(TOOLS.Config.PORT) + \
        "%" + path + "%" + auth + "%" + timestamp + "%" + parameters + "%" + body
    dig = hmac.new(app_config.hmac_secret,msg=message,digestmod=hashlib.sha1)

    # Append the headers
    headers['X-Client-Type'] = app_config.x_client_type
    headers['X-Api-Version'] = app_config.x_api_version
    headers['X-Timestamp'] = timestamp
    headers['X-Authorization'] = 'HMAC ' + str(dig.hexdigest()).upper()

    return headers
