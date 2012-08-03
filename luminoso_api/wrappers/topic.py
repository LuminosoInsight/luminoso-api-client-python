from .base import BaseWrapper
import json

class Topic(BaseWrapper):
    def __init__(self, path, topic_id, session, topic_dict=None):
        """Create a Topic object from a returned dictionary"""
        super(Topic, self).__init__(path=path,
                                    session=session)
        if topic_dict is None:
            topic_dict = self._get('')['topic']
        self._dict = topic_dict

    def __getattr__(self, attr):
        if hasattr(self, '_dict') and attr in self._dict:
            return self._dict[attr]
        raise AttributeError, ("'%s' object has no attribute '%s'" %
                               (self.__class__.__name__, attr))

    def __setattr__(self, attr, value):
        if hasattr(self, '_dict') and attr in self._dict:
            raise AttributeError, ("use 'change_topic()' to change attributes "
                                   "on the topic")
        else:
            super(Topic, self).__setattr__(attr, value)

    # TODO: add a __repr__ to show topic info

    def show_topic(self):
        dict_copy = dict(self._dict)
        dict_copy['vector'] = '...'
        return dict_copy

    def delete_topic(self):
        # not implementable at this level until the flask/DELETE bug is fixed?
        raise NotImplementedError, ("in the meantime, use delete_topic() "
                                    "on the database")

    def change_topic(self, attr, value):
        """
        Used to change attributes of a topic. Be warned, there is no error
        correction here, so if you set something incorrectly (an invalid
        color, etc.), then it's up to you to fix it. This makes no changes
        to the database; use "save_topic()" to save it.
        """
        if attr not in self._dict:
            raise AttributeError, ("topics have no '%s' attribute" % attr)
        elif attr in ['_id', 'vector']:
            raise AttributeError, ("attribute '%s' is immutable" % attr)
        self._dict[attr] = value

    def save_topic(self):
        """
        Used to store changes to the database.
        """
        dict_copy = dict(self._dict)
        dict_copy['weighted_terms'] = json.dumps(dict_copy['weighted_terms'])
        return self._put('', **dict_copy)
