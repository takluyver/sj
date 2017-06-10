from gi.repository import Gtk, GLib
from sj.utils import compress_user

css = b"""
GtkLabel {
    font-size: x-large;
}
"""

class PathLabel(Gtk.Label):
    larger = False
    def __init__(self, window):
        super().__init__()
        self.style_provider = Gtk.CssProvider()
        self.style_provider.load_from_data(css)
        self.set_markup("Configure your shell to run <b>$SJ_UPDATE_COMMAND</b> "
                        "at each prompt.")
        window.connect('wd_changed', self.wd_changed)
    
    def wd_changed(self, _, wd):
        path = compress_user(wd)
        self.set_markup('<big>%s</big>' % GLib.markup_escape_text(path))
