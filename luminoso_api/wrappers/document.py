class Document(object):

    def __init__(self,doc_dict):
        """Creates a Document object from a response dictionary"""
        self._dict = doc_dict

    def __getattr__(self, attr):
        if attr in self._dict:
            return self._dict.get(attr, None)
        raise AttributeError, ("'%s' object has no attribute '%s'" %
                               (self.__class__.__name__, attr))

    # TODO: add a __repr__ to show topic info?
