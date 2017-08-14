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
    subcmd = sys.argv[1]
    if subcmd == 'version':
        print('sj version {} connected at D-Bus name {}'.format(
            proxy_call('get_version'), os.environ['SJ_DBUS_NAME']
        ))
    elif subcmd == 'panels':
        print('Loaded panels:')
        info = proxy_call('get_panels_status')
        max_name_length = max(len(r[0]) for r in info)
        for name, enabled, visible in info:
            if enabled:
                status = 'visible' if visible else 'hiding'
            else:
                status = 'disabled'
            dashes = '-' * (max_name_length + 2 - len(name))
            print(' ', name, dashes, status)
