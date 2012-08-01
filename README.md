Luminoso Client API - python bindings
=====================================

A complete example

```python
from luminoso_api import Account
from luminoso_api.utils import get_session

# Get a python requests session for a particular Luminoso user
# - prompt for a password
s = get_session(username='jane')

# Get a list of accounts (in Account objects) accessible to the user
accts = Account.accessible(s)

# Pick an account
acct = accts[0]

# Get a dictionary mapping database names to Database objects
dbs = acct.databases()

# Pick a Database arbitrarily
db = dbs.values()[0]

# Extract relevant terms
terms = db.get_relevance()

```
