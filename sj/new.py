#!/usr/bin/python3
import gi
from os.path import abspath, dirname, join as pjoin
import signal

gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')

from gi.repository import Gtk, GObject, GLib, Vte, Gio, Gdk

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from .utils import compress_user
from .panels import pwd, git, files, dirstack

TERM_COLORS = [  # Selenized white from https://gogh-co.github.io/Gogh/
    '#ebebeb',
    '#d6000c',
    '#1d9700',
    '#c49700',
    '#0064e4',
    '#dd0f9d',
    '#00ad9c',
    '#878787',
    '#cdcdcd',
    '#bf0000',
    '#008400',
    '#af8500',
    '#0054cf',
    '#c7008b',
    '#009a8a',
    '#282828',
]

class MyDBUSService(dbus.service.Object):
    def __init__(self, window):
        self.window = window
        super().__init__(conn=window.dbus_conn,
                         object_path='/io/github/takluyver/sj')

    @dbus.service.method('io.github.takluyver.sj', in_signature='')
    def get_update_args(self):
        return ' '.join(['{} "{}"'.format(k, v)
                 for (k, v) in sorted(self.window.shell_request.items())])

    @dbus.service.method('io.github.takluyver.sj', in_signature='a{ss}')
    def update(self, values):
        self.window.emit('prompt', values)

    @dbus.service.method('io.github.takluyver.sj', in_signature='')
    def get_version(self):
        from . import __version__
        return __version__

    @dbus.service.method('io.github.takluyver.sj', in_signature='', out_signature='aa{sv}')
    def get_panels_status(self):
        return [{'name': p.panel_name,
                 'enabled': p.panel_name not in self.window.disabled_panel_names,
                 'visible': p.get_visible()}
                for p in self.window.panels]

    @dbus.service.method('io.github.takluyver.sj', in_signature='s')
    def disable_panel(self, name):
        panel = self.window.panel_by_name(name)
        panel.hide()
        if name not in self.window.disabled_panel_names:
            self.window.disabled_panel_names.add(name)
            self.window.disconnect_by_func(panel.on_prompt)

    @dbus.service.method('io.github.takluyver.sj', in_signature='s')
    def enable_panel(self, name):
        panel = self.window.panel_by_name(name)
        if name in self.window.disabled_panel_names:
            self.window.disabled_panel_names.discard(name)
            self.window.connect('prompt', panel.on_prompt)
        # The panel should show itself if relevant at the next prompt

this_dir = dirname(abspath(__file__))
update_file = pjoin(this_dir, 'send_update.py')
bashrc = pjoin(this_dir, 'bashrc.sh')
prompt_cmd = 'SJ_UPDATE_COMMAND=$(eval $({} --discover))'.format(update_file)

class MyWindow(Gtk.ApplicationWindow):
    __gsignals__ = {
        'prompt': (GObject.SIGNAL_RUN_FIRST, None, (object,)),
    }
    
    histno = 0
    last_cmd = None
    cwd = None
    
    def __init__(self, app):
        super().__init__(application=app, title="sj",
                         default_width=1200, default_height=700)
        self.set_default_icon_name('utilities-terminal')
        self.app = app
        self.panels = []
        self.disabled_panel_names = set()
        self.dbus_conn = dbus.SessionBus()
        self.update_service = MyDBUSService(self)
        
        # TODO: better way to make term not tiny?
        lr_split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, position=800)
        
        self.add(lr_split)
        self.term = Vte.Terminal(allow_hyperlink=True)
        self.term.set_colors(*self.prepare_colours())
        self.term.connect("child-exited", self.app.quit_on_signal)
        self.term.connect("button-press-event", self.on_button_press)
        PCRE2_MULTILINE = 0x00000400
        self.regex_tag_http = self.term.match_add_regex(
            Vte.Regex.new_for_match(r"https?://[^\s]+", -1, PCRE2_MULTILINE), 0
        )
        self.term.spawn_sync(Vte.PtyFlags.DEFAULT, 
                None,     # CWD
                # TODO: use your shell of choice
                ['/bin/bash', '--rcfile', bashrc], # argv
                ['SJ_DBUS_NAME={}'.format(self.dbus_conn.get_unique_name()),
                 prompt_cmd,
                ],
                GLib.SpawnFlags.DEFAULT,
                None,     # child_setup
                None,     # child_setup_data
                None,     # cancellable
            )
        lr_split.pack1(self.term, True, False)
        self.rhs = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL)
        lr_split.pack2(self.rhs, False, True)

        for panelmod in [pwd, files, git, dirstack]:
            self.new_panel(panelmod.constructor)

        self.setup_actions()

    @staticmethod
    def prepare_colours():
        res = [Gdk.RGBA() for _ in range(16)]
        for rgba, hex in zip(res, TERM_COLORS):
            rgba.parse(hex)

        fg, bg = Gdk.RGBA(), Gdk.RGBA()
        fg.parse('#474747')
        bg.parse('#ffffff')
        return fg, bg, res

    def on_button_press(self, widget, event):
        # Button 1 = left, 2 = middle, 3 = right
        if event.button == 1:
            # Ctrl+leftclick on a URL should open it
            if event.get_state() & Gdk.ModifierType.CONTROL_MASK == Gdk.ModifierType.CONTROL_MASK:
                url = self.term.hyperlink_check_event(event)
                if url is None:
                    url, tag = self.term.match_check_event(event)
                if url:
                    Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
                    return True  # Handled

        return False
        #self.term.do_button_press_event(widget, event)

    def new_panel(self, constructor):
        panel = constructor(self)
        self.rhs.add(panel)
        self.panels.append(panel)
        self.connect('prompt', panel.on_prompt)

    def panel_by_name(self, name):
        for panel in self.panels:
            if panel.panel_name == name:
                return panel
        raise KeyError(name)

    @property
    def enabled_panels(self):
        for panel in self.panels:
            if panel.panel_name not in self.disabled_panel_names:
                yield panel

    @property
    def shell_request(self):
        d = {'cwd': '$PWD'}
        for p in self.panels:
            if hasattr(p, 'shell_request'):
                d.update(p.shell_request)
        return d

    def setup_actions(self):
        copy = Gio.SimpleAction.new('term-copy', None)
        copy.connect('activate', self.term_copy)
        self.add_action(copy)
        self.app.add_accelerator("<Control><Shift>c", "win.term-copy")

        paste = Gio.SimpleAction.new('term-paste', None)
        paste.connect('activate', self.term_paste)
        self.add_action(paste)
        self.app.add_accelerator("<Control><Shift>v", "win.term-paste")

    def term_copy(self, *args):
        self.term.copy_clipboard()

    def term_paste(self, *args):
        self.term.paste_clipboard()

    def do_wd_changed(self, wd):
        self.cwd = wd
        self.set_title(compress_user(wd))

    def do_cmd_run(self, last_cmd, histno):
        self.histno = histno
        self.last_cmd = last_cmd

class SJApplication(Gtk.Application):
    def do_activate(self):
        win = MyWindow(self)
        self.add_window(win)
        win.show_all()
        win.term.grab_focus()

    def quit_on_signal(self, *args):
        self.quit()

def main():
    GObject.threads_init()
    DBusGMainLoop(set_as_default=True)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = SJApplication(application_id='io.github.takluyver.sj')
    app.run()
