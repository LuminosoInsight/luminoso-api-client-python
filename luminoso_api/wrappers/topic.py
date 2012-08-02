class Topic(object):

    def __init__(self,topic_dict):
        """Create a Topic object from a returned dictionary"""
        self.dict = topic_dict
        self.id = self.dict['_id']
        self.color = self.dict['color']
        self.weighted_terms = self.dict['weighted_terms']
        self.role = self.dict['role']
        self.name = self.dict['name']
        self.vector = self.dict['vector']