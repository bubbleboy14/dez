"""
Select a JSON library from any of several known libraries.
"""

try:
    # first try regular json,
    # but we need to import it weirdly
    # because this module is also called json
    import imp, sys
    f, pathname, desc = imp.find_module("json", sys.path[1:])
    js = imp.load_module("native_json", f, pathname, desc)
    f and f.close()
    encode = js.dumps
    decode = js.loads
except ImportError:
    try:
        import cjson
        encode = cjson.encode
        decode = cjson.decode
    except ImportError:
        try:
            import simplejson
            encode = simplejson.dumps
            decode = simplejson.loads
        except ImportError:
            try:
                import demjson
                encode = demjson.encode
                decode = demjson.decode
            except ImportError:
                raise ImportError, "could not load one of: json, cjson, simplejson, demjson"
