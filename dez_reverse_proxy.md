# Introduction #

The proxy listens on the specified port (80 by default) and routes domain names to host:port tuples.


# Details #

You run dez\_reverse\_proxy on the command line, like this:
```
$ dez_reverse_proxy -h
Usage: dez_reverse_proxy [CONFIG]

Options:
  -h, --help            show this help message and exit
  -v, --verbose         log proxy activity
  -p PORT, --port=PORT  public-facing port (default: 80)
```

The mandatory argument is the name of your config file. A dez\_reverse\_proxy config file is just a series of lines directing dez to forward traffic to different places depending on the Host header. It looks like this:
```
somehostname->adifferenthostname:12345
findsomething.mydomain.com->google.com:80
localhost->localhost:8888
sub.localhost->localhost:9999
```