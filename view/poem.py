from flask import render_template
import math
import pymysql
import re

import config
from data import Poem, get_structured_metadata, render_themes_tree


def get_similar_poems(db, p_id):
    db.execute(
        'SELECT p2_id, sim_al FROM p_sim WHERE p1_id = %s'
        ' ORDER BY sim_al DESC;', (p_id,))
    id_sim = db.fetchall()
    ids = [x[0] for x in id_sim]
    result = []
    if ids:
        smd = {x.p_id: x for x in get_structured_metadata(db, p_ids=ids)}
        result = [(x[1], smd[x[0]]) for x in id_sim]
    return result


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
        sim_poems = get_similar_poems(db, poem.p_id)
        for i, v in enumerate(poem.verses, 1):
            verses.append((i, v.clustfreq, _makecol(v.clustfreq),
                           v.type, v.text))
    return render_template('poem.html', p=poem, hl=hl, sim_poems=sim_poems,
                           verses=verses, refs=refs,
                           themes=render_themes_tree(poem.smd.themes))

