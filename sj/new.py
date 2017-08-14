#!/usr/bin/python3
import gi
from os.path import abspath, dirname, join as pjoin
import signal

gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')

from gi.repository import Gtk, GObject, GLib, Vte, Gio

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from .utils import compress_user
from .panels import pwd, git, files, dirstack

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
        if values['cwd'] != self.window.cwd:
            self.window.emit('wd_changed', values['cwd'])
        self.window.emit('prompt', values)

    @dbus.service.method('io.github.takluyver.sj', in_signature='')
    def get_version(self):
        from . import __version__
        return __version__

    @dbus.service.method('io.github.takluyver.sj', in_signature='', out_signature='a(sbb)')
    def get_panels_status(self):
        return [(p.panel_name, True, p.get_visible()) for p in self.window.panels]


this_dir = dirname(abspath(__file__))
update_file = pjoin(this_dir, 'send_update.py')
bashrc = pjoin(this_dir, 'bashrc.sh')
prompt_cmd = 'SJ_UPDATE_COMMAND=$(eval $({} --discover))'.format(update_file)

class MyWindow(Gtk.ApplicationWindow):
    __gsignals__ = {
        'prompt': (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        'command_run': (GObject.SIGNAL_RUN_FIRST, None, (str, int)),
        'wd_changed': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }
    
    histno = 0
    last_cmd = None
    cwd = None
    
    def __init__(self, app):
        super().__init__(application=app, title="sj", default_width=1200, default_height=700)
        self.app = app
        self.panels = []
        self.dbus_conn = dbus.SessionBus()
        self.update_service = MyDBUSService(self)
        
        # TODO: better way to make term not tiny?
        lr_split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, position=800)
        
        self.add(lr_split)
        self.term = Vte.Terminal()
        self.term.connect("child-exited", self.app.quit_on_signal)
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

    def new_panel(self, constructor):
        panel = constructor(self)
        self.rhs.add(panel)
        self.panels.append(panel)

    @property
    def shell_request(self):
        d = {'cwd': '$PWD'}
        for p in self.panels:
            if hasattr(p, 'shell_request'):
                d.update(p.shell_request)
        return d

    def setup_actions(self):
        copy = Gio.SimpleAction.new('term_copy', None)
        copy.connect('activate', self.term_copy)
        self.add_action(copy)
        self.app.add_accelerator("<Control><Shift>c", "win.term_copy")

        paste = Gio.SimpleAction.new('term_paste', None)
        paste.connect('activate', self.term_paste)
        self.add_action(paste)
        self.app.add_accelerator("<Control><Shift>v", "win.term_paste")

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
        win.connect("delete-event", self.quit_on_signal)
        win.show_all()
        win.term.grab_focus()

    def quit_on_signal(self, *args):
        self.quit()

def main():
    GObject.threads_init()
    DBusGMainLoop(set_as_default=True)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = SJApplication()
    app.run([])
