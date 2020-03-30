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
            '       so.year, col.collector, tt.types'
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
        nro, results = None, []
        for r in db.fetchall():
            if r[0] == nro and results:
                results[-1][1].append(r[1])
                results[-1][2].append(r[2])
                results[-1][3].append(r[3])
            else:
                nro = r[0]
                results.append(
                    (r[0], [r[1]], [r[2]], [r[3]], r[4], r[5], r[6], r[7],
                     r[8].split(';;;') if r[8] else []))
        # verses = [v[:8]+(v[8].split(';;;') if v[8] else '',) for v in db.fetchall()]
    return render_template('verse.html', v_id=v_id, text=text,
                           nro=nro, verses=results)

