import os.path
import re
import subprocess
from threading import Thread
from gi.repository import Gtk, GLib, GdkPixbuf, Pango
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
                                           universal_newlines=True, stderr=subprocess.DEVNULL,
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

_escape = GLib.markup_escape_text

def icon_and_label(icon_name, txt):
    box = Gtk.HBox()
    i = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.SMALL_TOOLBAR)
    i.set_property('margin-left', 5)
    box.pack_start(i, False, False, 0)
    l = Gtk.Label(halign=Gtk.Align.START, margin_left=8)
    l.set_markup('<tt>%s</tt>' % _escape(txt))
    box.pack_start(l, True, True, 0)
    return box

def status_icon_view():
    return Gtk.IconView(pixbuf_column=0, text_column=1, item_padding=0, 
        row_spacing=3, item_width=100, expand=True,
        selection_mode=Gtk.SelectionMode.NONE, can_focus=False,
        item_orientation=Gtk.Orientation.HORIZONTAL)

class GitPanel(Gtk.VBox):
    status_to_pixbuf = None

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,
            spacing=5, margin=3,
        )
        self.pack_start(Gtk.HSeparator(), False, False, 0)
        hbox = Gtk.HBox()
        self.repo_label = Gtk.Label(label='Git', halign=Gtk.Align.START)
        hbox.add(self.repo_label)
        self.branch_label = Gtk.Label(halign=Gtk.Align.END)
        hbox.add(self.branch_label)
        self.pack_start(hbox, False, False, 0)

        self.changes_part = Gtk.VBox()
        self.add(self.changes_part)
        stage_box = Gtk.HBox()
        self.changes_part.add(stage_box)
        self.stage_view = status_icon_view()
        stage_scroll = Gtk.ScrolledWindow()
        stage_scroll.add(self.stage_view)
        stage_box.add(stage_scroll)
        stage_box.pack_start(Gtk.Label(label='Stage', angle=90), False, False, 0)

        self.changes_part.pack_start(icon_and_label('go-down', "git reset HEAD <file>"),
                        False, False, 0)
        self.changes_part.pack_start(icon_and_label('go-up', "git add <file>"),
                        False, False, 0)

        wd_box = Gtk.HBox()
        self.changes_part.add(wd_box)
        self.wd_view = status_icon_view()
        wd_scroll = Gtk.ScrolledWindow()
        wd_scroll.add(self.wd_view)
        wd_box.add(wd_scroll)
        wd_box.pack_start(Gtk.Label(label='CWD', angle=90), False, False, 0)

        self.changes_part.pack_start(icon_and_label('go-down', "git checkout -- <file>"),
                        False, False, 0)

        self.commit_part = Gtk.VBox()
        self.pack_start(self.commit_part, False, False, 0)
        self.commit_info = Gtk.Label()
        self.commit_part.pack_start(self.commit_info, False, False, 0)
        self.commit_msg = Gtk.Label(ellipsize=Pango.EllipsizeMode.END)
        self.commit_part.pack_start(self.commit_msg, False, False, 0)

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
        if data['branch']:
            self.branch_label.set_text(data['branch'])
        else:
            self.branch_label.set_text('[no branch]')
        if data['stage'] or data['wd']:
            self.stage_view.set_model(self.make_list(data['stage']))
            self.wd_view.set_model(self.make_list(data['wd']))
            self.changes_part.show()
            self.commit_part.hide()
            self.set_vexpand(True)
        else:
            self.changes_part.hide()
            self.commit_part.show()
            self.set_vexpand(False)
            commit = data['commit']
            self.commit_info.set_markup('Last commit: <b>{}</b> · {}'.format(
                _escape(commit['shorthash']), _escape(commit['reltime'])
            ))
            self.commit_msg.set_text(commit['message'])


    def _get_data_in_thread(self, pwd):
        res = check_repo(pwd)
        GLib.idle_add(self._finish_update, res)

    def prompt(self, window):
        Thread(target=self._get_data_in_thread, args=(window.cwd,), daemon=True).start()
