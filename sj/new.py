#!/usr/bin/python3
import gi
from os.path import abspath, dirname, join as pjoin
import signal

gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')

from gi.repository import Gtk, GObject, GLib, Vte

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from .panels.pwd import PathLabel
from .panels.files import FilesTreeView
from .panels.git import GitPanel

class MyDBUSService(dbus.service.Object):
    def __init__(self, window):
        self.window = window
        dbus.service.Object.__init__(self, conn=window.dbus_conn,
                                     object_path='/io/github/takluyver/sj')

    @dbus.service.method('io.github.takluyver.sj', in_signature='ss')
    def update(self, cwd, last_cmd):
        self.window.emit('wd_changed', cwd)


this_dir = dirname(abspath(__file__))
update_file = pjoin(this_dir, 'send_update.py')
bashrc = pjoin(this_dir, 'bashrc.sh')
prompt_cmd = 'SJ_UPDATE_COMMAND=python3 "%s"' % update_file

class MyWindow(Gtk.Window):
    __gsignals__ = {
        'wd_changed': (GObject.SIGNAL_RUN_FIRST, None,
                      (str,))
    }
    
    def __init__(self):
        super().__init__(title="sj", default_width=1200, default_height=700)
        self.panels = []
        self.dbus_conn = dbus.SessionBus()
        self.update_service = MyDBUSService(self)
        
        # TODO: better way to make term not tiny?
        lr_split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, position=800)
        
        
        self.add(lr_split)
        self.term = Vte.Terminal()
        self.term.connect("child-exited", Gtk.main_quit)
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
        self.rhs = Gtk.VBox()
        self.rhs.pack_start(PathLabel(self), False, False, 5)
        lr_split.pack2(self.rhs, False, True)
        self.files_tv = FilesTreeView(self)
        scroll_window = Gtk.ScrolledWindow()
        scroll_window.add(self.files_tv)
        scroll_window.set_property('propagate-natural-width', True)
        self.rhs.add(scroll_window)
        self.rhs.add(GitPanel(self))


def main():
    GObject.threads_init()
    DBusGMainLoop(set_as_default=True)
    win = MyWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    win.term.grab_focus()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()
