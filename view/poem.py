from flask import render_template
import math
import pymysql
import re

import config
from data import Poem


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
        poem = Poem.from_db_by_nro(db, nro, fmt='mysql')
        #title = '{OSA} {ID}'.format(**poem.meta)
        title = poem.nro
        loc, col, year = poem.loc, poem.col, poem.year
        if poem.refs is not None:
            refs = re.sub('\n+', ' ', poem.refs).replace('#', '\n#').split('\n')
        topics = poem.topics
        # db.execute(
        #     'SELECT so.nro,'
        #     '       CONCAT(sm1.value, " ", sm2.value),'
        #     '       CONCAT(loc.region, " — ", loc.name),'
        #     '       so.year, col.collector, s.sim_al'
        #     ' FROM so_sim_al s'
        #     ' JOIN sources so ON so.so_id = s.so2_id'
        #     ' JOIN collectors col ON so.col_id = col.col_id'
        #     ' JOIN locations loc ON so.loc_id = loc.loc_id'
        #     ' LEFT OUTER JOIN so_meta sm1 ON so.so_id = sm1.so_id AND sm1.field = "OSA"'
        #     ' LEFT OUTER JOIN so_meta sm2 ON so.so_id = sm2.so_id AND sm2.field = "ID"'
        #     ' WHERE s.so1_id = %s AND s.sim_al > 0.01'
        #     ' ORDER BY s.sim_al DESC;',
        #     (poem.so_id,))
        # sim_poems = db.fetchall()
        sim_poems = []
        for i, v in enumerate(poem.verses, 1):
            verses.append((i, v.v_id, v.clustfreq, _makecol(v.clustfreq),
                           v.type, v.text))
    return render_template('poem.html', nro=nro, hl=hl, title=title,
                           loc=loc, col=col, year=year,
                           topics=topics, sim_poems=sim_poems, meta=poem.meta,
                           verses=verses, refs=refs)

