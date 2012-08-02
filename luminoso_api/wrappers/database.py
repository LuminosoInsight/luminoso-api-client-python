
from .base import BaseWrapper
import json

class Database(BaseWrapper):
    """An object encapsulating a document database (project) on Luminoso's
       servers"""
    def __init__(self, path, db_name, session, meta=None):
        super(Database, self).__init__(path=path,
                                       session=session)
        self.db_name = db_name

        if meta is None:
            meta = self._get('meta/')

        self._meta = meta

    def __unicode__(self):
        return u'Database("%s", "%s")' % (self.api_path, self.db_name)

    def get_relevance(self, limit=10):
        return self._get('get_relevance/', limit=limit)

    def upload_documents(self, documents):
        json_data = json.dumps(documents)
        return self._post_data('upload_documents/', json_data,
                               'application/json')
