#from dez.version import __version__
from setuptools import setup

setup(
    name='dez',
    version='0.10.10.37',
    author='Mario Balibrera',
    author_email='mario.balibrera@gmail.com',
    license='MIT License',
    description='A set of pyevent-based network services',
    long_description='The dez library includes an asynchronous server benchmarking toolset; advanced, inotify-based static caching; XML and JSON stream parsing; Stomp, OP, HTTP, and WebSocket servers; and WebSocketProxy, which enables web application deployment on existing, unmodified TCP servers without straying from the HTML5 spec. In addition, dez offers a highly sophisticated API for implementing custom protocols, as well as a controller class that simplifies the creation of applications that require multiple servers to run in the same process.',
    packages=[
        'dez',
        'dez.http',
        'dez.http.server',
        'dez.http.client',
        'dez.http.proxy',
        'dez.stomp',
        'dez.stomp.server',
        'dez.op',
        'dez.op.server',
        'dez.network',
        'dez.samples'
    ],
    zip_safe = False,
    install_requires = [
        "rel >= 0.4.9.20",
        "psutil >= 5.9.1",
        "python-magic >= 0.4.11"
    ],
    entry_points = '''
        [console_scripts]
        dez_test = dez.samples.test:main
        dbench = dez.samples.http_load_test:main
        dez_websocket_proxy = dez.network:startwebsocketproxy
        dez_reverse_proxy = dez.http.reverseproxy:startreverseproxy
        [paste.server_runner]
        wsgi_server = dez.http.application:serve_wsgi_application
    ''',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
