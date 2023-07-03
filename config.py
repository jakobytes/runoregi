import os


MYSQL_PARAMS = {
    'host' : os.getenv('DB_HOST'),
    'port' : int(os.getenv('DB_PORT')),
    'user' : os.getenv('DB_USER'),
    'password' : os.getenv('DB_PASS'),
    'database' : os.getenv('DB_NAME')
}

VISUALIZATIONS_URL = os.getenv('VISUALIZATIONS_URL')

SEARCH_LIMIT = 1000
ENABLE_LOGGING_TO_DB = not not os.getenv('DB_LOGGING')
LOGGING_TABLE_NAME = 'runoregi_log'
