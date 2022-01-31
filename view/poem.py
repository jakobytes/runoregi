from flask import render_template
import math
from operator import itemgetter
import pymysql
import re

from collections import Counter, defaultdict

import config
from data import Poem, get_structured_metadata, render_themes_tree


DEFAULTS = {
  'sim_order': 'consecutive_rare',
  'max_similar': 50,
  'hl': [],
  'sim_thr': 1,
  'show_verse_themes': False,
  'show_shared_verses': False
}

def link(nro, options, defaults):
    'Generates a link to the same view with specified option settings.'

    def _str(value):
        if isinstance(value, list):
            return ','.join(map(str, value))
        elif isinstance(value, bool):
            return str(value).lower()
        else:
            return str(value)

    link = '/poem?nro={}'.format(nro)
    opt_str = '&'.join('{}={}'.format(key, _str(options[key]))
                       for key in options if options[key] != defaults[key])
    if opt_str:
        return link + '&' + opt_str
    else:
        return link


def generate_page_links(nro, options, defaults):
    return {
        '+show_verse_themes':
            link(nro, dict(options, show_verse_themes=True), defaults),
        '-show_verse_themes':
            link(nro, dict(options, show_verse_themes=False), defaults),
        '+show_shared_verses':
            link(nro, dict(options, show_shared_verses=True), defaults),
        '-show_shared_verses':
            link(nro, dict(options, show_shared_verses=False), defaults),
        'sim_order:consecutive_rare':
            link(nro, dict(options, sim_order='consecutive_rare'), defaults),
        'sim_order:consecutive':
            link(nro, dict(options, sim_order='consecutive'), defaults),
        'sim_order:rare':
            link(nro, dict(options, sim_order='rare'), defaults),
        'sim_order:any':
            link(nro, dict(options, sim_order='shared'), defaults),
        '+max_similar':
            link(nro, dict(options, max_similar=options['max_similar']+10), defaults),
        '-max_similar':
            link(nro, dict(options, max_similar=max(options['max_similar']-10, 0)), defaults)
    }


# TODO verse-level themes
# data structure: list
# - start_pos, end_pos, 
def get_verse_themes(db, p_id):
    db.execute('SELECT max(pos) FROM verse_poem WHERE p_id = %s', (p_id,))
    n = db.fetchall()[0][0]
    db.execute('SELECT pos_start, pos_end, name '
               ' FROM verse_theme NATURAL JOIN themes '
               ' WHERE p_id = %s', (p_id,))
    i, last_pos = 0, 0
    results = {}
    for pos_start, pos_end, name in db.fetchall():
        if pos_start > last_pos:
            results[last_pos] = (pos_start-last_pos, '<unknown>', i)
            i += 1
        results[pos_start] = (pos_end-pos_start, name, i)
        i += 1
        last_pos = pos_end
    if last_pos < n:
        results[last_pos] = (n-last_pos, '<unknown>', i)
        i += 1
    return results


def get_similar_poems(db, p_id, thr_sym=0.1, thr_left=0.5, thr_right=0.5):
    db.execute(
        'SELECT p2_id, sim_al, sim_al_l, sim_al_r FROM p_sim WHERE p1_id = %s'
        ' ORDER BY sim_al DESC;', (p_id,))
    id_sim = db.fetchall()
    ids = [x[0] for x in id_sim]
    result_sym, result_left, result_right = [], [], []
    if ids:
        smd = {x.p_id: x for x in get_structured_metadata(db, p_ids=ids)}
        for x in id_sim:
            if x[1] >= thr_sym:
                result_sym.append((smd[x[0]], x[1]))
            if x[1] < thr_sym and x[2] >= thr_left:
                result_left.append((smd[x[0]], x[2]))
            if x[1] < thr_sym and x[3] >= thr_right:
                result_right.append((smd[x[0]], x[3]))
    result_left.sort(reverse=True, key=itemgetter(1))
    result_right.sort(reverse=True, key=itemgetter(1))
    return result_sym, result_left, result_right


def get_shared_verses(db, p_id, max, thr, order, verses, clustering_id=0):
    db.execute("""SELECT DISTINCT v.v_id, p2.nro FROM verses v
                  JOIN verse_poem vp ON vp.v_id = v.v_id
                  LEFT OUTER JOIN v_clust vc ON vp.v_id = vc.v_id AND vc.clustering_id = %s
                  LEFT OUTER JOIN v_clust vc2 ON vc2.clust_id = vc.clust_id AND vc2.clustering_id = %s
                  LEFT OUTER JOIN verse_poem vp2 ON vp2.v_id = vc2.v_id
                  LEFT OUTER JOIN poems p2 ON p2.p_id = vp2.p_id 
                  WHERE v.type='V' AND vp.p_id=%s AND vp2.p_id!=%s;""",
                  (clustering_id, clustering_id, p_id, p_id))
    results = db.fetchall()
    poem_verses = defaultdict(set)
    poem_versecounts = Counter([x[1] for x in results])
    verse_poemcounts = Counter([x[0] for x in results])
    for (verse, poem) in results:
        poem_verses[poem].add(verse)
    poem_weights = Counter()
    if order == "rare":
        for (poem, verses) in poem_verses.items():
            for verse in verses:
                poem_weights[poem] += 1.0/verse_poemcounts[verse]
    elif order == "consecutive" or order == "consecutive_rare":
        poems = [poem for poem, verses in poem_verses.items()]
        last = {poem: False for poem in poems}
        for verse in verses:
            if verse.type == 'V':
                current = { poem: (verse.v_id in verses)
                            for poem, verses in poem_verses.items() }
                for poem in poems:
                    if current[poem]:
                        if last[poem]:
                            if order == "consecutive_rare":
                                poem_weights[poem] += 1.0/verse_poemcounts[verse.v_id]
                            else:
                                poem_weights[poem] += 1
                        else:
                            if order == "consecutive_rare":
                                poem_weights[poem] += 0.01 / verse_poemcounts[verse.v_id]
                            else:
                                poem_weights[poem] += 0.01
            else:
                current = {poem: False for poem in poems}
            last = current
    else:  #order == "shared"
        poem_weights = poem_versecounts
    verse_poems = defaultdict(list)
    linked_poems = set()
    top_poems = set([poem for poem, count in poem_weights.most_common(max)])
    for (verse, poem) in results:
        if poem in top_poems and poem_versecounts[poem] >= thr:
            linked_poems.add(poem)
            verse_poems[verse].append(poem)
    linked_poems_sorted = sorted(linked_poems, reverse=True,
                                 key=lambda poem: poem_weights[poem])
    return verse_poems, linked_poems_sorted, len(poem_versecounts)


def render(nro, **options):
    global DEFAULTS

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

    links = generate_page_links(nro, options, DEFAULTS)
    topics, sim_poems, meta, verses, refs = [], [], [], [], []
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        poem = Poem.from_db_by_nro(db, nro)
        title = poem.smd.title
        loc, col, year = poem.smd.location, poem.smd.collector, poem.smd.year
        if poem.refs is not None:
            refs = re.sub('\n+', ' ', '\n'.join(poem.refs)).replace('#', '\n#').split('\n')
        topics = poem.smd.themes
        sim, sim_l, sim_r = get_similar_poems(db, poem.p_id)
        verse_poems, linked_poems, poems_sharing_verses = \
            get_shared_verses(db, poem.p_id, options['max_similar'],
                              options['sim_thr'], options['sim_order'],
                              poem.verses)
        verse_themes = get_verse_themes(db, poem.p_id)
        for i, v in enumerate(poem.verses, 1):
            verses.append((i, v.clustfreq, _makecol(v.clustfreq),
                           v.type, v.text, v.v_id))
    return render_template('poem.html', p=poem, sim_poems=sim,
                           sim_poems_left=sim_l, sim_poems_right=sim_r,
                           verses=verses, refs=refs, options=options,
                           themes=render_themes_tree(poem.smd.themes),
                           verse_poems=verse_poems,
                           linked_poems=linked_poems,
                           poems_sharing_verses=poems_sharing_verses,
                           nr_linked_poems=len(linked_poems),
                           verse_themes=verse_themes,
                           links=links)

