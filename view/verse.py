import pymysql

import config


def render(v_id):
    result = []
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

