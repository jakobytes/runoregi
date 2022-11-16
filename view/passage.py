from flask import render_template
from operator import itemgetter
import pymysql

import config
from data import \
    clean_special_chars, get_structured_metadata, \
    render_themes_tree, render_csv
from external import make_map_link
from utils import link

MAX_QUERY_LENGTH = None

DEFAULTS = {
  'nro': None,
  'start': 0,
  'end': 0,
  'clustering': 0,
  'context': 2,
  'dist': 2,
  'hitfact': 0.5,
  'format': 'html'
}


def generate_page_links(args, clusterings):
    global DEFAULTS

    def pagelink(**kwargs):
        return link('passage', dict(args, **kwargs), DEFAULTS)

    map_args = { key: val for key, val in args.items() if val != DEFAULTS[key] }
    result = {
        'csv': pagelink(format='csv'),
        'tsv': pagelink(format='tsv'),
        '-context': pagelink(context=max(args['context']-2, 0)),
        '+context': pagelink(context=args['context']+2),
        '-results': pagelink(dist=max(args['dist']-1, 1), hitfact=args['hitfact']*1.25),
        '+results': pagelink(dist=args['dist']+1, hitfact=args['hitfact']*0.8),
        'map_lnk' : make_map_link('passage', **map_args)
    }
    for c in clusterings:
        result['clustering-{}'.format(c[0])] = pagelink(clustering=c[0])
    return result


def get_hits(db, nro, start_pos, end_pos, clustering_id=0, dist=2, hitfact=0.5, context=2):
    hits = []
    # Get candidate verses: all verses belonging to one of the clusters
    # occurring in the query.
    db.execute(
        'SELECT vp.p_id, vp.pos FROM v_clust vc'
        ' JOIN verse_poem vp ON vc.v_id = vp.v_id'
        ' JOIN (SELECT DISTINCT clust_id'
        '       FROM v_clust'
        '            NATURAL JOIN verse_poem'
        '            NATURAL JOIN poems'
        '       WHERE clustering_id = %s'
        '       AND nro = %s'
        '       AND pos BETWEEN %s AND %s'
        '      ) AS c'
        '   ON c.clust_id = vc.clust_id AND vc.clustering_id = %s'
        ' ORDER BY vp.p_id, vp.pos;',
        (clustering_id, nro, start_pos, end_pos, clustering_id))
    # Find sequences of candidate verses that are in distance <= `dist`
    # from each other and their cluster IDs are a subsequence of those
    # in the query. Such sequences are called `hits`.
    # FIXME checking whether the cluster IDs form a subsequence of the
    # one in the query is currently done incorrectly (esp. duplicate
    # cluster IDs in the query are not handled properly).
    cur_hit, last_v_id, last_clust_id = None, None, None
    for p_id, pos in db.fetchall():
        if cur_hit is None:
            cur_hit = { 'p_id' : p_id, 'matches' : [pos] }
        else:
            if p_id == cur_hit['p_id'] and pos - cur_hit['matches'][-1] <= dist:
                cur_hit['matches'].append(pos)
            else:
                hits.append(cur_hit)
                cur_hit = { 'p_id' : p_id, 'matches' : [pos] }
    hits.append(cur_hit)
    # add intervals
    for h in hits:
        h['interval'] = (h['matches'][0]-context, h['matches'][-1]+context)
    # filter and sort hits
    min_hit_length = hitfact*(end_pos-start_pos+1)
    hits = [h for h in hits if len(h['matches']) >= min_hit_length]
    hits.sort(
        reverse=True,
        key=lambda h: (len(h['matches']), h['matches'][-1]-h['matches'][0]))
    return hits


def get_verses(db, hits):
    ids_clause = ' OR '.join(
        'vp.p_id = {} AND vp.pos BETWEEN {} AND {}'
        .format(h['p_id'], *h['interval']) for h in hits)
    db.execute(
        'SELECT vp.p_id, vp.pos, v.text'
        ' FROM verses v'
        ' JOIN verse_poem vp ON vp.v_id = v.v_id'
        ' WHERE v.type = "V" AND {};'\
        .format(ids_clause))
    result = \
        { (p_id, pos): { 'text' : clean_special_chars(text) } \
          for p_id, pos, text in db.fetchall() }
    return result


def render(**args):
    if MAX_QUERY_LENGTH is not None and (args['end'] - args['start']) > MAX_QUERY_LENGTH:
        return '<b>Error:</b> passage length currently limited to {} verses!'\
               .format(MAX_QUERY_LENGTH)
    if args['end'] < args['start']:
        return '<b>Error:</b> passage end before the start!'
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        hits = get_hits(
            db, args['nro'], args['start'], args['end'], clustering_id=args['clustering'],
            dist=args['dist'], context=args['context'], hitfact=args['hitfact'])
        if not hits:
            return 'No matching passages found.'
        # get verse information for all relevant verses
        verses = get_verses(db, hits)
        # get source information
        p_ids = sorted(set(p_id for (p_id, pos) in verses))
        smd = {x.p_id: x for x in get_structured_metadata(db, p_ids=p_ids)}
        # add snippets to hits
        for h in hits:
            p_id = h['p_id']
            h['verses'] = [
                (pos,
                 pos,
                 verses[(p_id, pos)]['text'],
                 pos in h['matches']) \
                    for pos in range(h['interval'][0], h['interval'][1]+1) \
                    if (p_id, pos) in verses]
            h['hl'] = smd[p_id].nro == args['nro'] and args['start'] in range(*h['interval'])
            h['themes'] = render_themes_tree(smd[p_id].themes)
        db.execute('SELECT * FROM v_clusterings;')
        clusterings = db.fetchall()

    if args['format'] in ('csv', 'tsv'):
        return render_csv([
            (smd[h['p_id']].nro, h['verses'][0][0],
             '\n'.join(map(itemgetter(2), h['verses'])),
             smd[h['p_id']].location, smd[h['p_id']].collector,
             '\n'.join(' > '.join(t[1] for t in tt if len(t) >= 2) \
                       for tt in smd[h['p_id']].themes)) \
            for h in hits],
            header=('nro', 'pos', 'snippet', 'location', 'collector', 'themes'),
            delimiter='\t' if args['format'] == 'tsv' else ',')
    else:
        links = generate_page_links(args, clusterings)
        data = { 'smd': smd, 'hits': hits, 'clusterings': clusterings }
        return render_template('passage.html', args=args, data=data, links=links)

