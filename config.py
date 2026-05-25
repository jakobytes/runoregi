import os
from contextlib import contextmanager
from operator import itemgetter
import pymysql
import re
import warnings


# Build MySQL connection parameters
MYSQL_PARAMS = {
    'host'     : os.getenv('DB_HOST'),
    'port'     : int(os.getenv('DB_PORT', 3306)),
    'user'     : os.getenv('DB_USER'),
    'password' : os.getenv('DB_PASS'),
    'database' : os.getenv('DB_NAME'),
}

# Add socket if DB_SOCKET is set (for non-standard setups)
if os.getenv('DB_SOCKET'):
    MYSQL_PARAMS['unix_socket'] = os.getenv('DB_SOCKET')

# Add SSL if DB_SSL is set
if os.getenv('DB_SSL'):
    # Disable SSL verification if DB_SSL_VERIFY is set to '0'
    if os.getenv('DB_SSL_VERIFY') == '0':
        MYSQL_PARAMS['ssl'] = {'verify_server_cert': False}
    else:
        MYSQL_PARAMS['ssl'] = {'ca': os.getenv('DB_SSL_CA', '/etc/ssl/certs/ca-certificates.crt')}

VISUALIZATIONS_URL = os.getenv('VISUALIZATIONS_URL')

SEARCH_LIMIT = 1000
ENABLE_LOGGING_TO_DB = not not os.getenv('DB_LOGGING')
ENABLE_PROXY = not not os.getenv('PROXY')
LOGGING_TABLE_NAME = 'runoregi_log'

BANNED_CRAWLERS = re.compile('Bytespider')
BANNED_CRAWLER_RESPONSE = '''
This site is currently not serving requests from your crawler.
Please consult robots.txt and conform to it.
'''

# Info on whether the tables were found in the DB. Set on startup.
TABLES = {
  'collectors'     : False,
  'p_clust'        : False,
  'p_clust_freq'   : False,
  'p_col'          : False,
  'p_dupl'         : False,
  'p_pl'           : False,
  'p_sim'          : False,
  'p_year'         : False,
  'places'         : False,
  'p_typ'          : False,
  'poems'          : False,
  'raw_meta'       : False,
  'refs'           : False,
  'runoregi_pages' : False,
  'types'          : False,
  'v_clust'        : False,
  'v_clust_freq'   : False,
  'v_clusterings'  : False,
  'v_sim'          : False,
  'verse_poem'     : False,
  'verses'         : False,
  'verses_cl'      : False,
  'verses_translated': False,
  'word_analysis'    : False,
  'word_analysis_1'  : False,
}

# Tables without which Runoregi can't work.
ESSENTIAL_TABLES = { 'poems', 'verse_poem', 'verses' }

# Error messages to print if a table is not found.
TABLE_ERRMSG = {
  'collectors'     : 'The collector information will not be available.',
  'p_clust'        : 'The poem clustering will not be available.',
  'p_clust_freq'   : 'The poem clustering will not be available.',
  'p_col'          : 'The collector information will not be available.',
  'p_dupl'         : 'The poem duplicate information will not be available.',
  'p_pl'           : 'The place information will not be available.',
  'p_sim'          : 'The poem similarities will not be available.',
  'p_year'         : 'The year information will not be available.',
  'places'         : 'The place information will not be available.',
  'p_typ'          : 'The type indices will not be available.',
  'poems'          : 'Terminating.',
  'raw_meta'       : 'The unstructured metadata will not be available.',
  'refs'           : 'The footnotes will not be available.',
  'runoregi_pages' : 'Some Runoregi pages (especially the starting page)'
                     ' might be missing content.',
  'types'          : 'The type indices will not be available.',
  'v_clust'        : 'The verse clustering and passage search will not be available.',
  'v_clust_freq'   : 'The verse clustering and passage search will not be available.',
  'v_clusterings'  : 'The verse clustering and passage search will not be available.',
  'v_sim'          : 'The neighboring clusters will not be available.',
  'verse_poem'     : 'Terminating.',
  'verses'         : 'Terminating.',
  'verses_cl'      : 'The side-by-side comparisons will not be available.',
  'verses_translated': 'The English translations will not be available.',
  'word_analysis'    : 'The word analysis will not be available.',
  'word_analysis_1'  : 'The word analysis will not be available.',
}


pool = None


@contextmanager
def get_db():
    conn = pool.connection()
    try:
        yield conn.cursor()
    finally:
        conn.close()


@contextmanager
def get_conn():
    conn = pool.connection()
    try:
        yield conn
    finally:
        conn.close()


def setup_tables():
    from dbutils.pooled_db import PooledDB
    global pool
    try:
        with pymysql.connect(**MYSQL_PARAMS).cursor() as db:
            db.execute('SHOW TABLES;')
            db_tables = set(map(itemgetter(0), db.fetchall()))
            for tbl in TABLES:
                TABLES[tbl] = tbl in db_tables
    except pymysql.err.OperationalError:
        raise RuntimeError('Cannot connect to the database. Terminating.')

    pool = PooledDB(pymysql, mincached=2, maxcached=5, maxconnections=20,
                    **MYSQL_PARAMS)

    # print warnings or throw errors about non-existing tables
    for tbl in TABLES:
        if not TABLES[tbl]:
            if tbl in ESSENTIAL_TABLES:
                raise RuntimeError('Fatal: table `{}` table not found. {}'\
                                   .format(tbl, TABLE_ERRMSG[tbl]))
            else:
                warnings.warn('Table `{}` not found. {}'\
                              .format(tbl, TABLE_ERRMSG[tbl]))

def check_maintenance():
    with pymysql.connect(**MYSQL_PARAMS).cursor() as db:
        db.execute('SELECT SUM(ready != 1) FROM dbmeta;')
        result = db.fetchall()
        return result[0][0] > 0

