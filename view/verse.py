from flask import render_template
import pymysql

import config
from data import get_structured_metadata, render_themes_tree, render_csv
from external import make_map_link


def render(nro=None, pos=None, v_id=None, fmt='html'):

    def _group_by_source(verses, smd):
        '''
        Group the results of the verses query by source, i.e. convert
        per-verse tuples:
          (p_id, pos, v_id, text)
        to per-source tuples:
          (nro, verses, so_name, location, year, collector, types)
        where `verses` is a list of (pos, v_id, text) and `smd`
        a dictionary: p_id -> StructuredMetadata.
        '''
        cur_p_id, results = None, []
        for p_id, pos, v_id, text in verses:
            if p_id == cur_p_id and results:
                results[-1][1].append((pos, v_id, text))
            else:
                cur_p_id = p_id
                results.append(
                    (smd[p_id].nro, [(pos, v_id, text)],
                     smd[p_id].title, smd[p_id].location,
                     smd[p_id].year, smd[p_id].collector,
                     render_themes_tree(smd[p_id].themes)))
        return results

    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        if nro is not None and pos is not None:
            db.execute(
                'SELECT v_id, text, nro, clust_id FROM verses'
                ' NATURAL JOIN verse_poem'
                ' NATURAL JOIN poems'
                ' NATURAL JOIN v_clust'
                ' WHERE nro = %s AND pos = %s;', (nro, pos))
        elif v_id is not None:
            db.execute(
                'SELECT v_id, text, nro, clust_id FROM verses'
                ' NATURAL JOIN verse_poem'
                ' NATURAL JOIN poems'
                ' NATURAL JOIN v_clust'
                ' WHERE v_id = %s;', v_id)
        v_id, text, nro, clust_id = db.fetchall()[0]
        smd = { x.p_id: x for x in get_structured_metadata(db, clust_id=clust_id) }
        db.execute(
            'SELECT vp.p_id, vp.pos, vp.v_id, v.text'
            ' FROM v_clust vc'
            '   JOIN verses v ON vc.v_id = v.v_id'
            '   JOIN verse_poem vp ON v.v_id = vp.v_id'
            ' WHERE vc.clust_id = %s'
            ' ORDER BY vp.p_id, vp.pos;',
            (clust_id,))

    if fmt == 'csv':
        return render_csv([
            (smd[p_id].nro, pos, text, smd[p_id].location, smd[p_id].collector,
             '\n'.join(' > '.join(t) for t in smd[p_id].themes)) \
            for p_id, pos, v_id, text in db.fetchall()],
            header=('nro', 'pos', 'text', 'location', 'collector', 'themes'))
    else:
        verses = _group_by_source(db.fetchall(), smd)
        map_lnk = make_map_link('verse', nro=nro, pos=pos)
        return render_template('verse.html', map_lnk=map_lnk, nro=nro, pos=pos,
                               text=text, verses=verses)
