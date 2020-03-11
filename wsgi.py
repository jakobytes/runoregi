from flask import Flask
import os
import pymysql

application = Flask(__name__)

MYSQL_PARAMS = {
    'host' : os.getenv('DB_HOST'),
    'port' : int(os.getenv('DB_PORT')),
    'user' : os.getenv('DB_USER'),
    'password' : os.getenv('DB_PASS'),
    'database' : os.getenv('DB_NAME')
}


@application.route('/')
def hello_world():
    results = ['Hello world!']
    with pymysql.connect(**MYSQL_PARAMS) as db:
        db.execute('SELECT count(*) FROM verses;')
        for row in db.fetchall():
            results.append(repr(row))
        db.execute('SELECT * FROM verses limit 10;')
        for row in db.fetchall():
            results.append(repr(row))
    return '<br/>\n'.join(results)

if __name__ == '__main__':
    application.run()
