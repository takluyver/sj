import dbus
import os
import sys

bus = dbus.SessionBus()
sj_proxy = bus.get_object(os.environ['SJ_DBUS_NAME'],
                          '/io/github/takluyver/sj')
def proxy_call(method_name, *args):
    method = sj_proxy.get_dbus_method(method_name)
    return method(*args)

def main():
    if sys.argv[1] == 'version':
        print('sj version {} connected at D-Bus name {}'.format(
            proxy_call('get_version'), os.environ['SJ_DBUS_NAME']
        ))
