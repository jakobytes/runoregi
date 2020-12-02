import os


MYSQL_PARAMS = {
    'host' : os.getenv('DB_HOST'),
    'port' : int(os.getenv('DB_PORT')),
    'user' : os.getenv('DB_USER'),
    'password' : os.getenv('DB_PASS'),
    'database' : os.getenv('DB_NAME')
}

BASE_URL = 'http://runoregi.rahtiapp.fi'
SHINY_URL = 'https://filter-shiny.rahtiapp.fi'

