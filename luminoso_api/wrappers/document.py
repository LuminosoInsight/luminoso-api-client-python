class Document(object):

    def __init__(self,doc_dict):
        """Creates a Document object from a response dictionary"""
        self.dict = doc_dict
        self.id = self.dict['_id']
        self.fields = self.dict['fields']
        self.fragments = self.dict['fragments']
        self.handling_flags = self.dict['handling_flags']
        self.reader = self.dict['reader']
        self.source = self.dict['source']
        self.subsets = self.dict['subsets']
        self.tags = self.dict['tags']
        self.terms = self.dict['terms']
        self.text = self.dict['text']
        self.title = self.dict['title']
        self.tokens = self.dict['tokens']