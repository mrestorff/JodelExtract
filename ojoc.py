#!/usr/bin/env python2
# encoding=utf8

# OJOC - An Open JOdel Client
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

"""This is the main executable file for the OJOC GTK GUI"""


import json
import tempfile
from StringIO import StringIO
import array
import os
import shutil
import pprint
import argparse
import sys
import enum
import gi
import appdirs
import time
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import WebKit
from PIL import Image

import OJOC.Connection
import OJOC.gui

import requests

# Enable utf8
reload(sys)
sys.setdefaultencoding('utf8')

CAT_API_URL = "http://thecatapi.com/api/images/get"
DBG_DIALOG = False

APP_NAME = "OJOC"
APP_AUTHOR = "cfib90"

def timesort(post):
    """Returns post's post ID as an int for sorting (roughly time-dependent)"""
    return int(post['post_id'], 16)

class post_category_type(enum.Enum):
    """Enumerate the types of page container widgets """
    MY_POSTS     = 1
    VOTED_POSTS  = 3
    MY_REPLIES   = 5
    POSTS        = 7
    CHANNEL      = 9
    PINNED_POSTS = 11

post_category_titles = {post_category_type.MY_POSTS:     'My Posts',
                        post_category_type.VOTED_POSTS:  'My Voted Posts',
                        post_category_type.PINNED_POSTS: 'My Pinned Posts',
                        post_category_type.MY_REPLIES:   'My Replies',
                        post_category_type.POSTS:        'Posts'}

menu_entry_titles={OJOC.Connection.PostType.POPULAR: 'Popular',
                   OJOC.Connection.PostType.DISCUSSED: 'Discussed',
                   OJOC.Connection.PostType.COMBO:'Combo'}

class OjocWindow(Gtk.Window):
    """ The main window class """

    def __init__(self, recent_posts=None):
        Gtk.Window.__init__(self, title=APP_NAME)
        self.set_wmclass(APP_NAME,APP_NAME)
        try:
            self.tempdir = appdirs.user_cache_dir(APP_NAME,APP_AUTHOR)
            if not os.path.exists(self.tempdir):
                os.makedirs(self.tempdir)
            print self.tempdir
        except Exception as e:
            print "Cannot create tempdir: "+str(e)
            return False

        iconpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images', 'icon.png')

        self.set_icon_from_file(iconpath)

        self.set_border_width(3)
        self.set_default_size(650, 960)
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.add(self.notebook)

        # dictionary of dynamically generated notebook pages
        self.notebook_pages_dict = {}
        # map post_category <=> page container widget
        self.page_container_widget_dict = {}
        # dictionary for tuples of function and parameter list to refresh each tab
        self.reload_function_dict = {}
        # map post_category_type <=> tab number
        self.tab_num_dict = {}
        self.posts_mode_dict = {}
        self.my_posts_notebook_page = None

        for post_category in post_category_type:
            self.posts_mode_dict[post_category] = OJOC.Connection.PostType.COMBO

        # contains all ancestors of currently open posts
        self.ancestors = {}

        # Only generate the Debug Dialog if the global flag is set
        if DBG_DIALOG:
            self.debugDialog = OJOC.gui.DebugWindow(self, self)
        else:
            self.debugDialog = None
        self.my_posts_mode = OJOC.Connection.PostType.COMBO
        self.posts_mode = OJOC.Connection.PostType.COMBO

        # Set up the GTK header bar for karma and 'new post/reply' buttons
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(True)
        headerbar.props.title = "OJOC"
        reload_button = Gtk.Button.new_from_icon_name('view-refresh', 1)
        reload_button.connect('clicked', self.reload, None)
        post_button = Gtk.Button.new_from_icon_name('list-add', 1)
        post_button.connect('clicked', self.new_post, None)
        channel_button = Gtk.Button()
        channel_button.set_image(Gtk.Image.new_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images', 'channel.png')))
        channel_button.connect('clicked', self.new_channel, None)
        location_button = Gtk.Button()
        location_button.set_image(Gtk.Image.new_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images', 'location.png')))
        location_button.connect('clicked', self.change_location, None)
        karma_button = Gtk.Button.new_from_icon_name('emblem-favorite', 1)
        karma_button.connect('clicked', self.view_karma, None)
        self.connect('key_press_event', self._key_pressed, None)
        headerbar.pack_end(location_button)
        headerbar.pack_end(channel_button)
        headerbar.pack_end(post_button)
        headerbar.pack_end(reload_button)
        headerbar.pack_start(karma_button)
        self.set_titlebar(headerbar)

        # Set up loading splash screen
        loadpath = os.path.join(self.tempdir, 'loading.jpg')
        try:
            # Download an image from thecatapi.com
            with open(loadpath, 'wb') as handle:
                reply = requests.request('GET', CAT_API_URL, params={'format': 'src', 'type': 'jpg', 'size': 'small'})
                if not reply.ok:
                    print "Could not get image."
                for block in reply.iter_content(1024):
                    handle.write(block)
            try:
                # Display it on a featureless dialog
                self.loading = OJOC.gui.ImageViewer(self,GdkPixbuf.Pixbuf.new_from_file(loadpath),top_text="Loading...",bottom_text="Cat pic by thecatapi.com")
                self.loading.show_all()
            except:
                print "Could not display loading image."
        except:
            print "Could not load loading image."

    def clean_tempdir(self,max_age=7*86400):
        try:
            files_in_temp = os.listdir(self.tempdir)
            for f in files_in_temp:
                real_path = os.path.join(self.tempdir,f)
                try:
                    if os.path.isfile(real_path) and (time.time() - os.stat(real_path).st_atime > max_age):
                        os.remove(real_path)
                except Exception as e:
                    print "Could not delete file: "+str(e)
        except Exception as e:
            print "Could not clean temp dir: "+str(e)

    def initialize(self, citycc=None, location=None, initial_channels=None):
        """Set up the connection to Jodel, load the content of the
           default tabs
           citycc  A location in City, CC format as in "Vienna, AT"
           """

        # make a new connection object
        self.connection = OJOC.Connection.Connection(location=location,citycc=citycc)
        if self.connection is None:
            print "Could not connect to server"
            self.destroy()
            return None
        self.set_title("OJOC: " + self.connection.get_location_string())

        if initial_channels is None:
            recommended_channels = self.connection.recommended_channels()
            if recommended_channels is not False:
                initial_channels = [channel['channel'] for channel in recommended_channels['recommended']]
            else:
                initial_channels = []

        # construct all the tabs
        self.posts()
        self.my_posts()
        self.my_replies()
        self.my_voted_posts()
        self.my_pinned_posts()
        for initial_channel in initial_channels:
            self._open_channel(self,initial_channel)
        self.notebook.set_current_page(self.tab_num_dict[post_category_type.POSTS])
        try:
            # Kill the loading dialog if it's there
            self.loading.destroy()
        except AttributeError as e:
            print str(e)
        self.show_all()
        return False

    def reload(self, widget, data):
        """Reloads the data in the currently raised notebook page, which is
           referred to by its numerical index given to it by the Notebook widget.

           widget and data are parameters required for callbacks but are
           ignored"""
        reload_function = self.reload_function_dict[self.notebook.get_current_page()]

        if reload_function is not None:
            reload_function[0](*reload_function[1])
        self.clean_tempdir()

    def change_location (self, widget, data):
        """ Method to change the location request, and forward the
            request to the API when editing is finished.

            data is a paramete required for callbacks but is ignored"""

        location_dialog = Gtk.MessageDialog(parent=None, flags=0, type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.OK, message_format="Location:")

        action_area = location_dialog.get_content_area()
        location    = None

        map_view = WebKit.WebView()
        lat = str(self.connection.location['loc_coordinates']['lat'])
        lng = str(self.connection.location['loc_coordinates']['lng'])
        html = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.0.2/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.0.2/dist/leaflet.js"></script>
</head>
<body>
<style>
    #map { width: 640px; height: 480px; }
</style>
<div id="map"></div>

<script type="text/javascript">
var map = L.map('map').setView(["""+lat+", "+lng+"""], 13);

L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

var marker = L.marker(["""+lat+", "+lng+"""]);
document.title = 

marker.addTo(map).openPopup();

function onMapClick(e) {
    marker.setLatLng(e.latlng);
}

function reverse_geo() {
   var xmlHttp = new XMLHttpRequest();
   var url = 'https://nominatim.openstreetmap.org/reverse?format=json&lat='+marker.getLatLng().lat+'&lon='+marker.getLatLng().lng;
   xmlHttp.open("GET",url,false);
   xmlHttp.send()
   document.title = xmlHttp.responseText;
}

map.on('click',onMapClick);

</script>
</body>
</html>
        """

        map_view.load_string(html,"text/html","UTF-8","/")
        action_area.add(map_view)

        location_dialog.show_all()
        rv = location_dialog.run()
        if rv == Gtk.ResponseType.OK:
            map_view.execute_script('reverse_geo()')
            loc = map_view.get_title()
            try:
               loc = json.loads(loc)
               cc   = loc['address']['country_code'].upper()
               city    = loc['address'].get('city')
               if city is None:
                  city = loc['address'].get('town')
               if city is None:
                  city = loc['address'].get('village')

               lat  = loc['lat']
               lon  = loc['lon']

               location = {'city':city, 'country':cc, 'loc_accuracy':100, 'loc_coordinates': {'lat':lat, 'lng':lon}}
            except ValueError as e:
               print "Cannot parse location "+str(loc)

        location_dialog.destroy()
        if location is not None:
            self.initialize(location=location)

    def new_channel (self, widget, data):
        """ Method to set up a channel request, and forward the
            request to the API when editing is finished.

            data is a paramete required for callbacks but is ignored"""

        channel_dialog = Gtk.MessageDialog(parent=None, flags=0, type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.OK, message_format="Channel: #")

        action_area = channel_dialog.get_content_area()

        channel_entry = Gtk.Entry()
        action_area.add(channel_entry)

        channel_dialog.show_all()
        rv = channel_dialog.run()
        if rv == Gtk.ResponseType.OK:
            channel = channel_entry.get_text()
            if channel != '':
                self._open_channel(self,channel)
        channel_dialog.destroy()

    def new_post(self, widget, data):
        """ Method to set up a post editing dialog, and forward the
            request to the API when editing is finished.

            data is a parameter required for callbacks but is ignored"""
        parent = None
        color = None
        current_notebook_page = self.notebook.get_current_page()
        # Check if this is a new post or a reply to an opened post.
        # This is done by checking the currently opened notebook page number
        # against a dict holding a cross-reference between post IDs and
        # page numbers
        if current_notebook_page != self.tab_num_dict[post_category_type.POSTS] and current_notebook_page != self.tab_num_dict[post_category_type.MY_POSTS]:
            for page_id in self.notebook_pages_dict.keys():
                if self.notebook.page_num(self.notebook_pages_dict[page_id]) == current_notebook_page:
                    try:
                        parent_post_widget = self.ancestors[page_id]
                        color = parent_post_widget.colorspec
                        parent = page_id
                    except KeyError:
                        return
                    break

        # Open a new post editing dialog
        dialog = OJOC.gui.PostEditor(self, color)
        dialog_response = dialog.run()
        post_data_dict = None
        if dialog_response == 1:
            # Send the post to the API if user clicked OK
            post = dialog.get_post()
            error_message = post.get('error')
            if error_message is not None:
                print str(error_message)
            else:
                post_data_dict = self.connection.new_post(post['message'],color=post['color'],image_data=post['image_data'],ancestor=parent,name=post['name'])
                if self.debugDialog is not None:
                    self.debugDialog.update('=== New Post ===\n' + pprint.pformat(post_data_dict) + '\n')

        dialog.destroy()
        if post_data_dict is None:
            return
        else:
            self.reload(widget, post_data_dict)

    def view_karma(self, widget, data):
        """ This method opens a dialog which shows the user's current karma.
            The karma value is fetched from the API

           widget and data are parameters required for callbacks but are
           ignored"""
        reply = self.connection.karma()

        if self.debugDialog is not None:
            self.debugDialog.update('=== Karma ===\n' + pprint.pformat(reply) + '\n')
        if reply is not None:
            dialog = Gtk.MessageDialog(self,Gtk.DialogFlags.DESTROY_WITH_PARENT,Gtk.MessageType.INFO,Gtk.ButtonsType.CLOSE,'Karma: ' + str(reply['karma']))
            dialog.run()
            dialog.destroy()

# ----------------------------------------------------------------------
# Methods for updating notebook tabs with posts
# ----------------------------------------------------------------------

    def posts(self, post_data_dict=None, mode=None):
        """ Construct a notebook page containing posts by others
            sorted or filtered by the current mode

            post_data_dict  Initial data for the tab (do not fetch from API)
            mode  Data fetching mode (e.g. popular mode) from OJOC.Connection.PostType
        """

        if mode is None:
            mode = self.posts_mode_dict[post_category_type.POSTS]

        # Fetch posts from the API if no data is supplied
        if post_data_dict is None:
            if mode == OJOC.Connection.PostType.POPULAR:
                post_data_dict = self.connection.popular_posts()
            elif mode == OJOC.Connection.PostType.DISCUSSED:
                post_data_dict = self.connection.discussed_posts()
            elif mode == OJOC.Connection.PostType.COMBO:
                raw_post_data_dict = self.connection.combo_posts()
                post_data_dict = {'posts': sorted(raw_post_data_dict['replied'] +
                        raw_post_data_dict['voted'] +
                        raw_post_data_dict['recent'],key=timesort,reverse=True)}
            else:
                post_data_dict = self.connection.get_combo()

        if post_data_dict is False:
            message_dialog = Gtk.MessageDialog(parent=self,text="Error!",secondary_text="Could not get data",message_type=Gtk.MessageType.ERROR,buttons=Gtk.ButtonsType.OK)
            message_dialog.run()
            message_dialog.destroy()

        self.post_data_dict = post_data_dict

        if self.debugDialog is not None:
            self.debugDialog.update('=== Posts ===\n' + pprint.pformat(post_data_dict) + '\n')

        # get page widget
        page_container_widget, tab_number = self._new_tab_container((self.posts,[None]),
                                                                    post_category=post_category_type.POSTS,
                                                                    menu_entries=[OJOC.Connection.PostType.COMBO,
                                                                                  OJOC.Connection.PostType.POPULAR,
                                                                                  OJOC.Connection.PostType.DISCUSSED])


        notebook_page = self._get_clear_notebook_page_grid(page_container_widget)

        if post_data_dict:
            try:
                for post in post_data_dict['posts']:
                    notebook_page.add(OJOC.gui.Post(self.tempdir,post,self,self.connection,callback=self._open_post))
            except:
                print post_data_dict
        page_container_widget.add(notebook_page)
        page_container_widget.show_all()

    def my_replies(self, post_data_dict=None):
        """ Construct a notebook page containing the posts replied to by
            the user's device_uid

            post_data_dict  Initial data for the tab (do not fetch from API)
        """

        # Fetch posts from the API if no data is supplied
        if post_data_dict is None:
            post_data_dict = self.connection.my_replies()

        # Display error dialog if data could not be loaded from the API
        if post_data_dict is False:
            error_dialog = Gtk.MessageDialog(parent=self,text="Error!",secondary_text="Could not get data",message_type=Gtk.MessageType.ERROR,buttons=Gtk.ButtonsType.OK)
            error_dialog.run()
            error_dialog.destroy()

        self.post_data_dict = post_data_dict
        if self.debugDialog is not None:
            self.debugDialog.update('=== My Replies ===\n' + pprint.pformat(post_data_dict) + '\n')

        # get page widget
        page_container_widget, tab_number = self._new_tab_container(post_category=post_category_type.MY_REPLIES, reload_function=(self.my_replies,[None]))

        self.my_replies_notebook_page = notebook_page = self._get_clear_notebook_page_grid(page_container_widget)

        if post_data_dict:
            for post in post_data_dict['posts']:
                notebook_page.add(OJOC.gui.Post(self.tempdir,post,self,self.connection,callback=self._open_post))

        notebook_page.show_all()
        page_container_widget.add(notebook_page)

    def my_posts(self, post_data_dict=None, mode=None):
        """ Construct a notebook page containing the posts posted by
            the user's device_uid

            post_data_dict  Initial data for the tab (do not fetch from API)
            mode  Data fetching mode (e.g. popular mode) from OJOC.Connection.PostType
        """
        if mode is None:
            mode = self.posts_mode_dict[post_category_type.MY_POSTS]

        # Fetch posts from the API if no data is supplied
        if post_data_dict is None:
            if mode is OJOC.Connection.PostType.POPULAR:
                post_data_dict = self.connection.my_popular_posts()
            elif mode is OJOC.Connection.PostType.DISCUSSED:
                post_data_dict = self.connection.my_discussed_posts()
            else:
                post_data_dict = self.connection.my_posts()

        if post_data_dict is False:
            message_dialog = Gtk.MessageDialog(parent=self,text="Error!",secondary_text="Could not get data",message_type=Gtk.MessageType.ERROR,buttons=Gtk.ButtonsType.OK)
            message_dialog.run()
            message_dialog.destroy()

        self.post_data_dict = post_data_dict
        if self.debugDialog is not None:
            self.debugDialog.update('=== My Posts ===\n' + pprint.pformat(post_data_dict) + '\n')

        # get page widget
        page_container_widget, tab_number = self._new_tab_container(post_category=post_category_type.MY_POSTS,
                                                                    menu_entries=[OJOC.Connection.PostType.COMBO,
                                                                                  OJOC.Connection.PostType.POPULAR,
                                                                                  OJOC.Connection.PostType.DISCUSSED],
                                                                    reload_function=(self.my_posts,[None]))

        self.my_posts_notebook_page = notebook_page = self._get_clear_notebook_page_grid(page_container_widget)

        # diplay new posts
        if post_data_dict:
            for post in post_data_dict['posts']:
                notebook_page.add(OJOC.gui.Post(self.tempdir,post,self,self.connection,callback=self._open_post))

        notebook_page.show_all()
        page_container_widget.add(notebook_page)

    def my_voted_posts(self, post_data_dict=None):
        """ Construct a notebook page containing the posts voted on by
            the user's device_uid

            post_data_dict  Initial data for the tab (do not fetch from API)
        """

        # Fetch posts from the API if no data is supplied
        if post_data_dict is None:
            post_data_dict = self.connection.my_voted_posts()

        if not post_data_dict:
            message_dialog = Gtk.MessageDialog(parent=self,text="Error!",secondary_text="Could not get data",message_type=Gtk.MessageType.ERROR,buttons=Gtk.ButtonsType.OK)
            message_dialog.run()
            message_dialog.destroy()

        self.post_data_dict = post_data_dict
        if self.debugDialog is not None:
            self.debugDialog.update('=== My Voted Posts ===\n' +
                pprint.pformat(post_data_dict) +
                '\n')

        page_container_widget, tab_number = self._new_tab_container((self.my_voted_posts,[None]),post_category=post_category_type.VOTED_POSTS)
        notebook_page = self._get_clear_notebook_page_grid(page_container_widget)

        if post_data_dict:
            for post in post_data_dict['posts']:
                notebook_page.add(OJOC.gui.Post(self.tempdir,post,self,self.connection,callback=self._open_post))

        notebook_page.show_all()
        page_container_widget.add(notebook_page)

    def my_pinned_posts(self, post_data_dict=None):
        """ Construct a notebook page containing the posts pinned by
            the user's device_uid

            post_data_dict  Initial data for the tab (do not fetch from API)
        """

        # Fetch posts from the API if no data is supplied
        if post_data_dict is None:
            post_data_dict = self.connection.my_pinned_posts()

        if not post_data_dict:
            message_dialog = Gtk.MessageDialog(parent=self,text="Error!",secondary_text="Could not get data",message_type=Gtk.MessageType.ERROR,buttons=Gtk.ButtonsType.OK)
            message_dialog.run()
            message_dialog.destroy()

        self.post_data_dict = post_data_dict
        if self.debugDialog is not None:
            self.debugDialog.update('=== My Pinned Posts ===\n' +
                pprint.pformat(post_data_dict) +
                '\n')

        page_container_widget, tab_number = self._new_tab_container((self.my_pinned_posts,[None]),post_category=post_category_type.PINNED_POSTS)
        notebook_page = self._get_clear_notebook_page_grid(page_container_widget)

        if post_data_dict:
            for post in post_data_dict['posts']:
                notebook_page.add(OJOC.gui.Post(self.tempdir,post,self,self.connection,callback=self._open_post))

        notebook_page.show_all()
        page_container_widget.add(notebook_page)

    def _open_channel(self, widget, channel):
        """ Construct a new notebook page for the given channel (hashtag)"""

        # Fetch posts from the API
        channel_data_dict = self.connection.get_channel(channel)

        if channel_data_dict is False:
            return

        if self.debugDialog is not None:
            self.debugDialog.update('=== Channel ===\n' + pprint.pformat(channel_data_dict) + '\n')

        old_page = self.notebook_pages_dict.get('#'+channel)
        if old_page is not None:
            old_page_index = self.notebook.page_num(old_page)
            if old_page_index != -1:
                self.notebook.remove_page(old_page_index)

        try:
            head = unicode(channel,errors='replace')
        except TypeError:
            head = channel

        page_container_widget, tab_number = self._new_tab_container((self._open_channel,[widget,channel]),
                                                                    text='#'+head,
                                                                    menu_entries=[OJOC.Connection.PostType.COMBO,
                                                                                  OJOC.Connection.PostType.POPULAR,
                                                                                  OJOC.Connection.PostType.DISCUSSED],
                                                                    closable=True)

        notebook_page = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL)
        notebook_page.set_row_spacing(3)
        notebook_page.set_border_width(5)

        self.notebook_pages_dict['#'+channel] = page_container_widget

        # Check if this channel has posts, and list them if yes
        channel_posts_list = channel_data_dict.get('recent')
        if channel_posts_list is not None and len(channel_posts_list) > 0:
            for post in channel_posts_list:
                    notebook_page.add(OJOC.gui.Post(self.tempdir,post,self,self.connection,callback=self._open_post))

        page_container_widget.add(notebook_page)
        page_container_widget.show_all()
        self.notebook.set_current_page(tab_number)

        return True

    def _open_post(self, widget, post_id):
        """ Construct a new notebook page for the post with the given
            post ID """

        # Fetch posts from the API
        this_post = post = self.connection.particular_post(post_id)
        if this_post is False:
            # We need this code because it is possible to open an
            # own post and then delete it.
            #
            # Here we check if the reloaded post still exists, and when
            # it does not, display an error message and return to
            # all posts.
            dialog = Gtk.MessageDialog(self,Gtk.DialogFlags.DESTROY_WITH_PARENT,Gtk.MessageType.ERROR,Gtk.ButtonsType.CLOSE,'Post could not be loaded\nReturning to All Posts')
            dialog.run()
            dialog.destroy()
            self.notebook.set_current_page(self.recent_posts_tab_num)
            tab_number = self.notebook_pages_dict.get(post_id)
            if tab_number is not None:
                self._close_tab(widget, tab_number)
            self.reload(None, None)
            return True

        if self.debugDialog is not None:
            self.debugDialog.update('=== Particular Post ===\n' + pprint.pformat(this_post) + '\n')

        # get post & answers
        if this_post is None:
            print "Could not fetch " + post_id
            for post in self.post_data_dict['posts']:
                if post['post_id'] == post_id:
                    this_post = post
                    break
        if this_post is None:
            return False

        old_page = self.notebook_pages_dict.get(this_post['post_id'])
        if old_page is not None:
            old_page_index = self.notebook.page_num(old_page)
            if old_page_index != -1:
                self.notebook.remove_page(old_page_index)

        # generate post object for original post
        self.ancestors[this_post['post_id']] = orig = OJOC.gui.Post(self.tempdir, this_post, self, self.connection)

        # extract data we need for user numbering
        user_handle = post.get('user_handle')
        userlist = None
        if user_handle is not None:
            # OP gets id 0
            userlist = {post['user_handle']: 0}

        # generate scrollable container with padding etc. and tab header
        page_container_widget, tab_number = self._new_tab_container((self._open_post,[widget,post_id]),text=this_post['message'],color=orig.color,closable=True)
        self.notebook_pages_dict[this_post['post_id']] = page_container_widget

        # generate notebook page content container grid
        notebook_page = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL)
        notebook_page.set_row_spacing(3)
        notebook_page.set_border_width(5)
        notebook_page.add(orig)

        # Check if this post has replies, and list them if yes
        children_posts_list = this_post.get('children')
        # Counts the number of responses, counts even when one poster posts multiple times
        response_index = 0
        if children_posts_list is not None and len(children_posts_list) > 0:
            for reply in children_posts_list:
                # Sometimes, the API supplies us with user numbers to
                # view who posted which answer
                response_index += 1
                user_handle = reply.get('user_handle')
                user_index = None
                if (user_handle is not None) and (userlist is not None):
                    if user_handle not in userlist:
                        userlist[user_handle] = response_index
                    user_index = userlist[user_handle]
                notebook_page.add(OJOC.gui.Post(self.tempdir,reply,self,self.connection,userno=user_index,ispost=False))

        page_container_widget.add(notebook_page)
        page_container_widget.show_all()
        self.notebook.set_current_page(tab_number)

        print str(self.notebook_pages_dict[this_post['post_id']])
        return True

# ----------------------------------------------------------------------
# Tab creation utility functions
# ----------------------------------------------------------------------

    def _get_clear_notebook_page_grid(self,page_container_widget):
        """ Remove all entries in the container widget and add a new empty grid """
        # remove all entries in this page & their container
        page_container_widget.foreach(lambda widget, data: page_container_widget.remove(widget), None)
        notebook_page = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL)
        notebook_page.set_row_spacing(3)
        notebook_page.set_border_width(5)
        return notebook_page

    def _new_tab_container(self,reload_function,post_category=None,text=None,menu_entries=None,color=None,closable=False):
        """ Generate a new tab with the given parameters and the required reload function """

        if post_category is None and text is None:
            return None

        page_container_widget = None
        menu_event_box = None

        if post_category is not None:
            page_container_widget = self.page_container_widget_dict.get(post_category)
            title = post_category_titles[post_category]

        if page_container_widget is None:
            page_container_widget = Gtk.ScrolledWindow()
            page_container_widget.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            w = page_container_widget.get_min_content_width()
            page_container_widget.set_min_content_width(w + 10)
            page_container_widget.set_margin_top(5)
            page_container_widget.set_margin_bottom(5)
            page_container_widget.set_margin_left(5)
            page_container_widget.set_margin_right(5)

            # generate the title text
            if text is not None:
                if (len(text) > 10):
                    title = text[:10] + '...'
                else:
                    title = text

            # generate a label holding the title
            head_label = Gtk.Label(title)
            if color is not None:
                head_label.modify_bg(Gtk.StateType.NORMAL, color)

            if menu_entries is not None:
                # generate a post type context menu for the label

                menu_event_box = Gtk.EventBox.new()

                head_label.show()
                menu_event_box.add(head_label)

                # Construct the context menu for switching the post type
                # The post_types dict contains the different options for
                # which to generate radio buttons
                # This dict is iterated and the list of radio buttons generated

                menugroup = None
                menu = Gtk.Menu.new()
                button_index = 0

                for button_type in menu_entries:
                    btn = Gtk.RadioMenuItem.new_with_label(menugroup, menu_entry_titles[button_type])
                    if menugroup is None:
                        menugroup = btn.get_group()
                    btn.connect('activate', self._handle_menu,button_type,post_category,page_container_widget)
                    menu.attach(btn, 0, 3, button_index, button_index + 1)
                    button_index += 1

                menugroup[0].set_active(True)

                menu_event_box.connect('button-press-event',self._handle_popup, menu)
                title_widget = menu_event_box
            else:
                # just use the plain label
                title_widget = head_label

            # If the tab shall be closable, generate a close button
            if closable:
                header_widget = Gtk.Grid()
                header_close = Gtk.Button.new_from_icon_name('window-close', 1)
                header_close.connect('clicked', self._close_tab, page_container_widget)
                header_widget.attach(title_widget, 0, 0, 1, 1)
                header_widget.attach_next_to(header_close, title_widget, Gtk.PositionType.RIGHT, 1, 1)
            else:
                header_widget = title_widget

            if text is not None:
                header_widget.set_tooltip_text(text)

            header_widget.show_all()
            tab_number = self.notebook.append_page(page_container_widget, header_widget)

            if post_category is not None:
                self.page_container_widget_dict[post_category] = page_container_widget
                self.tab_num_dict[post_category] = tab_number
        else:
            tab_number = self.notebook.page_num(page_container_widget)

        # build dictionary of functions for each tab to reload it
        self.reload_function_dict[tab_number] = reload_function

        return page_container_widget, tab_number


# ----------------------------------------------------------------------
# Internal callbacks
# ----------------------------------------------------------------------

    def _key_pressed(self, widget, ev, data):
        """ Keypress callback for the main window"""
        # Open the debug dialog if the flag is set
        if ev.keyval == Gdk.KEY_F10 and self.debugDialog is not None:
            self.debugDialog.show()

    def _remove(self, widget, data):
        self.remove(widget)

    def _cleanup(self):
        """
        Method to be executed before destroying this widget.
        """
        self.clean_tempdir()
        # Add cleanup code here if needed
        pass

    def _close_tab(self, widget, notebook_page):
        """ Method to close a given notebook tab. """
        tab_index = self.notebook.page_num(notebook_page)
        if tab_index != -1:
            for i in range(tab_index+1,self.notebook.get_n_pages()):
                self.reload_function_dict[i-1] = self.reload_function_dict[i]
            last_index = self.notebook.get_n_pages()-1
            self.reload_function_dict[last_index] = None
            self.notebook.remove_page(tab_index)
            return True
        else:
            return False

    def _handle_popup(self, widget, event, menu):
        """Display a context menu for selecting the post type"""
        if event.button == 3:
            menu.show_all()
            menu.popup(None, widget, None, None, event.button, event.time)

    def _handle_menu(self, widget, posttype, post_category, notebook_page):
        """ Click handler for selecting the post type """
        tab_index = self.notebook.page_num(notebook_page)
        self.posts_mode_dict[post_category] = posttype
        self.notebook.set_current_page(tab_index)
        self.reload(None,None)

# ----------------------------------------------------------------------
# End of class OJOCWindow
# ----------------------------------------------------------------------

if __name__ == '__main__':
    # The main routine

    parser = argparse.ArgumentParser()
    parser.add_argument('-c','--citycc',nargs=1,help='Your location, e.g. Vienna, AT',metavar='CITY, CC')

    print OJOC.Config.SPLASH_TEXT

    try:
        n = parser.parse_args(sys.argv[1:])
        args = vars(n)
    except:
        sys.exit(1)

    loc = args.get('citycc')

    if loc is not None:
        print "Location specified as " + loc[0]
        loc = loc[0]

    win = OjocWindow()
    if win is not None:
        win.connect("delete-event", Gtk.main_quit)
        # This timeout is needed to display the loading
        # splash screen for a minimum duration of 100ms
        GLib.timeout_add(100, win.initialize, loc)
        Gtk.main()
        win._cleanup()
