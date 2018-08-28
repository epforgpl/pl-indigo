from indigo.settings import *

INSTALLED_APPS = ('indigo_pl',) + INSTALLED_APPS

# This section is copied over from the main settings file, so that when Dockerizing the PL app
# I can use 'sed' to replace 'postgres://indigo:indigo@localhost:5432/indigo' with the right
# settings.
import dj_database_url
db_config = dj_database_url.config(default='postgres://indigo:indigo@localhost:5432/indigo')
db_config['ATOMIC_REQUESTS'] = False
DATABASES = {
    'default': db_config,
}
