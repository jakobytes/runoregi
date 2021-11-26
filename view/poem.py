from flask import render_template
import math
from operator import itemgetter
import pymysql
import re

from collections import Counter, defaultdict

import config
from data import Poem, get_structured_metadata, render_themes_tree


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


def get_similar_poems_2(db, p_id, max, thr, order, verses):
    db.execute("""SELECT DISTINCT v.v_id, p2.nro FROM verses v
JOIN verse_poem vp ON vp.v_id = v.v_id
LEFT OUTER JOIN v_clust vc ON vp.v_id = vc.v_id
LEFT OUTER JOIN v_clust vc2 ON vc2.clust_id = vc.clust_id
LEFT OUTER JOIN verse_poem vp2 ON vp2.v_id = vc2.v_id
LEFT OUTER JOIN poems p2 ON p2.p_id = vp2.p_id 
WHERE v.type='V' AND vp.p_id=%s AND vp2.p_id!=%s;""", (p_id,p_id))
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
                current = {poem: (verse.v_id in verses) for poem, verses in poem_verses.items()}
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
    return verse_poems, sorted(linked_poems, key=lambda poem: poem_weights[poem], reverse=True), len(poem_versecounts)


def render(nro, hl, max_similar, sim_thr, sim_order):
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

    topics, sim_poems, meta, verses, refs = [], [], [], [], []
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        poem = Poem.from_db_by_nro(db, nro)
        title = poem.smd.title
        loc, col, year = poem.smd.location, poem.smd.collector, poem.smd.year
        if poem.refs is not None:
            refs = re.sub('\n+', ' ', '\n'.join(poem.refs)).replace('#', '\n#').split('\n')
        topics = poem.smd.themes
        sim, sim_l, sim_r = get_similar_poems(db, poem.p_id)
        verse_poems, linked_poems, poems_sharing_verses = get_similar_poems_2(db, poem.p_id, max_similar, sim_thr, sim_order, poem.verses)
        for i, v in enumerate(poem.verses, 1):
            verses.append((i, v.clustfreq, _makecol(v.clustfreq),
                           v.type, v.text, v.v_id))
    return render_template('poem.html', p=poem, hl=hl, sim_poems=sim,
                           sim_poems_left=sim_l, sim_poems_right=sim_r,
                           verses=verses, refs=refs,
                           themes=render_themes_tree(poem.smd.themes), verse_poems=verse_poems,
                           linked_poems=linked_poems, max_similar=max_similar, sim_order=sim_order,
                           poems_sharing_verses=poems_sharing_verses, nr_linked_poems=len(linked_poems))

