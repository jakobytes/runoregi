import os
from contextlib import contextmanager
import duckdb
import re
import threading
import warnings


# Location of the parquet files: an HTTP(S) URL or a local directory.
# Each table is read from <PARQUET_BASE>/<table>.parquet
PARQUET_BASE = os.getenv('PARQUET_BASE', 'https://a3s.fi/filter-data/')
# Where DuckDB looks for extensions (httpfs is preinstalled there in the image)
DUCKDB_EXTENSION_DIRECTORY = os.getenv('DUCKDB_EXTENSION_DIRECTORY')
# DuckDB sizes memory and threads by the host, not the container: cap them
DUCKDB_MEMORY_LIMIT = os.getenv('DUCKDB_MEMORY_LIMIT')
DUCKDB_THREADS = os.getenv('DUCKDB_THREADS')

VISUALIZATIONS_URL = os.getenv('VISUALIZATIONS_URL')

SEARCH_LIMIT = 1000
# Logging writes to the database; not available with parquet.
ENABLE_LOGGING_TO_DB = False
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
}


# Tables read by queries but not checked in TABLES
EXTRA_TABLES = ['dbmeta', 'place_stats']

con = None
_local = threading.local()


class Cursor:
    '''DB-API-like cursor on DuckDB accepting the pymysql query style:
       `%s` placeholders, with tuple/list arguments expanded for `IN %s`.'''

    def __init__(self, cur):
        self._cur = cur

    @staticmethod
    def _translate(query, args):
        if args is None:
            return query, []
        parts = query.split('%s')
        if len(parts) - 1 != len(args):
            raise ValueError('Expected {} query arguments, got {}'\
                             .format(len(parts) - 1, len(args)))
        sql, params = [parts[0]], []
        for arg, part in zip(args, parts[1:]):
            if isinstance(arg, (tuple, list)):
                sql.append('(' + ', '.join(['?'] * len(arg)) + ')')
                params.extend(arg)
            else:
                sql.append('?')
                params.append(arg)
            sql.append(part)
        return ''.join(sql), params

    def execute(self, query, args=None):
        sql, params = self._translate(query, args)
        self._cur.execute(sql, params)

    def fetchall(self):
        return self._cur.fetchall()

    def fetchone(self):
        return self._cur.fetchone()


def _cursor():
    # DuckDB connections are not thread-safe: one cursor per thread
    if getattr(_local, 'cur', None) is None:
        _local.cur = Cursor(con.cursor())
    return _local.cur


@contextmanager
def get_db():
    yield _cursor()


def _parquet_path(tbl):
    return '{}/{}.parquet'.format(PARQUET_BASE.rstrip('/'), tbl)


def setup_tables():
    global con
    con = duckdb.connect()
    if DUCKDB_EXTENSION_DIRECTORY:
        con.execute("SET extension_directory = '{}'".format(DUCKDB_EXTENSION_DIRECTORY))
    if DUCKDB_MEMORY_LIMIT:
        con.execute("SET memory_limit = '{}'".format(DUCKDB_MEMORY_LIMIT))
    if DUCKDB_THREADS:
        con.execute('SET threads = {:d}'.format(int(DUCKDB_THREADS)))
    if PARQUET_BASE.startswith(('http://', 'https://')):
        con.execute('INSTALL httpfs; LOAD httpfs;')
    for tbl in list(TABLES) + EXTRA_TABLES:
        try:
            con.execute('CREATE VIEW "{}" AS SELECT * FROM read_parquet(\'{}\')'\
                        .format(tbl, _parquet_path(tbl)))
            if tbl in TABLES:
                TABLES[tbl] = True
        except duckdb.Error:
            pass

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
    with get_db() as db:
        try:
            db.execute('SELECT SUM(ready != 1) FROM dbmeta;')
        except duckdb.Error:
            return False
        result = db.fetchall()
        return bool(result[0][0])

