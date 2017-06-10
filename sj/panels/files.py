import os
from gi.repository import Gtk, Gdk, Gio

def get_icon(path):
    mimetype = Gio.content_type_guess(path)[0]
    return Gio.content_type_get_icon(mimetype)

def fmt_size(n):
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if n < 1024:
            return '{} {}'.format(n, unit)
        n //= 1024
    return 'huge'  # Technically correct


def make_list_store(path):
    # Cols: name, icon, size, path
    s = Gtk.ListStore(str, Gio.Icon, str, str)
    # TODO: configurable sorting, visibility of .hidden files
    for file in sorted(os.scandir(path),
            key=lambda f: (not f.is_dir(), f.name.lower())):
        if file.name.startswith('.'):
            continue
        if file.is_dir():
            icon = Gio.ThemedIcon.new('folder')
            size = ''
        else:
            icon = get_icon(file.path)
            size = fmt_size(file.stat().st_size)
        s.append([file.name, icon, size, file.path])
    return s

# ------
# MultiDragDropTreeView: copyright 2010 Kevin Mehall
# Used under MIT license.
# https://kevinmehall.net/2010/pygtk_multi_select_drag_drop

class MultiDragDropTreeView(Gtk.TreeView):
    '''TreeView that captures mouse events to make drag and drop work properly'''

    def __init__(self):
        super().__init__()
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.connect('button_press_event', self.on_button_press)
        self.connect('button_release_event', self.on_button_release)
        self.defer_select = False

    def on_button_press(self, widget, event):
        # Here we intercept mouse clicks on selected items so that we can
        # drag multiple items without the click selecting only one
        target = self.get_path_at_pos(int(event.x), int(event.y))
        if (target 
           and event.type == Gdk.EventType.BUTTON_PRESS
           and not (event.state & (Gdk.ModifierType.CONTROL_MASK|Gdk.ModifierType.SHIFT_MASK))
           and self.get_selection().path_is_selected(target[0])):
           # disable selection
           self.get_selection().set_select_function(lambda *ignore: False)
           self.defer_select = target[0]
    
    def on_button_release(self, widget, event):
        # re-enable selection
        self.get_selection().set_select_function(lambda *ignore: True)
        
        target = self.get_path_at_pos(int(event.x), int(event.y))	
        if (self.defer_select and target 
                and self.defer_select == target[0]
                and not (event.x==0 and event.y==0)): # certain drag and drop
            self.set_cursor(target[0], target[1], False)

        self.defer_select=False
# ------

class FilesTreeView(MultiDragDropTreeView):
    def __init__(self, window):
        super().__init__()
        namecol = Gtk.TreeViewColumn("Name")
        namecol.set_property('expand', True)
        self.append_column(namecol)
        icon_renderer = Gtk.CellRendererPixbuf()
        namecol.pack_start(icon_renderer, False)
        namecol.add_attribute(icon_renderer, "gicon", 1)
        # Space between the icon and the name
        namecol.pack_start(Gtk.CellRendererText(text=' '), False)
        name_renderer = Gtk.CellRendererText()
        namecol.pack_start(name_renderer,  True)
        namecol.add_attribute(name_renderer, "text", 0)
        self.append_column(Gtk.TreeViewColumn("Size", Gtk.CellRendererText(), text=2))

        window.connect('wd_changed', self.wd_changed)

        self.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
            [('text/uri-list', 0, 1)],  Gdk.DragAction.COPY)
        self.connect("drag-data-get", self.on_drag_data_get)

    def wd_changed(self, _, wd):
        new_files_store = make_list_store(wd)
        self.set_model(new_files_store)

    def on_drag_data_get(self, widget, drag_context, data, info, time):
        selected_rows = self.get_selection().get_selected_rows()[1]
        model = self.get_model()

        uris = []
        for row_path in selected_rows:
            selected_iter = model.get_iter(row_path)
            file_path = model.get_value(selected_iter, 3)
            uris.append('file://' + file_path)

        data.set_uris(uris)
