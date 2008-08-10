from setuptools import setup
setup(
    name='dez',
    version='0.3.3',
    author='Michael Carter',
    author_email='mario.balibrera@gmail.com',
    download_url='http://code.google.com/p/dez/downloads/list',
    license='MIT License',
    description='A set of pyevent-based network services',
    long_description='',
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
        "rel >= 0.2.2",
        "demjson"
    ],
    entry_points = '''
        [console_scripts]
        dez_test = dez.samples.test:main
        dbench = dez.samples.http_load_test:main
        [paste.server_runner]
        wsgi_server = dez.http.application:serve_wsgi_application
    ''',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)