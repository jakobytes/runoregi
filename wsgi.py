from flask import Flask, request
import math
import os
import pymysql
import re

import config
from data import Poem
import poemdiff

application = Flask(__name__)


@application.route('/poemdiff')
@application.route('/runodiff')
def show_diff():
    nro_1 = request.args.get('nro1', 1, type=str)
    nro_2 = request.args.get('nro2', 1, type=str)
    return poemdiff.render(nro_1, nro_2)

@application.route('/poem')
@application.route('/runo')
def show_poem():

    def _makecolcomp(value):
        result = hex(255-int(value*51))[2:]
        if len(result) == 1:
            result = '0'+result
        return result

    def _makecol(value):
        val_norm = min(math.log(value), 10)
        rg = _makecolcomp(min(val_norm, 5))
        b = _makecolcomp(max(val_norm-5, 0))
        return '#'+rg+rg+b

    nro = request.args.get('nro', 1, type=str)
    hl = request.args.get('hl', None, type=int)
    result = ['<h1>{}</h1>'.format(nro)]
    result.append('<small>[<a href="/">to index</a>]</small>')
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        poem = Poem.from_db_by_nro(db, nro, fmt='mysql')
        result.append('<p>')
        result.append('<h2>Similar poems</h2>')
        db.execute(
            'SELECT so.nro, s.sim_al FROM so_sim_al s'
            ' JOIN sources so ON so.so_id = s.so2_id'
            ' WHERE s.so1_id = %s AND s.sim_al > 0.01'
            ' ORDER BY s.sim_al DESC;',
            (poem.so_id,))
        result.append('<table>')
        for nro_2, sim in db.fetchall():
            simperc = round(sim*100)
            bw = simperc*3
            result.append(
                '<tr><td><a href="/poemdiff?nro1={}&nro2={}">{}</a></td>'
                '<td>&emsp;<img src="/static/img/blue.png" title="{} %" alt="{} %"'
                ' width="{}" height="10">&ensp;<small>{} %</small></td>'\
                .format(nro, nro_2, nro_2, simperc, simperc, bw, simperc))
        result.append('</ul>')
        result.append('</p>')
        result.append('</table>')
        result.append('<table cellspacing="0" cellpadding="2">')
        result.append('<h2>Text</h2>')
        for key in sorted(poem.meta.keys()):
            result.append(
                '<tr><td colspan="3"><small><b>{}:</b> {}</small></td></tr>'\
                    .format(key, poem.meta[key]))
        result.append('<tr><td colspan="3">&nbsp;</td></tr>')
        for i, v in enumerate(poem.verses, 1):
            if v.type == 'V':
                text = v.text
                if hl is not None and hl == i:
                    text = '<b>{}</b>'.format(v.text)
                result.append(
                    '<tr>'
                    '<td bgcolor="{}" align="right">'
                    '<a name="{}" href="/verse?id={}">'
                    '<img src="/static/img/transparent.png" width="15" height="15"'
                    ' title="{} similar" alt="{}"></a></td>'
                    '<td align="right">&ensp;<sup><small>{}</a>'
                    '</small></sup></td><td>{}</td>'
                    '</tr>'\
                    .format(_makecol(v.clustfreq), i, v.v_id, v.clustfreq, v.clustfreq, i, text))
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
            '<small>[<a href="/poem?nro={}">back to poem</a>]</small>'\
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
                '<tr><td><a href="/poem?nro={}&hl={}#{}">{}</td>'
                '<td><sup><small>{}</small></sup></td><td>{}</td></tr>'\
                .format(nro, pos, pos, nro_text, pos, text))
        result.append('</table>')
    return '\n'.join(result)

@application.route('/')
def index():
    q = request.args.get('q', 'a', type=str).lower()
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
    result.append('<tr><td><b>code</b></td><td><b>title</b></td><td><b>poems</b></td></tr>')
    with open('data/index/index-{}.txt'.format(q)) as fp:
        for line in fp:
            code, title, poems = line.rstrip().split('\t')
            result.append('<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
                code,
                title,
                ',\n'.join('<a href="/poem?nro={}">{}</a>'.format(x, x) \
                           for x in poems.split(','))))
    result.append('</table>')
    return '\n'.join(result)

if __name__ == '__main__':
    application.run()
