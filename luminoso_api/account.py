
from .constants import URL_BASE

class Account(object):
    """An object encapsulating a billing account on Luminoso's servers"""
    def __init__(self, acct_name, session):
        """Construct a wrapper around a particular account name
           NOTE: Construction does not validate the existence or accessibility
           of the account"""

        self.acct_name = acct_name
        self.session = session
        self.url_base = URL_BASE + '/' + acct_name

    def __unicode__(self):
        return u'Account("%s")' % self.acct_name

    def __str__(self):
        return str(unicode(self))

    def __repr__(self):
        return str(self)

    @classmethod
    def accessible(cls, session):
        accounts = session.get(URL_BASE + '/.accounts/').json
        return [Account(acct, session) for acct in accounts['accounts']]
