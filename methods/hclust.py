import numpy as np
import scipy.cluster.hierarchy
from scipy.spatial.distance import squareform


def make_sim_mtx(poems, onesided=False):
    m = np.zeros(shape=(len(poems), len(poems))) + np.eye(len(poems))
    idx = { nro: i for i, nro in enumerate(poems) }
    for nro in poems:
        for s in poems[nro].sim_poems:
            if onesided:
                m[idx[nro], idx[s.nro]] = s.sim_al_l
            else:
                m[idx[nro], idx[s.nro]] = s.sim_al
    return m


def sim_to_dist(m):
    d = 1-m
    d[d < 0] = 0
    return squareform(d)

