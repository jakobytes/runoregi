from flask import render_template
import math
import pymysql

import config
from data import Poem


def render(nro, hl):
    def _makecolcomp(value):
        result = hex(255-int(value*51))[2:]
        if len(result) == 1:
            result = '0'+result
        return result

    def _makecol(value):
        val_norm = min(math.log(value), 10)
        rg = _makecolcomp(min(val_norm, 5))
        b = _makecolcomp(max(val_norm-5, 0))
        return '#'+rg+rg+b

    sim_poems, meta, verses = [], None, []
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        poem = Poem.from_db_by_nro(db, nro, fmt='mysql')
        db.execute(
            'SELECT so.nro, s.sim_al FROM so_sim_al s'
            ' JOIN sources so ON so.so_id = s.so2_id'
            ' WHERE s.so1_id = %s AND s.sim_al > 0.01'
            ' ORDER BY s.sim_al DESC;',
            (poem.so_id,))
        for nro_2, sim in db.fetchall():
            simperc = round(sim*100)
            bw = simperc*3
            sim_poems.append((nro_2, simperc, bw))
        meta = [(key, poem.meta[key]) for key in sorted(poem.meta)]
        for i, v in enumerate(poem.verses, 1):
            if v.type == 'V':
                verses.append((i, v.v_id, v.clustfreq, _makecol(v.clustfreq), v.text))
    return render_template('poem.html', nro=nro, hl=hl, sim_poems=sim_poems,
                           meta=meta, verses=verses)

