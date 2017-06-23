#!/usr/bin/python3
import dbus
import os
from sys import argv

bus = dbus.SessionBus()
helloservice = bus.get_object(os.environ['SJ_DBUS_NAME'],
                              '/io/github/takluyver/sj')
if argv[1] == '--discover':
    args = helloservice.get_dbus_method('get_update_args',
                                        'io.github.takluyver.sj')()
    print(argv[0], args)
else:
    update = helloservice.get_dbus_method('update', 'io.github.takluyver.sj')
    values = dict(zip(argv[1::2], argv[2::2]))
    update(values)
