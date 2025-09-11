from importlib.metadata import version, PackageNotFoundError

try:
    _vnum = version('pytaskrunner')
    version = f'v{_vnum}'
except PackageNotFoundError:
    version = 'v0.0.0'
