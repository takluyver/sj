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

from .utils import compress_user
from .panels.pwd import PathLabel
from .panels.files import FilesTreeView
from .panels.git import GitPanel

class MyDBUSService(dbus.service.Object):
    def __init__(self, window):
        self.window = window
        super().__init__(conn=window.dbus_conn,
                         object_path='/io/github/takluyver/sj')

    @dbus.service.method('io.github.takluyver.sj', in_signature='sus')
    def update(self, cwd, histno, last_cmd):
        if cwd != self.window.cwd:
            self.window.emit('wd_changed', cwd)
        if histno != self.window.histno:
            self.window.emit('command_run', last_cmd, histno)
        self.window.emit('prompt')


this_dir = dirname(abspath(__file__))
update_file = pjoin(this_dir, 'send_update.py')
bashrc = pjoin(this_dir, 'bashrc.sh')
prompt_cmd = 'SJ_UPDATE_COMMAND=' + update_file

class MyWindow(Gtk.Window):
    __gsignals__ = {
        'prompt': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'command_run': (GObject.SIGNAL_RUN_FIRST, None, (str, int)),
        'wd_changed': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }
    
    histno = 0
    last_cmd = None
    cwd = None
    
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
        self.rhs = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL)
        self.rhs.add(PathLabel(self))
        lr_split.pack2(self.rhs, False, True)
        self.files_tv = FilesTreeView(self)
        scroll_window = Gtk.ScrolledWindow(expand=True)
        scroll_window.add(self.files_tv)
        #scroll_window.set_property('propagate-natural-width', True)
        self.rhs.add(scroll_window)
        self.rhs.add(GitPanel(self))

    def do_wd_changed(self, wd):
        self.cwd = wd
        self.set_title(compress_user(wd))

    def do_cmd_run(self, last_cmd, histno):
        self.histno = histno
        self.last_cmd = last_cmd

def main():
    GObject.threads_init()
    DBusGMainLoop(set_as_default=True)
    win = MyWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    win.term.grab_focus()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()
