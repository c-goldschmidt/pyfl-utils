from collections import namedtuple

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
