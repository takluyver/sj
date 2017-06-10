import os.path
import re
import subprocess
from threading import Thread
from gi.repository import Gtk, GLib, GdkPixbuf
from sj.utils import compress_user


status_to_icon_name = {
    'A': 'list-add',
    'M': 'text-x-generic',
    'D': 'edit-delete',
    '?': 'list-add',
}

# TODO: R for renamed

head_branch_re = re.compile(r'ref: refs/heads/(.*)')

def check_repo(pwd):
    try:
        reporoot = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'],
                                           universal_newlines=True,
                                           cwd=pwd).strip()
    except subprocess.CalledProcessError as e:
        # Not in a git repo
        return {'reporoot': None}

    data = {'stage': [], 'wd': [], 'branch': None, 'commit': None,
            'reporoot': reporoot}

    # Get the branch we're on. This is easy enough without shelling out
    with open(os.path.join(reporoot, '.git', 'HEAD')) as f:
        m = head_branch_re.match(f.read().strip())
        if m:
            data['branch'] = m.group(1)

    # Describe the latest commit
    try:
        commit_info = subprocess.check_output(['git', 'log', '-n', '1',
                                       '--format=format:%h\x1f%cr\x1f%s'],
                                      cwd=reporoot,
                                      universal_newlines=True)
        c = data['commit'] = {}
        c['shorthash'], c['reltime'], c['message'] = commit_info.split('\x1f', 2)
    except subprocess.CalledProcessError:
        # This happens in a brand new repo with no commits.
        data['commit'] = {'shorthash': '', 'reltime': '',
                          'message': '(No commits)'}

    status = subprocess.check_output(['git', 'status', '--porcelain'],
                                  cwd=reporoot,
                                  universal_newlines=True)
    for line in status.splitlines():
        stagestatus = line[0]
        wdstatus = line[1]
        path = line[3:]
        
        if stagestatus in 'AMD':
            data['stage'].append({'path': path,
                                  'status': stagestatus,
                                 })
        if wdstatus in 'MD?':
            data['wd'].append({'path': path,
                               'status': wdstatus,
                              })

    return data

def code_label(txt):
    l = Gtk.Label(halign=Gtk.Align.START)
    l.set_markup('<tt>%s</tt>' % GLib.markup_escape_text(txt))
    return l

def small_icon(name):
    i = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.SMALL_TOOLBAR)
    i.set_halign(Gtk.Align.END)
    return i

def status_icon_view():
    return Gtk.IconView(pixbuf_column=0, text_column=1, item_padding=0, 
        row_spacing=3, item_width=100, expand=True,
        selection_mode=Gtk.SelectionMode.NONE, can_focus=False,
        item_orientation=Gtk.Orientation.HORIZONTAL)

class GitPanel(Gtk.Grid):
    status_to_pixbuf = None

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,
            row_spacing=5, column_spacing=5,
        )
        self.repo_label = Gtk.Label(label='Git')
        self.attach(self.repo_label, 0, 0, 2, 1)

        self.stage_view = status_icon_view()
        stage_scroll = Gtk.ScrolledWindow(propagate_natural_width=True)
        stage_scroll.add(self.stage_view)
        self.attach(stage_scroll, 0, 1, 2, 1)

        self.attach(small_icon('go-up'), 0, 2, 1, 1)
        self.attach(code_label("git add <file>"), 1, 2, 1, 1)

        self.attach(small_icon('go-down'), 0, 3, 1, 1)
        self.attach(code_label("git reset HEAD <file>"), 1, 3, 1, 1)

        self.wd_view = status_icon_view()
        wd_scroll = Gtk.ScrolledWindow(propagate_natural_width=True)
        wd_scroll.add(self.wd_view)
        self.attach(wd_scroll, 0, 4, 2, 1)

        self.attach(small_icon('go-down'), 0, 5, 1, 1)
        self.attach(code_label("git checkout -- <file>"), 1, 5, 1, 1)

        window.connect('prompt', self.prompt)

    def make_list(self, files):
        if self.status_to_pixbuf is None:
            theme = Gtk.IconTheme.get_default()
            self.status_to_pixbuf = { k: theme.load_icon(icon, 16, 0)
                for k, icon in status_to_icon_name.items()}

        liststore = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        for file in files:
            icon = self.status_to_pixbuf[file['status']]
            liststore.append([icon, file['path']])
        
        return liststore

    def _finish_update(self, data):
        if data['reporoot'] is None:
            self.hide()
            return
        
        self.show()
        self.repo_label.set_text('Git: %s' % compress_user(data['reporoot']))
        self.stage_view.set_model(self.make_list(data['stage']))
        self.wd_view.set_model(self.make_list(data['wd']))

    def _get_data_in_thread(self, pwd):
        res = check_repo(pwd)
        GLib.idle_add(self._finish_update, res)

    def prompt(self, window):
        Thread(target=self._get_data_in_thread, args=(window.cwd,), daemon=True).start()
