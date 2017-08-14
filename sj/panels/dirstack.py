from gi.repository import Gtk

def make_list_store(dirs):
    liststore = Gtk.ListStore(str)
    for d in dirs:
        liststore.append([d])

    return liststore

class DirsPanel(Gtk.VBox):
    shell_request = {'dirstack': '$(dirs -p)'}
    liststore = None

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,
            spacing=5, margin=3,
        )
        self.pack_start(Gtk.HSeparator(), False, False, 0)
        self.title = Gtk.Label(label='<b>popd</b> goes to:', use_markup=True)
        self.add(self.title)
        self.list = Gtk.TreeView(can_focus=False,
                                 headers_visible=False,
                                )
        namecol = Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=0)
        namecol.set_property('expand', True)
        self.list.append_column(namecol)
        self.add(self.list)

        window.connect('prompt', self.prompt)

    def prompt(self, window, values):
        dirstack = values['dirstack'].split('\n')[1:]
        if not dirstack:
            self.hide()
            return

        self.show()
        self.liststore = make_list_store(dirstack)
        self.list.set_model(self.liststore)
