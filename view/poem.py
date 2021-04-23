from flask import render_template
import math
from operator import itemgetter
import pymysql
import re

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


def render(nro, hl):
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
        for i, v in enumerate(poem.verses, 1):
            verses.append((i, v.clustfreq, _makecol(v.clustfreq),
                           v.type, v.text))
    return render_template('poem.html', p=poem, hl=hl, sim_poems=sim,
                           sim_poems_left=sim_l, sim_poems_right=sim_r,
                           verses=verses, refs=refs,
                           themes=render_themes_tree(poem.smd.themes))

