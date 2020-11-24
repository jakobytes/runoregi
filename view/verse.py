from flask import render_template
import pymysql

import config
from data import get_structured_metadata, render_themes_tree


def render(v_id):

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
        db.execute(
            'SELECT v_id, text, nro, clust_id FROM verses'
            ' NATURAL JOIN verse_poem'
            ' NATURAL JOIN poems'
            ' NATURAL JOIN v_clust'
            ' WHERE v_id = %s;', v_id)
        v_id, text, nro, clust_id = db.fetchall()[0]
        regions = []
        themes = []
        smd = { x.p_id: x for x in get_structured_metadata(db, clust_id=clust_id) }
        db.execute(
            'SELECT vp.p_id, vp.pos, vp.v_id, v.text'
            ' FROM v_clust vc'
            '   JOIN verses v ON vc.v_id = v.v_id'
            '   JOIN verse_poem vp ON v.v_id = vp.v_id'
            ' WHERE vc.clust_id = %s',
            (clust_id,))
        verses = _group_by_source(db.fetchall(), smd)
    return render_template('verse.html', v_id=v_id, text=text,
                           nro=nro, regions=regions, themes=themes,
                           verses=verses)

