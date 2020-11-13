from collections import defaultdict
from flask import render_template
import numpy as np
import pymysql
import re
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
    v_sim s
    JOIN verse_poem vp1 ON s.v1_id = vp1.v_id
    JOIN verse_poem vp2 ON s.v2_id = vp2.v_id
WHERE
    vp1.p_id = %s
    AND vp2.p_id = %s
;
'''


def get_data_from_db(nro_1, nro_2, mysql_params):
    poem_1, poem_2, sim_list = None, None, None
    with pymysql.connect(**mysql_params) as db:
        poem_1 = Poem.from_db_by_nro(db, nro_1)
        poem_2 = Poem.from_db_by_nro(db, nro_2)
        db.execute(SIM_SELECT, (poem_1.p_id, poem_2.p_id))
        sims_list = db.fetchall()
    return poem_1, poem_2, sims_list


def poem_to_verse_dict(poem):
    '''Convert a poem to dictionary: verse_id -> list of positions
       in the text. Also return the total number of verses.'''
    v_dict = defaultdict(lambda: list())
    n = 0
    for i, v in enumerate(poem.text_verses()):
        v_dict[v.v_id].append(i)
        n += 1
    return v_dict, n


def build_similarity_matrix(poem_1, poem_2, sims_list):
    '''Create a verse similarity matrix for the poems.'''
    poem_1_v_ids, n1 = poem_to_verse_dict(poem_1)
    poem_2_v_ids, n2 = poem_to_verse_dict(poem_2)

    # FIXME this is a slight hack to add identical verse pairs
    # the preferred way is to use clusters for alignment rather than raw
    # similarities
    ids = set(poem_1_v_ids.keys()) | set(poem_2_v_ids.keys())
    sims_list = list(sims_list)
    sims_list.extend((i, i, 1.0) for i in ids)

    sims = np.zeros(shape=(n1, n2), dtype=np.float32)
    for v1_id, v2_id, s in sims_list:
        for i in poem_1_v_ids[v1_id]:
            for j in poem_2_v_ids[v2_id]:
                sims[i,j] = float(s)
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
                if x == ' ' and different: x = '_'
                if y == ' ' and different: y = '_'
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
    return render_template('poemdiff.html', p1=poem_1, p2=poem_2,
                           meta_keys=meta_keys, alignment=alignment)

