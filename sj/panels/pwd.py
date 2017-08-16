from gi.repository import Gtk, GLib
from sj.utils import compress_user

class PathLabel(Gtk.Label):
    panel_name = 'pwd'
    larger = False
    def __init__(self, window):
        super().__init__(margin_bottom=5, margin_top=5)
        self.set_markup("Configure your shell to run <b>$SJ_UPDATE_COMMAND</b> "
                        "at each prompt.")
    
    def on_prompt(self, window, values):
        path = compress_user(values['cwd'])
        self.set_markup('<big>%s</big>' % GLib.markup_escape_text(path))
        self.show()

constructor = PathLabel
