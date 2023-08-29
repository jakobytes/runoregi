from flask import request
from socket import gethostbyname, gethostname
import pymysql
import time

import config

def create_logging_table(db):
    db.execute(
        'CREATE TABLE {}('
        '  log_id INTEGER NOT NULL AUTO_INCREMENT,'
        '  level ENUM("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") DEFAULT "INFO",'
        '  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,'
        '  hostname VARCHAR(100) DEFAULT NULL,'
        '  msg VARCHAR(2000) DEFAULT NULL,'
        '  user_agent VARCHAR(1000) DEFAULT NULL,'
        '  PRIMARY KEY(log_id), '
        '  INDEX (level), '
        '  INDEX (timestamp), '
        '  INDEX (hostname) '
        ');'.format(config.LOGGING_TABLE_NAME))

def log(level, msg):
    if config.ENABLE_LOGGING_TO_DB:
        with pymysql.connect(**config.MYSQL_PARAMS).cursor() as db:
            db.execute('SHOW TABLES LIKE %s;', (config.LOGGING_TABLE_NAME,))
            if len(list(db.fetchall())) <= 0:
                create_logging_table(db)
            db.execute('INSERT INTO {} (level, hostname, msg, user_agent) VALUES (%s, %s, %s, %s)'\
                       .format(config.LOGGING_TABLE_NAME),
                       (level, gethostbyname(gethostname()), msg, request.user_agent.string))

def profile(fun):
    def exec_profiled_fun(*args, **kwargs):
        t1 = time.time()
        result = fun(*args, **kwargs)
        t2 = time.time()
        log('INFO', '{} {}.{} took {}s'.format(
                        '{}?{}'.format(request.path, request.query_string.decode()),
                        fun.__module__, fun.__name__, t2-t1))
        return result
    return exec_profiled_fun

