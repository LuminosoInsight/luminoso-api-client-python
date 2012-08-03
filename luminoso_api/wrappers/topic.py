from .base import BaseWrapper

class Topic(BaseWrapper):
    def __init__(self, path, topic_id, session, topic_dict=None):
        """Create a Topic object from a returned dictionary"""
        super(Topic, self).__init__(path=path,
                                    session=session)
        if topic_dict is None:
            topic_dict = self._get('')
        self._dict = topic_dict

    def __getattr__(self, attr):
        if attr in self._dict:
            return self._dict.get(attr, None)
        raise AttributeError, ("'%s' object has no attribute '%s'" %
                               (self.__class__.__name__, attr))

    # TODO: add a __repr__ to show topic info
