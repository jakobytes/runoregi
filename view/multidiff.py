from flask import render_template
import numpy as np
from operator import itemgetter
import pymysql

from align import align
import config
from data import Poem, render_themes_tree, render_csv


V_SIM_SELECT = '''
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

P_SIM_SELECT = '''
SELECT
    p1_id, p2_id, sim_al
FROM
    p_sim
WHERE
    p1_id IN ({})
    AND p2_id IN ({})
    AND p1_id < p2_id
;
'''


def get_data_from_db(nros, mysql_params):
    poems, sims_list = None, None
    with pymysql.connect(**mysql_params) as db:
        poems = [Poem.from_db_by_nro(db, nro) for nro in nros]
        ids_str = ','.join(str(p.p_id) for p in poems)
        query = P_SIM_SELECT.format(ids_str, ids_str)
        db.execute(query)
        p_sims_list = list(db.fetchall())
        query = V_SIM_SELECT.format(ids_str, ids_str)
        db.execute(query)
        v_sims = {}
        for i, j, s in db.fetchall():
            v_sims[i,j] = s
            v_sims[j,i] = s
        # insert identities explicitly
        for p in poems:
            for v in p.text_verses():
                v_sims[v.v_id,v.v_id] = 1
    return poems, p_sims_list, v_sims


def multialign(poems, p_sims, v_sims):

    # This computes the aggregated similarity (max) between verse tuples,
    # leaving Nones out.
    # e.g. _agr_sim((A, None, B), (None, C, None, D))
    #      = max(sim(A, C), sim(A, D), sim(B, C), sim(B, D))
    # Returns -1 if no verse pair is similar.
    def _agr_sim(x, y):
        x_ids = [vx.v_id for vx in x if vx is not None]
        y_ids = [vy.v_id for vy in y if vy is not None]
        sims = [-1] + [v_sims[(i, j)] \
                       for i in x_ids for j in y_ids if (i, j) in v_sims]
        return max(sims)

    # FIXME passing x_size and y_size here is slow and clumsy!
    # A better solution would be to have parameters like
    # `ins` and `del` instead of `empty` for the `align()` function
    # (different `empty` values for the left and right side),
    # so that the Nones produced by it already have the right lengths.
    def _merge(x, y, x_size, y_size):
        mx = (None,) * x_size if x is None else x
        my = (None,) * y_size if y is None else y
        return mx+my

    p_sims_list = [(i, j, p_sims[i,j]) \
                   for i in range(p_sims.shape[0]) for j in range(i)]
    p_sims_list.sort(reverse=True, key=itemgetter(2))
    cl = [[i] for i in range(len(poems))]   # poem clusters (lists of indices)
    inv_cl = list(range(len(poems)))        # map: poem_index -> cluster_index
    al = [[(v,) for v in p.text_verses()] for p in poems]
    for i, j, s in p_sims_list:
        if inv_cl[i] == inv_cl[j]:
            continue
        pair_al = align(al[inv_cl[i]], al[inv_cl[j]],
                   insdel_cost=0,
                   dist_fun = lambda x,y: \
                       _agr_sim(al[inv_cl[i]][x], al[inv_cl[j]][y]),
                   opt_fun=max,
                   empty=None)
        # XXX merging clusters -- determine how to put them next to each other!
        # Now they are arranged naively, e.g. while merging clusters
        # "AB" and "CD", the result is "ABCD", but other possibilities
        # would be "CDAB", "BACD" or "CDBA" (depending on which neighboring
        # poem pairs are most similar?)
        al[inv_cl[i]] = [_merge(x, y, len(cl[inv_cl[i]]), len(cl[inv_cl[j]])) \
                         for x, y, w in pair_al]
        # merge the clusters of poems i and j
        cl[inv_cl[i]].extend(cl[inv_cl[j]])
        for k in cl[inv_cl[j]]:
            inv_cl[k] = inv_cl[i]
        # if the merged cluster contains all poems -> finish
        if len(cl[inv_cl[i]]) == len(poems):
            return cl[inv_cl[i]], al[inv_cl[i]]


def build_poem_similarity_matrix(poems, p_sims_list, v_sims):
    # -1 means "no value"
    p_sims = -np.ones(shape=(len(poems), len(poems)))
    id_dict = { p.p_id: i for i, p in enumerate(poems) }
    # fill in the precomputed similarities
    # FIXME before this is used, the similarities in the database
    # need to be changed to the same type of computation as below
    # (no substitutions of differing verses allowed)
    #for p1_id, p2_id, s in p_sims_list:
    #    sims[id_dict[p1_id],id_dict[p2_id]] = float(s)
    #    sims[id_dict[p2_id],id_dict[p1_id]] = float(s)
    # fill in the missing similarities
    for i in range(len(poems)):
        for j in range(i):
            if p_sims[i,j] == -1:
                p1 = list(poems[i].text_verses())
                p2 = list(poems[j].text_verses())
                al = align(
                    p1, p2,
                    insdel_cost=0,
                    dist_fun = lambda x,y:
                        v_sims[(p1[x].v_id, p2[y].v_id)] \
                            if (p1[x].v_id, p2[y].v_id) in v_sims \
                            else -1,
                    opt_fun=max,
                    empty=None)
                s = sum(map(itemgetter(2), al)) / len(al)
                p_sims[i,j] = s
                p_sims[j,i] = s
    return p_sims


def render(nros, fmt='html'):
    poems, p_sims_list, v_sims = get_data_from_db(nros, config.MYSQL_PARAMS)
    p_sims = build_poem_similarity_matrix(poems, p_sims_list, v_sims)
    ids, als = multialign(poems, p_sims, v_sims)
    nros = [nros[i] for i in ids]
    poems = [poems[i] for i in ids]
    meta_keys = sorted(set([k for p in poems for k in p.meta.keys()]))
    themes = [render_themes_tree(p.smd.themes) for p in poems]
    if fmt == 'csv':
        rows = [((v.text if v else '') for v in row) for row in als]
        return render_csv(rows, header=tuple(p.smd.nro for p in poems))
    else:
        return render_template('multidiff.html', nro=nros, poems=poems,
                               alignment=als, meta_keys=meta_keys,
                               themes=themes)

