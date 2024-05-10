from flask import request
from socket import gethostbyname, gethostname
import pymysql
import time

import config

# unused
def get_remote_addr():
    if config.ENABLE_PROXY and request.headers.getlist('X-Forwarded-For'):
        return request.headers.getlist('X-Forwarded-For')[0]
    else:
        return request.remote_addr

def create_logging_table(db):
    db.execute(
        'CREATE TABLE {}('
        '  log_id INTEGER NOT NULL AUTO_INCREMENT,'
        '  level ENUM("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") DEFAULT "INFO",'
        '  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,'
        '  hostname VARCHAR(100) DEFAULT NULL,'
        '  msg VARCHAR(2000) DEFAULT NULL,'
        '  user_agent VARCHAR(1000) DEFAULT NULL,'
        '  crawler varchar(50) DEFAULT NULL,'
        '  PRIMARY KEY(log_id), '
        '  INDEX (level), '
        '  INDEX (timestamp), '
        '  INDEX (hostname), '
        '  INDEX (crawler) '
        ');'.format(config.LOGGING_TABLE_NAME))

def log(level, msg):
    if config.ENABLE_LOGGING_TO_DB:
        with pymysql.connect(**config.MYSQL_PARAMS) as db_con:
            with db_con.cursor() as db:
                db.execute('SHOW TABLES LIKE %s;', (config.LOGGING_TABLE_NAME,))
                if len(list(db.fetchall())) <= 0:
                    create_logging_table(db)
                if len(msg) > 2000:
                    msg = msg[:1997] + '...'
                db.execute('INSERT INTO {} (level, hostname, msg, user_agent) '
                           'VALUES (%s, %s, %s, %s)'\
                           .format(config.LOGGING_TABLE_NAME),
                           (level, gethostbyname(gethostname()), msg,
                            request.user_agent.string))
            db_con.commit()

# FIXME this function does more than just profiling -- consider
# changing name to sth like serve_request()
def profile(fun):
    def exec_profiled_fun(*args, **kwargs):
        t1 = time.time()
        # do not serve banned crawlers
        if config.BANNED_CRAWLERS \
                and config.BANNED_CRAWLERS.search(request.user_agent.string):
            result = config.BANNED_CRAWLER_RESPONSE
        else:
            result = fun(*args, **kwargs)
        t2 = time.time()
        log('INFO', '{} {}.{} took {}s'.format(
                        '{}?{}'.format(request.path, request.query_string.decode()),
                        fun.__module__, fun.__name__, t2-t1))
        return result
    return exec_profiled_fun

