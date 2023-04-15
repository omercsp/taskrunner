import pkg_resources

try:
    _vnum = pkg_resources.get_distribution('pytaskrunner').version
    version = f'v{_vnum}'
except pkg_resources.DistributionNotFound:
    version = 'v0.0.0'
