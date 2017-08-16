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
        max_name_length = max(len(p['name']) for p in info)
        for panel in info:
            if panel['enabled']:
                status = 'visible' if panel['visible'] else 'hiding'
            else:
                status = 'disabled'
            dashes = '-' * (max_name_length + 1 - len(panel['name']))
            print(' ', panel['name'], dashes, status)

    elif subcmd.startswith('.'):
        # Panel command, e.g. 'sj .git off'
        panel_name = subcmd[1:]
        panel_cmd = sys.argv[2]
        if panel_cmd == 'on':
            proxy_call('enable_panel', panel_name)
        elif panel_cmd == 'off':
            proxy_call('disable_panel', panel_name)

    else:
        sys.exit('Unknown command: sj %s' % subcmd)
