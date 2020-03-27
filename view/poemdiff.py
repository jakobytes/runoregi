from flask import render_template
import numpy as np
import pymysql
from subprocess import Popen, PIPE

from align import align
import config
from data import Poem


COLOR_NORMAL = None
COLOR_CHARDIFF = 'blue'
COLOR_LINEDIFF = 'grey'

SIM_SELECT = '''
SELECT
    s.v1_id, s.v2_id, s.sim_cos
FROM
    v_sim_cos s
    JOIN v_so v_so1 ON s.v1_id = v_so1.v_id
    JOIN v_so v_so2 ON s.v2_id = v_so2.v_id
WHERE
    v_so1.so_id = %s
    AND v_so2.so_id = %s
;
'''


def get_data_from_db(nro_1, nro_2, mysql_params):
    poem_1, poem_2, sim_list = None, None, None
    with pymysql.connect(**mysql_params) as db:
        poem_1 = Poem.from_db_by_nro(db, nro_1, fmt='mysql')
        poem_2 = Poem.from_db_by_nro(db, nro_2, fmt='mysql')
        db.execute(SIM_SELECT, (poem_1.so_id, poem_2.so_id))
        sims_list = db.fetchall()
    return poem_1, poem_2, sims_list


def build_similarity_matrix(poem_1, poem_2, sims_list):
    # create a verse similarity matrix for the poems
    poem_1_v_ids = { v.v_id : i for i, v in enumerate(poem_1.text_verses()) }
    poem_2_v_ids = { v.v_id : i for i, v in enumerate(poem_2.text_verses()) }
    sims = np.zeros(
        shape=(len(poem_1_v_ids), len(poem_2_v_ids)),
        dtype=np.float32)
    for v1_id, v2_id, s in sims_list:
        sims[poem_1_v_ids[v1_id], poem_2_v_ids[v2_id]] = float(s)
    return sims


def render(nro_1, nro_2):
    # TODO
    # - some refactoring
    # - bold for captions
    poem_1, poem_2, sims_list = \
        get_data_from_db(nro_1, nro_2, config.MYSQL_PARAMS)
    sims = build_similarity_matrix(poem_1, poem_2, sims_list)
    al = align(
        list(poem_1.text_verses()),
        list(poem_2.text_verses()),
        insdel_cost=0,
        dist_fun=lambda i, j: sims[i,j],
        opt_fun=max,
        empty=None)
    meta_keys = sorted(list(set(poem_1.meta.keys()) | set(poem_2.meta.keys())))
    meta_1, meta_2 = {}, {}
    for key in meta_keys:
        meta_1[key] = poem_1.meta[key] if key in poem_1.meta else ''
        meta_2[key] = poem_2.meta[key] if key in poem_2.meta else ''
    alignment = []
    for row in al:
        verse_1, verse_2 = [], []
        if row[2] > 0:
            v_al = align(row[0].text, row[1].text)
            chunk_1, chunk_2, different, col = [], [], False, COLOR_NORMAL
            for x, y, c in v_al:
                if (x != y) != different:
                    if chunk_1:
                        verse_1.append((col, ''.join(chunk_1)))
                    if chunk_2:
                        verse_2.append((col, ''.join(chunk_2)))
                    chunk_1, chunk_2 = [], []
                    different = (x != y)
                    col = COLOR_CHARDIFF if different else COLOR_NORMAL
                if x == ' ': x = '_'
                if y == ' ': y = '_'
                chunk_1.append(x)
                chunk_2.append(y)
            if chunk_1:
                verse_1.append((col, ''.join(chunk_1)))
            if chunk_2:
                verse_2.append((col, ''.join(chunk_2)))
        else:
            if row[0] is not None:
                verse_1.append((COLOR_LINEDIFF, row[0].text))
            if row[1] is not None:
                verse_2.append((COLOR_LINEDIFF, row[1].text))
        alignment.append((verse_1, verse_2))
    return render_template('poemdiff.html', nro_1=nro_1, nro_2=nro_2,
                           meta_keys=meta_keys, meta_1=meta_1, meta_2=meta_2,
                           alignment=alignment)

