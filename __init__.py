from collections import namedtuple
from .utf import UTFFile
from .inifile import INIFile, IniSection
from .fldll import FLDll
from .utils import *

SettingsTPL = namedtuple('Settings', [
	'dll',
	'tex',
	'fl',
	'universe',
	'news'
])

settings = SettingsTPL(
	dll='workfiles/Manhattan.dll',
	tex='workfiles/newsvendor.txm',
	fl='workfiles/freelancer.ini',
	universe='workfiles/universe.ini',
	news='workfiles/news.ini',
)