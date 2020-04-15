from flask import render_template
from operator import itemgetter
import pymysql

import config


MAX_QUERY_LENGTH = 20


def get_hits(db, start_id, end_id, clust_succ, dist=2, hitfact=0.5, context=2):
    hits = []
    # Get candidate verses: all verses belonging to one of the clusters
    # occurring in the query.
    db.execute(
        'SELECT v_so.so_id, vc.v_id, vc.clust_id FROM v_clust vc'
        ' JOIN v_so ON vc.v_id = v_so.v_id'
        ' JOIN (SELECT DISTINCT clust_id FROM v_clust'
        '       WHERE v_id BETWEEN %s AND %s) AS c'
        '   ON c.clust_id = vc.clust_id'
        ' ORDER BY vc.v_id;', (start_id, end_id))
    # Find sequences of candidate verses that are in distance <= `dist`
    # from each other and their cluster IDs are a subsequence of those
    # in the query. Such sequences are called `hits`.
    # FIXME checking whether the cluster IDs form a subsequence of the
    # one in the query is currently done incorrectly (esp. duplicate
    # cluster IDs in the query are not handled properly).
    cur_hit, last_v_id, last_clust_id = None, None, None
    for so_id, v_id, clust_id in db.fetchall():
        if cur_hit is None:
            cur_hit = { 'so_id' : so_id, 'matches' : [v_id] }
        else:
            if v_id - cur_hit['matches'][-1] <= dist \
                    and clust_id in clust_succ[last_clust_id]:
                cur_hit['matches'].append(v_id)
            else:
                hits.append(cur_hit)
                cur_hit = { 'so_id' : so_id, 'matches' : [v_id] }
        last_clust_id = clust_id
    hits.append(cur_hit)
    # add intervals
    for h in hits:
        h['interval'] = (h['matches'][0]-context, h['matches'][-1]+context)
    # filter and sort hits
    min_hit_length = hitfact*(end_id-start_id+1)
    hits = [h for h in hits if len(h['matches']) >= min_hit_length]
    hits.sort(
        reverse=True,
        key=lambda h: (len(h['matches']), h['matches'][-1]-h['matches'][0]))
    return hits


def get_verses(db, intervals):
    ids_clause = ' OR '.join(
        'v.v_id BETWEEN {} AND {}'
        .format(start, end) for start, end in intervals)
    db.execute(
        'SELECT v.v_id, v.text, v_so.so_id, v_so.pos'
        ' FROM verses v'
        ' JOIN v_so ON v_so.v_id = v.v_id'
        ' WHERE v.type = "V" AND {};'\
        .format(ids_clause))
    result = \
        { v_id: { 'text' : text, 'so_id' : so_id, 'pos': pos } \
          for v_id, text, so_id, pos in db.fetchall() }
    return result


def get_sources_metadata(db, so_ids):
    db.execute(
        'SELECT so.so_id, so.nro,'
        '       CONCAT(sm1.value, " ", sm2.value),'
        '       CONCAT(loc.region, " — ", loc.name),'
        '       so.year, col.collector, tt.types'
        ' FROM sources so'
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
        ' WHERE so.so_id IN ({});'.format(','.join(map(str, so_ids))))
    result = { so_id: {
                 'nro' : nro, 'name': name, 'year' : year,
                 'loc' : loc, 'col': col,
                 'types': types.split(';;;') if types else []
               } for so_id, nro, name, loc, year, col, types in db.fetchall() }
    return result


def render(start_id, end_id, dist=2, context=2, hitfact=0.5):
    if (end_id - start_id) > MAX_QUERY_LENGTH:
        return '<b>Error:</b> passage length currently limited to {} verses!'\
               .format(MAX_QUERY_LENGTH)
    if end_id < start_id:
        return '<b>Error:</b> passage end before the start!'
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        db.execute(
            'SELECT v_id, clust_id FROM v_clust'
            ' WHERE v_id BETWEEN %s AND %s;', (start_id, end_id))
        clust_ids = []
        for v_id, clust_id in db.fetchall():
            clust_ids.append(clust_id)
        # FIXME This is not the right way to check whether the matching
        # verses occur in the proper order. Need something like an FSA.
        clust_succ = {}
        for i in range(len(clust_ids)):
            clust_succ[clust_ids[i]] = set(clust_ids[i+1:])
        hits = get_hits(
            db, start_id, end_id, clust_succ,
            dist=dist, context=context, hitfact=hitfact)
        if not hits:
            return 'No matching passages found.'
        # get verse information for all relevant verses
        verses = get_verses(db, [h['interval'] for h in hits])
        # get source information
        so_ids = sorted(set(str(v['so_id']) for v in verses.values()))
        sources = get_sources_metadata(db, so_ids)
        # add snippets to hits
        for h in hits:
            h['verses'] = [
                (v_id,
                 verses[v_id]['pos'],
                 verses[v_id]['text'],
                 v_id in h['matches']) \
                    for v_id in range(h['interval'][0], h['interval'][1]+1) \
                    if v_id in verses \
                        and verses[v_id]['so_id'] == h['so_id']]
            h['hl'] = start_id in range(*h['interval'])
        return render_template(
            'passage.html', start=start_id, end=end_id, dist=dist,
            context=context, hitfact=hitfact, hits=hits, sources=sources)

