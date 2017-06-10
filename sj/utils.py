import os.path

_home = os.path.expanduser('~')
def compress_user(path):
    if path.startswith(_home):
        return '~' + path[len(_home):]
    return path
