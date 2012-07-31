
from .base import BaseWrapper
from .database import Database
from ..constants import URL_BASE

class Account(BaseWrapper):
    """An object encapsulating a billing account on Luminoso's servers"""
    def __init__(self, acct_name, session):
        """Construct a wrapper around a particular account name
           NOTE: Construction does not validate the existence or accessibility
           of the account"""
        super(Account, self).__init__(path=acct_name, session=session)

        self.acct_name = acct_name

    def __unicode__(self):
        return u'Account("%s")' % self.acct_name

    @classmethod
    def accessible(cls, session):
        accounts = session.get(URL_BASE + '/.accounts/').json
        return [Account(acct, session) for acct in accounts['accounts']]

    def databases(self):
        db_table = self._get('.list_dbs/')
        dbs = {}
        for db_name, db_meta in db_table.items():
            path = self.api_path + '/' + db_name
            dbs[db_name]=Database(path, db_name, meta=db_meta,
                                  session=self._session)
        return dbs

    def create_project(self, db_name):
        resp = self._post_raw('%s/create_project/' % db_name)
        if resp == 'Database %s created' % db_name:
            return None
        return resp
