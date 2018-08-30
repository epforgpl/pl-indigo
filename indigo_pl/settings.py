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

# Having it set to true resulted in 'database connection isn't set to UTC' AssertionError in Django.
# See https://stackoverflow.com/questions/38807296 for more. I couldn't find a way to update 
# the pg_timezone_names view in Postgres responsible for it. We're not really using timestamps
# in Indigo so this 'hack' seems fine.
USE_TZ = False
