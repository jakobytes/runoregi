from flask import render_template
import pymysql

import config


def render(v_id):
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        db.execute(
            'SELECT v_id, text, nro FROM verses'
            ' NATURAL JOIN v_so'
            ' NATURAL JOIN sources'
            ' WHERE v_id = %s;', v_id)
        v_id, text, nro = db.fetchall()[0]
        db.execute(
            'SELECT so.nro, v_so.pos, v_so.v_id, v.text'
            ' FROM v_clust vc1'
            '   JOIN v_clust vc2 ON vc1.clust_id = vc2.clust_id'
            '   JOIN verses v ON vc2.v_id = v.v_id'
            '   JOIN v_so ON v.v_id = v_so.v_id'
            '   JOIN sources so ON v_so.so_id = so.so_id'
            ' WHERE vc1.v_id = %s',
            (v_id,))
        verses = db.fetchall()
    return render_template('verse.html', v_id=v_id, text=text,
                           nro=nro, verses=verses)

