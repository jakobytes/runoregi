from flask import Flask, request
import os
import pymysql
import re

import config
from data import Runo
import runodiff

application = Flask(__name__)


@application.route('/runodiff')
def show_diff():
    nro_1 = request.args.get('nro1', 1, type=str)
    nro_2 = request.args.get('nro2', 1, type=str)
    return runodiff.render(nro_1, nro_2)

@application.route('/runo')
def show_runo():
    nro = request.args.get('nro', 1, type=str)
    result = ['<h1>{}</h1>'.format(nro)]
    result.append('<small>[<a href="/">to index</a>]</small>')
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        runo = Runo.from_db_by_nro(db, nro, fmt='mysql')
        result.append('<p>')
        result.append('<b>Similar runos:</b>')
        db.execute(
            'SELECT so.nro, s.sim_al FROM so_sim_al s'
            ' JOIN sources so ON so.so_id = s.so2_id'
            ' WHERE s.so1_id = %s AND s.sim_al > 0.01'
            ' ORDER BY s.sim_al DESC;',
            (runo.so_id,))
        result.append('<ul>')
        for nro_2, sim in db.fetchall():
            result.append(
                '<li><a href="/runodiff?nro1={}&nro2={}">{}</a> ({} %)'\
                .format(nro, nro_2, nro_2, round(sim*100)))
        result.append('</ul>')
        result.append('</p>')
        result.append('<table>')
        for key in sorted(runo.meta.keys()):
            result.append(
                '<tr><td colspan="2"><small><b>{}:</b> {}</small></td></tr>'\
                    .format(key, runo.meta[key]))
        result.append('<tr><td colspan="2">&nbsp;</td></tr>')
        for i, v in enumerate(runo.verses, 1):
            if v.type == 'V':
                result.append(
                    '<tr><td><sup><small><a href="/verse?id={}">{}</a>'
                    '</small></sup></td><td>{}</td></tr>'\
                    .format(v.v_id, i, v.text))
    result.append('</table>')
    return '\n'.join(result)

@application.route('/verse')
def show_verse():
    result = []
    v_id = request.args.get('id', 1, type=str)
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        db.execute(
            'SELECT v_id, text, nro FROM verses'
            ' NATURAL JOIN v_so'
            ' NATURAL JOIN sources'
            ' WHERE v_id = %s;', v_id)
        v_id, text, nro = db.fetchall()[0]
        result.append('<h1>{}</h1>'.format(text))
        result.append(
            '<small>[<a href="/runo?nro={}">back to runo</a>]</small>'\
            .format(nro))
        db.execute(
            'SELECT so.nro, v_so.pos, v_so.v_id, v.text'
            ' FROM v_clust vc1'
            '   JOIN v_clust vc2 ON vc1.clust_id = vc2.clust_id'
            '   JOIN verses v ON vc2.v_id = v.v_id'
            '   JOIN v_so ON v.v_id = v_so.v_id'
            '   JOIN sources so ON v_so.so_id = so.so_id'
            ' WHERE vc1.v_id = %s',
            (v_id,))
        result.append('<h2>Cluster</h2>')
        result.append('<table>')
        for nro, pos, v_id_2, text in db.fetchall():
            nro_text = nro
            if v_id_2 == v_id:
                nro_text = '<b>{}</b>'.format(nro)
                text = '<b>{}</b>'.format(text)
                pos = '<b>{}</b>'.format(pos)
            result.append(
                '<tr><td><a href="/runo?nro={}">{}</td>'
                '<td><sup><small>{}</small></sup></td><td>{}</td></tr>'\
                .format(nro, nro_text, pos, text))
        result.append('</table>')
    return '\n'.join(result)

@application.route('/')
def index():
    q = 'a'
    try:
        q = request.args.get('q', 1, type=str).lower()
    except Exception:
        pass
    result = []
    result.append('<center><h2>')
    index_letters = []
    for filename in sorted(os.listdir('data/index/')):
        m = re.match('index-([a-zäö]).txt', filename)
        if m is not None:
            index_letters.append(m.group(1))
    result.append(' |\n'.join(
        ('<a href="/?q={}">{}</a>'.format(x, x.upper()) if x != q \
         else '<b>{}</b>'.format(x.upper())) \
        for x in index_letters))
    result.append('</h2></center>')
    result.append('<table border="1">')
    result.append('<tr><td><b>code</b></td><td><b>title</b></td><td><b>runos</b></td></tr>')
    with open('data/index/index-{}.txt'.format(q)) as fp:
        for line in fp:
            code, title, runos = line.rstrip().split('\t')
            result.append('<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
                code,
                title,
                ',\n'.join('<a href="/runo?nro={}">{}</a>'.format(x, x) \
                           for x in runos.split(','))))
    result.append('</table>')
    return '\n'.join(result)

if __name__ == '__main__':
    application.run()
