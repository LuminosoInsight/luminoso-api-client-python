class Document(object):

    def __init__(self,doc_dict):
        """Creates a Document object from a response dictionary"""
        self._dict = doc_dict

    def __getattr__(self, attr):
        if attr in self._dict:
            return self._dict.get(attr, None)
        raise AttributeError, ("'%s' object has no attribute '%s'" %
                               (self.__class__.__name__, attr))

    def __repr__(self):
        return '<Document: %s (%s)>' % (self._dict['title'], self._dict['_id'])

    def show_document(self):
        dict_copy = self._dict.copy()
        dict_copy[u'fragments'] = (u'<list of %d term triples>' % 
                                   len(dict_copy['fragments']))
        dict_copy[u'terms'] = (u'<list of %d term triples>' % 
                               len(dict_copy['terms']))
        dict_copy[u'tokens'] = (u'<list of %d token triples>' % 
                                len(dict_copy['tokens']))
        dict_copy[u'termlist'] = (u'<list of %d terms>' % 
                                  len(dict_copy['termlist']))
        del dict_copy['source']['meta']
        return dict_copy
