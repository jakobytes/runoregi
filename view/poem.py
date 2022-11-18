from flask import render_template
import math
from operator import itemgetter
import pymysql
import re

from collections import Counter, defaultdict

import config
from data.poems import Poems
from data.verses import get_verses
from utils import link


DEFAULTS = {
  'nro': None,
  'sim_order': 'consecutive_rare',
  'max_similar': 50,
  'hl': [],
  'sim_thr': 1,
  'show_verse_themes': False,
  'show_shared_verses': False
}

def generate_page_links(args):
    global DEFAULTS

    def pagelink(**kwargs):
        return link('poem', dict(args, **kwargs), DEFAULTS)

    return {
        '+show_verse_themes':
            pagelink(show_verse_themes=True),
        '-show_verse_themes':
            pagelink(show_verse_themes=False),
        '+show_shared_verses':
            pagelink(show_shared_verses=True),
        '-show_shared_verses':
            pagelink(show_shared_verses=False),
        'sim_order:consecutive_rare':
            pagelink(sim_order='consecutive_rare'),
        'sim_order:consecutive':
            pagelink(sim_order='consecutive'),
        'sim_order:rare':
            pagelink(sim_order='rare'),
        'sim_order:any':
            pagelink(sim_order='shared'),
        '+max_similar':
            pagelink(max_similar=args['max_similar']+10),
        '-max_similar':
            pagelink(max_similar=max(args['max_similar']-10, 0))
    }


# TODO verse-level themes
# data structure: list
# - start_pos, end_pos, 
def get_verse_themes(db, nro):
    db.execute('SELECT max(pos) FROM verse_poem NATURAL JOIN poems WHERE nro = %s', (nro,))
    n = db.fetchall()[0][0]
    db.execute('SELECT pos_start, pos_end, name '
               ' FROM verse_theme NATURAL JOIN themes NATURAL JOIN poems '
               ' WHERE nro = %s', (nro,))
    i, last_pos = 0, 0
    results = {}
    for pos_start, pos_end, name in db.fetchall():
        if pos_start > last_pos:
            results[last_pos] = (pos_start-last_pos, '<unknown>', i)
            i += 1
        results[pos_start] = (pos_end-pos_start, name, i)
        i += 1
        last_pos = pos_end
    if n is not None and last_pos < n:
        results[last_pos] = (n-last_pos, '<unknown>', i)
        i += 1
    return results


# TODO refactor and document!
def get_shared_verses(db, poem, max, thr, order, clustering_id=0):
    clust_ids = set(v.clust_id for v in poem.text if v.v_type == 'V' and v.text_cl)
    verses = get_verses(db, clust_id=tuple(clust_ids), clustering_id=clustering_id)

    poem_verses = defaultdict(set)
    poem_versecounts = Counter([v.nro for v in verses])
    verse_poemcounts = Counter([v.clust_id for v in verses])
    for v in verses:
        if v.nro != poem.nro:
            poem_verses[v.nro].add(v.clust_id)
    poem_weights = Counter()
    if order == "rare":
        for (nro, clust_ids) in poem_verses.items():
            for clust_id in clust_ids:
                poem_weights[nro] += 1.0/verse_poemcounts[clust_id]
    elif order == "consecutive" or order == "consecutive_rare":
        nros = [nro for nro, clust_ids in poem_verses.items()]
        last_index = {nro: -1 for nro in nros}
        for i, v in enumerate(poem.text):
            if v.v_type == 'V':
                current = { nro: (v.clust_id in clust_ids)
                            for nro, clust_ids in poem_verses.items() }
                for nro in nros:
                    if current[nro]:
                        if order == "consecutive_rare":
                            poem_weights[nro] += 1.0/(i-last_index[nro]/verse_poemcounts[v.clust_id])
                        else:
                            poem_weights[nro] += 1.0/(i-last_index[nro])
                        last_index[nro]=i
            else:
                for nro in nros:
                    last_index[nro] = i
    else:  #order == "shared"
        poem_weights = poem_versecounts
    verse_poems = defaultdict(list)
    linked_poems = set()
    top_poems = set([nro for nro, count in poem_weights.most_common(max)])
    for v in verses:
        if v.nro in top_poems and poem_versecounts[v.nro] >= thr:
            linked_poems.add(v.nro)
            verse_poems[v.clust_id].append(v.nro)
    linked_poems_sorted = sorted(linked_poems, reverse=True,
                                 key=lambda nro: poem_weights[nro])
    return verse_poems, linked_poems_sorted, len(poem_versecounts)


def render(**args):
    def _makecolcomp(value):
        result = hex(255-int(value*51))[2:]
        if len(result) == 1:
            result = '0'+result
        return result

    def _makecol(value):
        if value is None:
            value = 1
        val_norm = min(math.log(value), 10)
        rg = _makecolcomp(min(val_norm, 5))
        b = _makecolcomp(max(val_norm-5, 0))
        return '#'+rg+rg+b

    links = generate_page_links(args)
    p = Poems(nros=[args['nro']])
    sim_poems, verse_themes, types = None, None, None
    verse_poems, linked_poems, poems_sharing_verses = None, None, None
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        p.get_duplicates_and_parents(db)
        p.get_poem_cluster_info(db)
        p.get_raw_meta(db)
        p.get_refs(db)
        p.get_similar_poems(db, sim_thr=0.1, sim_onesided_thr=0.5)
        p.get_structured_metadata(db)
        p.get_text(db)
        # poem types
        types = p.get_types(db)
        types.get_names(db)
        # get metadata for related poems (similar, duplicates etc.)
        related_nros = list(set([x.nro for x in p[args['nro']].sim_poems] \
                                + p[args['nro']].duplicates + p[args['nro']].parents))
        related = Poems(nros=related_nros)
        if related:
            related.get_structured_metadata(db)
        # get verse-level types
        if args['show_verse_themes']:
            verse_themes = get_verse_themes(db, args['nro'])
        # get verse clusters for the matrix view
        if args['show_shared_verses']:
            verse_poems, linked_poems, poems_sharing_verses = \
                get_shared_verses(db, p[args['nro']], args['max_similar'],
                                  args['sim_thr'], args['sim_order'])
    poem = p[args['nro']]
    data = {
        'poem': poem,
        'related': related,
        'types': types,
        'sim': [(x.nro, x.sim_al) for x in poem.sim_poems if x.sim_al >= 0.1],
        'sim_left': [(x.nro, x.sim_al_l) \
                     for x in poem.sim_poems \
                         if x.sim_al < 0.1 and x.sim_al_l >= 0.5],
        'sim_right': [(x.nro, x.sim_al_r) \
                      for x in poem.sim_poems \
                          if x.sim_al < 0.1 and x.sim_al_r >= 0.5],
        'colors': { x: _makecol(x) for x in set(v.clust_freq for v in poem.text) },
        'verse_themes' : verse_themes,
        'verse_poems': verse_poems,
        'linked_poems': linked_poems,
        'poems_sharing_verses': poems_sharing_verses
    }
    return render_template('poem.html', args=args, data=data, links=links)

