from .base import BaseWrapper
import json
from .topic import Topic
from .document import Document
from urllib import quote

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
        return self._get('get_relevance/', limit=limit)['result']

    def upload_documents(self, documents):
        json_data = json.dumps(documents)
        return self._post_data('upload_documents/', json_data,
                               'application/json')
    
    def docvectors(self):
        return self._get('docvectors/')
        
    def doc_ids(self):
        return self._get('docs/')['ids']
    
    def doc(self,id):
        """This probably needs to have a document object added.
            The magic parameter in quote tells it to escape slashes correctly
        """
        return Document(self._get('docs/' + quote(id,'') + "/"))
        
    def topics(self):
        return [Topic(topic_dict) for topic_dict in self._get('topics/')['topics']]
        
    def recalculate_topics(self):
        return self._get('topics/.calculate/')
        
    def create_topic(self,name,role,color,terms):
        """Posting appears to be broken here too"""
        return self._post('topics/create/',name=name,role=role,color=color,terms=terms)
        
    def delete_topic(self,topic_id):
        return self._post('topics/.delete/',topic_id = topic_id)
        
    def get_topic(self,id):
        return Topic(self._get('topics/' + id + '/'))
        
    def get_topic_stats(self):
        return self._get('topic_stats/')
        
    def get_topic_histograms(self,bins=10):
        return self._get('topic_histograms/')
        
    def get_topic_correlation(self,text=""):
        return self._get('topic_correlation/',text=text)
        
    def get_batch_topic_correlation(self,texts):
        return self._get('batch_topic_correlation/',texts=texts)
        
    def all_document_correlations(self):
        return self._get('all_document_correlations/')
        
    def timeline(self,bins=10):
        return self._get('timeline/')
        
    def term_search(self,text="",limit=10,domain=False):
        """This seems broken as well"""
        return self._get('term_search/',text=text,limit=limit,domain=domain)
        
    def search(self,query,style="text",limit = 10, near = None, start_at = 0):
        if style == "terms":
            return self._get('search/',terms=query,limit=limit,near=near,start_at=start_at)
        elif style == "topic":
            return self._get('search/',topic=query,limit=limit,near=near,start_at=start_at)
        else:
            return self._get('search/',text=query,limit=limit,near=near,start_at=start_at)
