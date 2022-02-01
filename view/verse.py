from collections import defaultdict
from flask import render_template
import pymysql

import config
from data import \
    clean_special_chars, get_structured_metadata, \
    render_themes_tree, render_csv
from external import make_map_link


def get_similar_verses(db, clust_id, clustering_id=0):
    db.execute(
        'SELECT'
        '  min(v1.v_id), p2.nro, vp2.pos, v2.text, vcf2.freq'
        ' FROM'
        '   v_sim s'
        '   JOIN verses v1 ON s.v1_id = v1.v_id'
        '   JOIN v_clust vc1 ON s.v1_id = vc1.v_id AND vc1.clustering_id = %s'
        '   JOIN verses v2 ON s.v2_id = v2.v_id'
        '   JOIN v_clust vc2 ON s.v2_id = vc2.v_id AND vc2.clustering_id = %s'
        '   JOIN v_clust_freq vcf2 ON vc2.clust_id = vcf2.clust_id AND vcf2.clustering_id = %s'
        '   JOIN verse_poem vp2 ON v2.v_id = vp2.v_id'
        '   JOIN poems p2 ON vp2.p_id = p2.p_id'
        ' WHERE'
        '   vc1.clust_id = %s'
        '   AND vc1.clust_id <> vc2.clust_id'
        ' GROUP BY'
        '   vc2.clust_id;',
        (clustering_id, clustering_id, clustering_id, clust_id))
    results = defaultdict(lambda: list())
    for r in db.fetchall():
        results[r[0]].append((r[1], r[2], clean_special_chars(r[3]), r[4]))
    return dict(results)


def render(nro=None, pos=None, v_id=None, clustering_id=0, fmt='html'):

    def _group_by_source(verses, smd, simverses):
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
                if v_id in simverses:
                    results[-1][7].extend(simverses[v_id])
                    del simverses[v_id]
            else:
                cur_p_id = p_id
                results.append(
                    (smd[p_id].nro, [(pos, v_id, clean_special_chars(text))],
                     smd[p_id].title, smd[p_id].location,
                     smd[p_id].year, smd[p_id].collector,
                     render_themes_tree(smd[p_id].themes),
                     list(simverses[v_id]) if v_id in simverses else list()))
                if v_id in simverses:
                    del simverses[v_id]
        return results

    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        if nro is not None and pos is not None:
            db.execute(
                'SELECT v_id, text, nro, clust_id, freq FROM verses'
                ' NATURAL JOIN verse_poem'
                ' NATURAL JOIN poems'
                ' NATURAL JOIN v_clust'
                ' NATURAL JOIN v_clust_freq'
                ' WHERE nro = %s AND pos = %s AND clustering_id = %s;',
                (nro, pos, clustering_id))
        elif v_id is not None:
            db.execute(
                'SELECT v_id, text, nro, clust_id, freq FROM verses'
                ' NATURAL JOIN verse_poem'
                ' NATURAL JOIN poems'
                ' NATURAL JOIN v_clust'
                ' NATURAL JOIN v_clust_freq'
                ' WHERE v_id = %s AND clustering_id = %s;', (v_id, clustering_id))
        v_id, text, nro, clust_id, freq = db.fetchall()[0]
        smd = { x.p_id: x for x in get_structured_metadata(db, clust_id=clust_id, clustering_id=clustering_id) }
        db.execute(
            'SELECT vp.p_id, vp.pos, vp.v_id, v.text'
            ' FROM v_clust vc'
            '   JOIN verses v ON vc.v_id = v.v_id'
            '   JOIN verse_poem vp ON v.v_id = vp.v_id'
            ' WHERE vc.clust_id = %s AND clustering_id = %s'
            ' ORDER BY vp.p_id, vp.pos;',
            (clust_id, clustering_id))
        verses = list(db.fetchall())
        db.execute('SELECT * FROM v_clusterings;')
        clusterings = db.fetchall()

    if fmt in ('csv', 'tsv'):
        return render_csv([
            (smd[p_id].nro, pos, text, smd[p_id].location, smd[p_id].collector,
             '\n'.join(' > '.join(t[1] for t in tt if len(t) >= 2) \
                       for tt in smd[p_id].themes)) \
            for p_id, pos, v_id, text in verses],
            header=('nro', 'pos', 'text', 'location', 'collector', 'themes'),
            delimiter='\t' if fmt == 'tsv' else ',')
    else:
        simverses = get_similar_verses(db, clust_id, clustering_id=clustering_id)
        verses_by_src = _group_by_source(verses, smd, simverses)
        map_lnk = make_map_link('verse', nro=nro, pos=pos, clustering=clustering_id)
        return render_template('verse.html', map_lnk=map_lnk, nro=nro, pos=pos,
                               text=text, freq=freq, verses=verses_by_src,
                               clustering_id=clustering_id, clusterings=clusterings)

