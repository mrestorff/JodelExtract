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

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GdkPixbuf
from gi.repository import Pango
import TOOLS.prettytime as prettytime
import requests
import os
import cgi
import re

COLORS = ['#06A3CB', '#8ABDB0', '#9EC41C', '#DD5F5F', '#FF9908', '#FFBA00']
DBG_NO_IMAGES = False


class DebugWindow:
    """ A window recording every answer by the API.
        useful to discover new features or for debugging"""

    def __init__(self, main_window, parent):

        self.main_window = main_window
        self.parent = parent
        self.data = "=== Execution started ===\n"
        self.font = Pango.FontDescription('monospace')
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.tb = Gtk.TextBuffer.new()

    def show(self):
        self.tb.set_text(self.data)
        textbox = Gtk.TextView().new_with_buffer(self.tb)
        textbox.set_editable(False)
        textbox.set_hexpand(True)
        textbox.set_vexpand(True)
        textbox.set_margin_top(5)
        textbox.set_margin_bottom(5)
        textbox.set_margin_left(5)
        textbox.set_margin_right(5)
        textbox.modify_font(self.font)
        container = Gtk.ScrolledWindow()
        container.connect("size-allocate", self._scroll)
        container.add(textbox)

        dialog = Gtk.Dialog('Debug Data')
        copy_btn = Gtk.Button('Copy to Clipboard')
        copy_btn.connect('pressed', self._copy, None)
        dialog.get_action_area().add(copy_btn)
        dialog.get_content_area().add(container)
        dialog.set_transient_for(self.main_window)
        dialog.set_size_request(800, 600)
        dialog.show_all()
        adj = container.get_vadjustment()
        adj.set_value(adj.get_lower())

        dialog.run()
        dialog.destroy()

    def update(self, data):
        self.data += data

    def _copy(self, widget, data):
        self.clipboard.set_text(self.tb.get_text(self.tb.get_start_iter(), self.tb.get_end_iter(), True), -1)

    def _scroll(self, widget, data):
        adj = widget.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())


class Colors:
    """ Class providing a color palette accepted by the API """

    def __init__(self):
        self.colorspec = ['#06A3CB','#8ABDB0','#9EC41C','#DD5F5F','#FF9908','#FFBA00']
        self.colors = []
        for color in self.colorspec:
            rgba = Gdk.RGBA()
            rv = rgba.parse(color)
            if (not rv):
                raise ValueError
            self.colors.append(rgba)

    def get_palette(self):
        return self.colors


class PostEditor (Gtk.Dialog):
    """
    A GTK dialog to edit a new post or a reply.
    Lets the user type a message, select an image for uploading,select a color and a name (however, the latter is ignored by the API
    unless a valid geographic name)"""

    def __init__(self, main_window, color):
        Gtk.Dialog.__init__(self, use_header_bar=True)

        self.message = None
        self.image = None

        self.main_window = main_window
        self.color_chooser = color_chooser = Gtk.ColorChooserWidget(show_editor=False)
        color_chooser.add_palette(Gtk.Orientation.HORIZONTAL, 9, Colors().get_palette())
        color_chooser.show_editor = False
        if (color is not None):
            rgba = color_chooser.get_rgba()
            rgba.parse(color)
            color_chooser.set_rgba(rgba)
        color_chooser.set_use_alpha(False)
        grid_container = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL)
        self.text = Gtk.TextBuffer()
        self.name = Gtk.TextBuffer()
        self.imageChooser = Gtk.FileChooserButton('Select Image', Gtk.FileChooserAction.OPEN)

        ## Add *.jpg filter
        jpg_filter = Gtk.FileFilter()
        jpg_filter.set_name('JPEG Files')
        jpg_filter.add_pattern('*.jpg')
        jpg_filter.add_pattern('*.jpeg')
        self.imageChooser.add_filter(jpg_filter)

        ## Add mime type filter. Some OSs do not support this, so make it second
        mime_filter = Gtk.FileFilter()
        mime_filter.set_name('Image Files')
        mime_filter.add_mime_type('image/jpeg')
        mime_filter.add_mime_type('image/gif')
        self.imageChooser.add_filter(mime_filter)

        grid_container.set_margin_top(5)
        grid_container.set_margin_bottom(5)
        grid_container.set_margin_left(5)
        grid_container.set_margin_right(5)
        color_chooser.set_margin_top(5)
        color_chooser.set_margin_bottom(5)
        color_chooser.set_margin_left(5)
        color_chooser.set_margin_right(5)

        # Generate frame widgets for all entry fields
        # and set their parameters
        image_frame = Gtk.Frame(label='Image')
        text_frame = Gtk.Frame(label='Text')
        name_frame = Gtk.Frame(label='Name')
        text_view_widget = Gtk.TextView.new_with_buffer(self.text)
        text_frame.set_vexpand(True)
        text_frame.set_hexpand(True)
        text_frame.set_halign(Gtk.Align.FILL)
        text_frame.set_valign(Gtk.Align.FILL)
        text_frame.add(text_view_widget)
        name_frame.add(Gtk.TextView.new_with_buffer(self.name))
        image_frame.add(self.imageChooser)
        image_frame.set_hexpand(True)
        grid_container.add(text_frame)
        grid_container.add(image_frame)
        grid_container.add(name_frame)

        # generate a notebook. The first page will be post content,# the second one will be a color picker for the post color.
        notebook_widget = Gtk.Notebook()
        notebook_widget.append_page(grid_container, Gtk.Label('Content'))
        notebook_widget.append_page(color_chooser, Gtk.Label('Post Color'))

        # generate the dialog's buttons and set their parameters
        cancel_button = Gtk.Button('Cancel')
        cancel_button.set_hexpand(True)
        cancel_button.set_halign(Gtk.Align.START)
        send_button = Gtk.Button('Send')
        send_button.set_halign(Gtk.Align.END)
        send_button.get_style_context().add_class('suggested-action')

        # add the widgets to the content area of the dialog,# set dialog parameters and show them
        self.get_content_area().add(notebook_widget)
        self.add_action_widget(cancel_button, 0)
        self.add_action_widget(send_button, 1)
        self.set_transient_for(main_window)
        self.set_deletable(False)
        self.show_all()

    def get_post(self):
        """
        Return the edited post, an image if selected, and
        the selected color in a dict containing the following entries:
        'color':      Color string in the format expected by the API,'message':    The edited message text
        'name':       The selected posting name. May be ignored by the API.
        'image_data': The contents of the selected image file, None if no image was selected.}
        """
        color = self.color_chooser.get_rgba()
        text = self.text.get_text(self.text.get_start_iter(),self.text.get_end_iter(),True)
        name = self.name.get_text(self.name.get_start_iter(),self.name.get_end_iter(),True)
        imagePath_opsys = self.imageChooser.get_filename()
        imagePath = None
        print imagePath_opsys

        if imagePath_opsys is not None:
            imagePathUtf8 = GLib.filename_to_utf8(imagePath_opsys, len(imagePath_opsys),0,0)
            if (imagePathUtf8 is None):
                return {'error': 'Could not convert filename to UTF8'}
            imagePath = imagePathUtf8

        image = None

        if ((text is None or text == '') and (imagePath is None or imagePath[0] == '')):
            return {'error': 'Neither an image nor a message given'}

        if (imagePath is not None):
            with open(imagePath, 'rb') as img:
                image = img.read()
            if image is None:
                return {'error': 'Could not read image'}
            if (text == ''):
                text = 'Photo'

        # FIXME this may be a leak
        # But if the following line is uncommented, I get
        # ValueError: Pointer arguments are restricted to integers, capsules, and None. See: https://bugzilla.gnome.org/show_bug.cgi?id=683599
        # GLib.free(imagePath)

        color_str = "%02X%02X%02X" % (round(color.red * 0xFF),round(color.green * 0xFF),round(color.blue * 0xFF))

        return {'color': color_str,'message': text,'name': name,'image_data': image}


class ImageViewer (Gtk.Dialog):
    """Featureless dialog for displaying image posts"""

    def __init__(self, main_window, pixbuf, top_text=None, bottom_text=None):
        Gtk.Dialog.__init__(self)
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        if(top_text is not None):
            self.get_content_area().add(Gtk.Label(top_text))
        self.get_content_area().add(image)
        if(bottom_text is not None):
            self.get_content_area().add(Gtk.Label(bottom_text))
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_transient_for(main_window)
        self.show_all()

        return None


class Post (Gtk.Grid):
    """Widget containing the post content (text or image), metadata
       (location, time), and buttons to perform interactions (up/downvote,delete if we are the creator) with that post."""

    def _link_(self,label,uri,data):
        self.main_window._open_channel(self,uri)
        return True

    def __init__(self,tempdir,post,main_window,connection,userno=None,callback=None,ispost=True):
        """ tempdir     Directory for downloaded images
            post        Post data
            main_window Reference to main window
            userno      Number of user in post
            callback    Callback for open button
            ispost      Flag if this is an original post (True) or a reply (False)"""

        Gtk.Grid.__init__(self)
        self.connection = connection
        self.tempdir = tempdir
        self.main_window = main_window
        self.imageViewer = False

        print post['color']
        ok, col = Gdk.Color.parse('#' + post['color'])
        if not ok:
            col = None

        self.color = col
        self.colorspec = '#' + post['color']
        ok, fgcol = Gdk.Color.parse('#ffffff')

        ## Generate the lower bar with the buttons (delete, upvote, downvote etc.)

        location_widget = Gtk.Label(post['location']['name'] +
            ' (' +
            named_distance(post['distance']) +
            ')')
        location_widget.modify_fg(Gtk.StateType.NORMAL, fgcol)  # white

        votes_widget = Gtk.Label(post['vote_count'])
        time_widget = Gtk.Label(prettytime.pretty(post['created_at']))

        self.attach(location_widget, 0, 1, 3, 1)
        self.attach(time_widget, 3, 1, 1, 1)

        ## We use the presence of a callback to determine if we opened the
        #  post already
        if (callback is not None):
            children = post.get('child_count')
            rep = Gtk.Button.new_from_icon_name('emblem-mail', 1)
            rep.set_always_show_image(True)

            if (children is None):
                children = 0
            rep.set_label(' (' + str(children) + ')')
            rep.connect('clicked', callback, post['post_id'])
            self.attach(rep, 4, 1, 1, 1)
        else:
            parent_creator = post.get('parent_creator')
            if (parent_creator is not None and parent_creator != 0):
                parent_creator_label = Gtk.Label('(OJ)')
            elif (userno is not None):
                parent_creator_label = Gtk.Label('#' + str(userno))
            else:
                parent_creator_label = Gtk.Label('')
            self.attach(parent_creator_label, 4, 1, 1, 1)

        if (post['post_own'] == 'own'):
            delete_widget = Gtk.Button.new_from_icon_name('window-close', 1)
            delete_widget.connect('clicked', self._delete_callback, post['post_id'])
        else:
            delete_widget = Gtk.Label('')

        voted = post.get('voted')

        if (voted is None):
            upvote_widget = Gtk.Button.new_from_icon_name('go-up', 1)
            upvote_widget.connect('button_press_event', self._vote_callback, 1, post['post_id'])
            downvote_widget = Gtk.Button.new_from_icon_name('go-down', 1)
            downvote_widget.connect('button_press_event', self._vote_callback, -1, post['post_id'])
        elif (voted == 'up'):
            upvote_widget = Gtk.Button.new_from_icon_name('go-up', 1)
            upvote_widget.set_state(Gtk.StateType.INSENSITIVE)
            downvote_widget = Gtk.Label('')
        else:
            downvote_widget = Gtk.Button.new_from_icon_name('go-down', 1)
            downvote_widget.set_state(Gtk.StateType.INSENSITIVE)
            upvote_widget = Gtk.Label('')

        if ispost:
            pinned = post.get('pinned')
            pin_count = post.get('pin_count')

            if pin_count is None:
                pin_count_text = ''
            else:
                pin_count_text = ' (%d)' % pin_count

            if (pinned is None):
                pin_widget = Gtk.Button(u"\U0001F4CD"+pin_count_text)
                pin_widget.connect('button_press_event', self._pin_callback, 1, post['post_id'])
            else:
                pin_widget = Gtk.Button(u"\U0001F4CD\u00D7"+pin_count_text)
                pin_widget.connect('button_press_event', self._pin_callback, -1, post['post_id'])
        else:
            pin_widget = Gtk.Label('')

        upvote_widget.set_hexpand(False)

        self.attach(pin_widget,      5, 1, 1, 1)
        self.attach(delete_widget,   6, 1, 1, 1)
        self.attach(upvote_widget,   7, 1, 1, 1)
        self.attach(votes_widget,    8, 1, 1, 1)
        self.attach(downvote_widget, 9, 1, 1, 1)


        image_url = post.get('image_url')
        if (image_url is None):
            # display the post's text if no image is contained
            lab = Gtk.Label()

            message = re.sub(r'\@([^\s]+)',r'<a href="\1">@\1</a>',cgi.escape(post['message']))

            lab.set_markup('<span size="14000">' + message + '</span>')
            lab.connect('activate-link', self._link_, None)
            lab.set_use_markup(True)
            lab.set_justify(Gtk.Justification.LEFT)
            lab.set_alignment(xalign=0, yalign=0)
            lab.set_hexpand(True)
            lab.set_padding(5, 5)
            lab.set_line_wrap(True)
            lab.modify_bg(Gtk.StateType.NORMAL, col)
            lab.modify_fg(Gtk.StateType.NORMAL, fgcol)
            self.attach(lab, 0, 0, 10, 1)
        elif not DBG_NO_IMAGES:
            # Download the image into the temp folder (if not yet downloaded) and
            # display an image preview in the post
            image_headers = post.get('image_headers')
            path = os.path.join(self.tempdir, post['post_id'] + ".jpg")
            if not (os.path.exists(path) and os.path.isfile(path)):
                print "Downloading image https:" + image_url + "... "
                try:
                    with open(path, 'wb') as handle:
                        if (image_headers is not None):
                            r = connection.imgsession.request('GET', 'https:' + image_url, headers=image_headers)
                        else:
                            r = connection.imgsession.request('GET', 'https:' + image_url)

                        if not r.ok:
                            print "Could not get image."

                        for block in r.iter_content(1024):
                            handle.write(block)

                except requests.exceptions.ConnectionError as e:
                    print "failed: " + str(e)

            try:
                # Scale the post to the aspect ratio expected by the app
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(path).scale_simple(600, 960, GdkPixbuf.InterpType.NEAREST)
                # Get the top 150 lines of the scaled image for preview
                spb = pixbuf.new_subpixbuf(0, 0, pixbuf.get_width(), 150)
                ev = Gtk.EventBox()
                img = Gtk.Image.new_from_pixbuf(spb)
                img.set_alignment(xalign=0, yalign=0.5)
                img.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
                ev.connect('button_press_event', self._view_image, pixbuf)
                ev.connect('button_release_event', self._destroy_image, None)
                ev.add(img)
                self.attach(ev, 0, 0, 10, 1)
            except IOError as e:
                print "Image file " + path + "not found: " + str(e)
            except GLib.Error as e:
                print "Could not load image file "+ path + ": "+str(e)

        self.foreach(self._set_color, col)
        self.set_column_homogeneous(True)

    def _delete_callback(self, widget, post_id):
        rv = self.connection.delete_post(post_id)
        if (rv is not False):
            print "Deleted " + post_id
        self.main_window.reload(None, None)

    def _vote_callback(self, widget, dummy, which, post_id):
        if which > 0:
            rv = self.connection.upvote(post_id)
        else:
            rv = self.connection.downvote(post_id)
        if (rv is not None):
            print "Voted (" + str(which)+") " + post_id
        self.main_window.reload(None, None)

    def _pin_callback(self, widget, dummy, which, post_id):
        if which > 0:
            rv = self.connection.pin(post_id)
        else:
            rv = self.connection.unpin(post_id)
        if (rv is not None):
            print "Pinned (" + str(which)+") " + post_id
        self.main_window.reload(None, None)

    def _view_image(self, widget, event, pixbuf):
        self.imageViewer = ImageViewer(self.main_window, pixbuf)
        if (self.imageViewer is False):
            return

    def _destroy_image(self, widget, event, ign):
        if (self.imageViewer is False):
            return
        self.imageViewer.destroy()

    def _set_color(self, widget, color):
        if isinstance(widget, Gtk.Button):
            widget.set_relief(Gtk.ReliefStyle.HALF)
        widget.modify_bg(Gtk.StateType.NORMAL, color)

def named_distance(distance):
    if (distance < 2):
        return "very near"
    elif (distance < 15):
        return "near"
    else:
        return "remote"
