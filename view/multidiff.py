from collections import defaultdict
from flask import render_template
import numpy as np
from operator import itemgetter
import pymysql

from align import align, merge_alignments
import config
from data import Poem, render_themes_tree, render_csv

SIM_SELECT = '''
SELECT
    s.v1_id, s.v2_id, s.sim_cos
FROM
    v_sim s
    JOIN verse_poem vp1 ON s.v1_id = vp1.v_id
    JOIN verse_poem vp2 ON s.v2_id = vp2.v_id
WHERE
    vp1.p_id IN ({})
    AND vp2.p_id IN ({})
    AND vp1.p_id < vp2.p_id
;
'''


def get_data_from_db(nros, mysql_params):
    poems, sims_list = None, None
    with pymysql.connect(**mysql_params) as db:
        poems = [Poem.from_db_by_nro(db, nro) for nro in nros]
        ids_str = ','.join(str(p.p_id) for p in poems)
        query = SIM_SELECT.format(ids_str, ids_str)
        db.execute(query)
        sims_list = list(db.fetchall())
    return poems, sims_list


def build_similarity_matrices(poems, sims_list, empty=-1):
    sims = {}
    id_dict = defaultdict(lambda: list())
    # build dictionaries of IDs
    for i, p in enumerate(poems):
        for j, v in enumerate(p.text_verses()):
            id_dict[v.v_id].append((i, j))
    sims_list.extend((v_id, v_id, 1.0) for v_id in id_dict.keys())
    # build empty matrices
    n = [len(list(p.text_verses())) for p in poems]
    for i in range(len(poems)):
        for j in range(i+1, len(poems)):
            sims[(i,j)] = empty*np.ones(shape=(n[i],n[j]), dtype=np.float32)
    # fill the matrices
    for v1_id, v2_id, s in sims_list:
        for (i, k) in id_dict[v1_id]:
            for (j, l) in id_dict[v2_id]:
                if i < j:
                    sims[(i,j)][k,l] = float(s)
                elif j < i:
                    sims[(j,i)][l,k] = float(s)
    return sims


def arrange(als):
    # The purpose of this function is to choose the best order, in which the
    # poems are shown next to each other.
    # XXX The following greedy algorithm doesn't find the best solution! It
    # constructs the "optimal" permutation of length n by inserting the n-th
    # element into the "optimal" permutation of length (n-1). It should be
    # replaced with a correct one.

    def _get_al(als, i, j):
        if i < j:
            return als[(i,j)]
        else:
            return [(y, x, z) for (x, y, z) in als[(j,i)]]

    n = max(j for (i, j) in als)+1
    m = np.zeros(shape=(n,n))
    for (i, j), al in als.items():
        s = sum(map(itemgetter(2), al))
        m[i,j] = s
        m[j,i] = s
    p = [0, 1]
    for i in range(2, n):
        scores = \
            [m[i,p[0]]] \
            + [m[p[j],i]+m[i,p[j+1]]-m[p[j],p[j+1]] for j in range(len(p)-1)] \
            + [m[i,p[-1]]]
        k = max(enumerate(scores), key=itemgetter(1))[0]
        p = p[:k] + [i] + p[k:]
    return p, [_get_al(als, p[i], p[i+1]) for i in range(len(p)-1)]


def render(nros, fmt='html'):
    poems, sims_list = get_data_from_db(nros, config.MYSQL_PARAMS)
    sims = build_similarity_matrices(poems, sims_list)
    als = {}
    for (i, j), s in sims.items():
        als[(i,j)] = align(
            list(poems[i].text_verses()),
            list(poems[j].text_verses()),
            insdel_cost=0,
            dist_fun = lambda x,y: sims[(i,j)][x,y],
            opt_fun=max,
            empty=None)
    permutation, als_lst = arrange(als)
    poems = [poems[i] for i in permutation]
    als_merged = merge_alignments(als_lst, empty=None)
    scores = []
    for a in als_lst:
        scores.append(sum(z for (x, y, z) in a)/len(a))
    meta_keys = sorted(set([k for p in poems for k in p.meta.keys()]))
    themes = [render_themes_tree(p.smd.themes) for p in poems]
    if fmt == 'csv':
        rows = [((v.text if v else '') for v in row) for row in als_merged]
        return render_csv(rows, header=tuple(p.smd.nro for p in poems))
    else:
        return render_template('multidiff.html', nro=nros, poems=poems,
                               alignment=als_merged, scores=scores,
                               meta_keys=meta_keys, themes=themes)

