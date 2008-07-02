from dez.http.application import HTTPApplication

def main(**kwargs):
    a = HTTPApplication("", kwargs['port'])
    a.add_proxy_rule('/', kwargs['domain'], 80)
    a.add_static_rule('/static/', '.')
    a.start()