import sys
if sys.version_info < (3, 0) and sys.getdefaultencoding() == 'ascii':
    reload(sys)
    sys.setdefaultencoding('utf-8')
import rel
rel.override()

__version__ = "0.10.9.50"
