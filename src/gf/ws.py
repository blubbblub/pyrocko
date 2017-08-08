# http://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------
from future import standard_library
standard_library.install_aliases()  # noqa


import time
import urllib.request
import urllib.parse
import urllib.error

import logging

from pyrocko import util

logger = logging.getLogger('pyrocko.gf.ws')

g_url = '%(site)s/gfws/%(service)s/%(majorversion)i/%(method)s'
g_url_static = '%(site)s/gfws/%(service)s'

g_site_abbr = {
    'localhost': 'http://localhost:8080',
    'kinherd': 'http://kinherd.org:8080'}

g_default_site = 'localhost'


def sdatetime(t):
    return util.time_to_str(t, format='%Y-%m-%dT%H:%M:%S')


class EmptyResult(Exception):
    def __init__(self, url):
        Exception.__init__(self)
        self._url = url

    def __str__(self):
        return 'No results for request %s' % self._url


class RequestEntityTooLarge(Exception):
    def __init__(self, url):
        Exception.__init__(self)
        self._url = url

    def __str__(self):
        return 'Request entity too large: %s' % self._url


class InvalidRequest(Exception):
    pass


def _request(url, post=False, **kwargs):
    url_values = urllib.parse.urlencode(kwargs)
    if url_values:
        url += '?' + url_values
    logger.debug('Accessing URL %s' % url)

    req = urllib.request.Request(url)
    if post:
        logger.debug('POST data: \n%s' % post)
        req.add_data(post)

    req.add_header('Accept', '*/*')

    try:
        resp = urllib.request.urlopen(req)
        if resp.getcode() == 204:
            raise EmptyResult(url)
        return resp

    except urllib.error.HTTPError as e:
        if e.code == 413:
            raise RequestEntityTooLarge(url)
        else:
            raise


def fillurl(url, site, service, majorversion, method='query'):
    return url % dict(
        site=g_site_abbr.get(site, site),
        service=service,
        majorversion=majorversion,
        method=method)


def static(url=g_url_static, site=g_default_site, majorversion=1, **kwargs):

    url = fillurl(url, site, 'static', majorversion)
    return _request(url, **kwargs)


def ujoin(*args):
    return '/'.join(args)


class DownloadError(Exception):
    pass


class PathExists(DownloadError):
    pass


class Incomplete(DownloadError):
    pass


def rget(url, path, force=False, method='download', stats=None,
         status_callback=None, entries_wanted=None):

    return util._download(
        url, path,
        force=force,
        method=method,
        status_callback=status_callback,
        entries_wanted=entries_wanted,
        recursive=True)


def download_gf_store(url=g_url_static, site=g_default_site, majorversion=1,
                      store_id=None, force=False, quiet=False):

    url = fillurl(url, site, 'static', majorversion)

    stores_url = ujoin(url, 'stores')

    tlast = [time.time()]

    if not quiet:
        def status_callback(i, n):
            tnow = time.time()
            if (tnow - tlast[0]) > 5 or i == n:
                print('%s / %s [%.1f%%]' % (
                    util.human_bytesize(i), util.human_bytesize(n), i*100.0/n))

                tlast[0] = tnow
    else:
        def status_callback(i, n):
            pass

    wanted = ['config', 'extra/', 'index', 'phases/', 'traces/']

    try:
        if store_id is None:
            print(static(url=stores_url+'/', format='text').read())

        else:
            store_url = ujoin(stores_url, store_id)
            stotal = rget(
                store_url, store_id, force=force, method='calcsize',
                entries_wanted=wanted)

            rget(
                store_url, store_id, force=force, stats=[0, stotal],
                status_callback=status_callback, entries_wanted=wanted)

    except Exception as e:
        raise DownloadError('download failed. Original error was: %s, %s' % (
            type(e).__name__, e))


def seismosizer(url=g_url, site=g_default_site, majorversion=1,
                request=None):

    url = fillurl(url, site, 'seismosizer', majorversion)

    from pyrocko.gf import meta

    return meta.load(stream=_request(url, post=urllib.parse.urlencode(
        {'request': request.dump()})))
