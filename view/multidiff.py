from flask import render_template
import numpy as np
from operator import itemgetter
import pymysql
import scipy.cluster.hierarchy
from scipy.spatial.distance import squareform

from shortsim.align import align
from shortsim.ngrcos import vectorize

import config
from data import Poem, render_themes_tree, render_csv

from view.dendrogram import cluster    # TODO move it to some common place
from utils import link


DEFAULTS = {
  'nro': None,
  'method': 'none',
  't': 0.75,
  'format': 'html'
}


def generate_page_links(args):
    global DEFAULTS

    def pagelink(**kwargs):
        return link('multidiff', dict(args, **kwargs), DEFAULTS)

    result = {
        'csv': pagelink(format='csv'),
        'tsv': pagelink(format='tsv'),
        '-t': pagelink(t=max(args['t']-0.05, 0)),
        '+t': pagelink(t=min(args['t']+0.05, 1)),
    }
    for method in ['none', 'complete', 'average', 'single']:
        result['method-{}'.format(method)] = pagelink(method=method)
    return result


def get_sim_mtx(db, nros):
    nros_str = ','.join(['"{}"'.format(nro) for nro in nros])
    idx = { nro: i for i, nro in enumerate(nros) }
    m = np.zeros(shape=(len(nros), len(nros))) + np.eye(len(nros))
    m_onesided = np.zeros(shape=(len(nros), len(nros))) + np.eye(len(nros))
    q = 'SELECT p1.nro, p2.nro, sim_al, sim_al_l FROM p_sim s'\
        '  JOIN poems p1 ON p1.p_id = s.p1_id'\
        '  JOIN poems p2 ON p2.p_id = s.p2_id'\
        '  WHERE p1.nro IN ({}) AND p2.nro IN ({});'\
        .format(nros_str, nros_str)
    db.execute(q)
    for nro1, nro2, sim, sim_l in db.fetchall():
        m[idx[nro1],idx[nro2]] = sim
        m_onesided[idx[nro1],idx[nro2]] = sim_l
    return m, m_onesided


def sim_to_dist(m):
    d = 1-m
    d[d < 0] = 0
    return squareform(d)


# TODO merge with view.poemdiff.compute_similarity()
def compute_verse_similarity(poems, threshold):
    verses = set((v.v_id, v.text_cl if v.text_cl is not None else '') \
                 for p in poems for v in p.text_verses())
    v_ids, v_texts, ngr_ids, m = vectorize(verses)
    sim = m.dot(m.T)
    sim[sim < threshold] = 0
    v_sim = {}
    for i, j in list(zip(*sim.nonzero())):
        v_sim[v_ids[i], v_ids[j]] = sim[i,j]
    return v_sim


def merge_alignments(poems, merges, v_sims):
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

    alignments = [[(v,) for v in p.text_verses()] for p in poems]
    for i in range(merges.shape[0]):
        al_1 = alignments[int(merges[i,0])]
        al_2 = alignments[int(merges[i,1])]
        pair_al = align(al_1, al_2,
                        insdel_cost=0,
                        dist_fun = lambda x,y: \
                            _agr_sim(al_1[x], al_2[y]),
                        opt_fun=max,
                        empty=None)
        alignments.append([_merge(x, y, len(al_1[0]), len(al_2[0])) \
                           for x, y, w in pair_al])
    return alignments[-1]


def render(**args):
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        poems = [Poem.from_db_by_nro(db, nro) for nro in args['nro']]
        m, m_onesided = get_sim_mtx(db, args['nro'])
        d = sim_to_dist(m)

    v_sims = compute_verse_similarity(poems, args['t'])
    clust, ids = None, None
    if args['method'] == 'none':
        # align the poems from left to right, in the order given by `nros`
        clust = np.zeros(shape=(len(poems)-1, 2))
        for i in range(len(poems)-1):
            clust[i,0] = 0 if i == 0 else len(poems)+i-1
            clust[i,1] = i+1
        ids = list(range(len(poems)))
    else:
        # arrange the poems using hierarchical clustering
        clust = cluster(d, args['method'])
        ids = scipy.cluster.hierarchy.leaves_list(clust) 

    als = merge_alignments(poems, clust[:,:2], v_sims)

    poems = [poems[i] for i in ids]
    meta_keys = sorted(set([k for p in poems for k in p.meta.keys()]))
    themes = [render_themes_tree(p.smd.themes) for p in poems]
    if args['format'] in ('csv', 'tsv'):
        rows = [((v.text if v else '') for v in row) for row in als]
        return render_csv(rows, header=tuple(p.smd.nro for p in poems),
                          delimiter='\t' if args['format'] == 'tsv' else ',')
    else:
        data = {
            'alignment': als, 'poems': poems, 'meta_keys': meta_keys,
            'themes': themes, 'm': m, 'm_onesided': m_onesided
        }
        links = generate_page_links(args)
        return render_template('multidiff.html', args=args, data=data, links=links)

