from flask import render_template
import pymysql

import config


def render(v_id):

    def _group_by_source(verses):
        '''
        Group the results of the verses query by source, i.e. convert
        per-verse tuples:
          (nro, pos, v_id, text, so_name, location, year, collector,
           types)
        to per-source tuples:
          (nro, verses, so_name, location, year, collector, types)
        where `verses` is a list of (pos, v_id, text).
        '''
        cur_nro, results = None, []
        for nro, pos, v_id, text, so_name, loc, year, col, types in verses:
            if nro == cur_nro and results:
                results[-1][1].append((pos, v_id, text))
            else:
                cur_nro = nro
                results.append(
                    (cur_nro, [(pos, v_id, text)],
                     so_name, loc, year, col,
                     types.split(';;;') if types else []))
        return results

    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        db.execute(
            'SELECT v_id, text, nro FROM verses'
            ' NATURAL JOIN verse_poem'
            ' NATURAL JOIN poems'
            ' WHERE v_id = %s;', v_id)
        v_id, text, nro = db.fetchall()[0]
        # db.execute(
        #     'SELECT region, count(*) as freq '
        #     ' FROM v_clust vc1 '
        #     ' JOIN v_clust vc2 ON vc1.clust_id = vc2.clust_id'
        #     ' JOIN v_so ON v_so.v_id = vc2.v_id'
        #     ' NATURAL JOIN sources'
        #     ' NATURAL JOIN locations'
        #     ' WHERE vc1.v_id=%s'
        #     ' GROUP BY region ORDER BY freq DESC;', v_id)
        # regions = db.fetchall()
        regions = []
        # db.execute(
        # 'SELECT CONCAT(f.title, " — ", t.title_1), count(*) as freq '
        # ' FROM v_clust vc1'
        # ' JOIN v_clust vc2 ON vc1.clust_id = vc2.clust_id'
        # ' JOIN v_so ON v_so.v_id = vc2.v_id'
        # ' JOIN so_type ON v_so.so_id = so_type.so_id'
        # ' JOIN types t ON t.t_id=so_type.t_id'
        # ' JOIN files f ON f.f_id = t.f_id'
        # ' WHERE vc1.v_id=%s'
        # ' GROUP BY t.title_1 ORDER BY freq DESC;', v_id)
        # themes = db.fetchall()
        themes = []
        # db.execute(
        #     'SELECT so.nro, v_so.pos, v_so.v_id, v.text,'
        #     '       CONCAT(sm1.value, " ", sm2.value),'
        #     '       CONCAT(loc.region, " — ", loc.name),'
        #     '       so.year, col.collector, tt.types'
        #     ' FROM v_clust vc1'
        #     '   JOIN v_clust vc2 ON vc1.clust_id = vc2.clust_id'
        #     '   JOIN verses v ON vc2.v_id = v.v_id'
        #     '   JOIN v_so ON v.v_id = v_so.v_id'
        #     '   JOIN sources so ON v_so.so_id = so.so_id'
        #     '   JOIN locations loc ON so.loc_id = loc.loc_id'
        #     '   JOIN collectors col ON so.col_id = col.col_id'
        #     '   LEFT OUTER JOIN so_meta sm1 ON so.so_id = sm1.so_id AND sm1.field = "OSA"'
        #     '   LEFT OUTER JOIN so_meta sm2 ON so.so_id = sm2.so_id AND sm2.field = "ID"'
        #     '   LEFT OUTER JOIN'
        #     '     (SELECT'
        #     '        so_id,'
        #     '        GROUP_CONCAT(CONCAT(f.title, " — ", t.title_1) SEPARATOR ";;;") AS types'
        #     '      FROM so_type st'
        #     '      JOIN types t ON t.t_id = st.t_id'
        #     '      JOIN files f ON t.f_id = f.f_id'
        #     '      GROUP BY so_id)'
        #     '     tt ON so.so_id = tt.so_id'
        #     ' WHERE vc1.v_id = %s',
        #     (v_id,))
        db.execute(
            'SELECT p.nro, vp.pos, vp.v_id, v.text,'
            '       p.nro,'
            '       "No location",'
            '       "No year", "No collector", ""'
            ' FROM v_clust vc1'
            '   JOIN v_clust vc2 ON vc1.clust_id = vc2.clust_id'
            '   JOIN verses v ON vc2.v_id = v.v_id'
            '   JOIN verse_poem vp ON v.v_id = vp.v_id'
            '   JOIN poems p ON vp.p_id = p.p_id'
            ' WHERE vc1.v_id = %s',
            (v_id,))
        verses = _group_by_source(db.fetchall())
    return render_template('verse.html', v_id=v_id, text=text,
                           nro=nro, regions=regions, themes=themes,
                           verses=verses)

