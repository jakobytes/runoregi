import math
import pymysql

import config
from data import Poem


def render(nro, hl):
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

