
from ..constants import URL_BASE

class BaseWrapper(object):
    """A wrapper implementing a suite methods common to all in luminoso_api"""
    def __init__(self, path, session):
        """Construct a wrapper around a particular path from the global URL_BASE
           for a particular session.

           NOTE: Construction does not validate the existance or accessibility
           of the API object in question"""

        self.api_path = path
        self.url_base = URL_BASE + '/' + self.api_path + '/'
        self._session = session

    def __unicode__(self):
        return u'BaseWrapper("%s")' % self.api_path

    def __str__(self):
        return str(unicode(self))

    def __repr__(self):
        return str(self)

    def _get(self, path, **params):
        return self._session.get(self.url_base + path, params=params).json

    def _post(self, path, **params):
        return self._session.post(self.url_base + path, data=params).json

    def _put(self, path, data, content_type, **params):
        return self._session.put(self.url_base + path,
                                 params=params,
                                 data=data,
                                 headers={'Content-Type': content_type}).json

    def _patch(self, path, data, content_type, **params):
        return self._session.patch(self.url_base + path,
                                   params=params,
                                   data=data,
                                   headers={'Content-Type': content_type}).json

    def _delete(self, path, **params):
        return self._session.delete(self.url_base + path, params=params).json

