activate_this = 'd:/GitHub/mcard/venv/Scripts/activate_this.py'
exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))

import sys

#Expand Python classed path with my own app's path
sys.path.insert(0, "d:/GitHub/mcard")

from manage import app
#Put logging code (and imports) here...

#Initialize WSGI app object
application = app
