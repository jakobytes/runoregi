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
            'SELECT so.nro, v_so.pos, v_so.v_id, v.text,'
            '       CONCAT(sm1.value, " ", sm2.value),'
            '       CONCAT(loc.region, " — ", loc.name),'
            '       col.collector, tt.types'
            ' FROM v_clust vc1'
            '   JOIN v_clust vc2 ON vc1.clust_id = vc2.clust_id'
            '   JOIN verses v ON vc2.v_id = v.v_id'
            '   JOIN v_so ON v.v_id = v_so.v_id'
            '   JOIN sources so ON v_so.so_id = so.so_id'
            '   JOIN locations loc ON so.loc_id = loc.loc_id'
            '   JOIN collectors col ON so.col_id = col.col_id'
            '   LEFT OUTER JOIN so_meta sm1 ON so.so_id = sm1.so_id AND sm1.field = "OSA"'
            '   LEFT OUTER JOIN so_meta sm2 ON so.so_id = sm2.so_id AND sm2.field = "ID"'
            '   LEFT OUTER JOIN'
            '     (SELECT'
            '        so_id,'
            '        GROUP_CONCAT(CONCAT(f.title, " — ", t.title_1) SEPARATOR ";;;") AS types'
            '      FROM so_type st'
            '      JOIN types t ON t.t_id = st.t_id'
            '      JOIN files f ON t.f_id = f.f_id'
            '      GROUP BY so_id)'
            '     tt ON so.so_id = tt.so_id'
            ' WHERE vc1.v_id = %s',
            (v_id,))
        verses = [v[:7]+(v[7].split(';;;') if v[7] else '',) for v in db.fetchall()]
    return render_template('verse.html', v_id=v_id, text=text,
                           nro=nro, verses=verses)

