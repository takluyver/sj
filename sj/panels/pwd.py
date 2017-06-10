import os.path
from gi.repository import Gtk

_home = os.path.expanduser('~')
def compress_user(path):
    if path.startswith(_home):
        return '~' + path[len(_home):]
    return path

class PathLabel(Gtk.Label):
    def __init__(self, window):
        super().__init__()
        self.set_markup("Configure your shell to run <b>$SJ_UPDATE_COMMAND</b> "
                        "at each prompt.")
        window.connect('wd_changed', self.wd_changed)
    
    def wd_changed(self, _, wd):
        self.set_text(compress_user(wd))
