from flask import Flask, request
import pymysql

import config
import runodiff

application = Flask(__name__)


@application.route('/runodiff')
def show_diff():
    nro_1 = request.args.get('nro1', 1, type=str)
    nro_2 = request.args.get('nro2', 1, type=str)
    return runodiff.render(nro_1, nro_2)

@application.route('/')
def hello_world():
    results = ['Hello world!']
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        db.execute('SELECT count(*) FROM verses;')
        for row in db.fetchall():
            results.append(repr(row))
        db.execute('SELECT * FROM verses limit 10;')
        for row in db.fetchall():
            results.append(repr(row))
    return '<br/>\n'.join(results)

if __name__ == '__main__':
    application.run()
