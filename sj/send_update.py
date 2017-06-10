#!/usr/bin/python3
import dbus
import os
import re
from sys import argv

bus = dbus.SessionBus()
helloservice = bus.get_object(os.environ['SJ_DBUS_NAME'],
                              '/io/github/takluyver/sj')
update = helloservice.get_dbus_method('update', 'io.github.takluyver.sj')
histno = 0
last_cmd = ''
if len(argv) > 1:
    m = re.match(r"hist1=\s*(\d+)\s+(.+)", argv[1])
    if m:
        histno = int(m.group(1))
        last_cmd = m.group(2)
update(os.getcwd(), histno, last_cmd)
