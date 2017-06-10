import dbus
import os

bus = dbus.SessionBus()
helloservice = bus.get_object(os.environ['SJ_DBUS_NAME'],
                              '/io/github/takluyver/sj')
update = helloservice.get_dbus_method('update', 'io.github.takluyver.sj')
update(os.getcwd(), '')
