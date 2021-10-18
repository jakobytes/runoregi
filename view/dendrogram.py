from flask import render_template
from operator import itemgetter
import numpy as np
import pymysql
import scipy.cluster.hierarchy
from scipy.spatial.distance import squareform

import config
from data import get_structured_metadata


def get_dist_mtx(db, p_ids, dist='al'):
    p_ids_str = ','.join(map(str, p_ids))
    idx = { p_id: i for i, p_id in enumerate(p_ids) }
    m = np.zeros(shape=(len(p_ids), len(p_ids))) + np.eye(len(p_ids))
    q = 'SELECT p1_id, p2_id, sim_{} FROM p_sim'\
        '  WHERE p1_id IN ({}) AND p2_id IN ({});'\
        .format(dist, p_ids_str, p_ids_str)
    db.execute(q)
    for p1_id, p2_id, sim in db.fetchall():
        m[idx[p1_id],idx[p2_id]] = sim
    return squareform(1-m)


def get_p_ids_by_theme(db, theme_id):
    db.execute(\
        'SELECT p_id, is_minor FROM poem_theme'
        ' NATURAL JOIN themes'
        ' WHERE theme_id = %s;',
        (theme_id,))
    return list(map(itemgetter(0), db.fetchall()))


def cluster(x, method):
    if method == 'average':
        return scipy.cluster.hierarchy.average(x)
    elif method == 'centroid':
        return scipy.cluster.hierarchy.centroid(x)
    elif method == 'complete':
        return scipy.cluster.hierarchy.complete(x)
    elif method == 'single':
        return scipy.cluster.hierarchy.single(x)
    elif method == 'ward':
        return scipy.cluster.hierarchy.ward(x)


# XXX transform linkages to a horizontal dendrogram -- CURRENTLY NOT USED
#def transform_dendrogram(dd, n, smd):
#
#    def tx(x):
#        return int(150*x+75)
#
#    def ty(y):
#        return int(525-500*y)
#
#    result = []
#    ill = np.zeros(n, dtype=np.uint16)   # inverse leaves list -- positions of leaf nodes
#    ll = leaves_list(dd)
#    for i in range(dd.shape[0]+1):
#        ill[ll[i]] = i
#    for i in range(dd.shape[0]):
#        x1 = tx(ill[int(dd[i,0])]) if dd[i,0] < n else result[int(dd[i,0])-n][4]
#        x2 = tx(ill[int(dd[i,1])]) if dd[i,1] < n else result[int(dd[i,1])-n][4]
#        y1 = ty(0) if dd[i,0] < n else result[int(dd[i,0])-n][5]
#        y2 = ty(0) if dd[i,1] < n else result[int(dd[i,1])-n][5]
#        x = (x1 + x2) // 2
#        y = ty(dd[i,2])
#        nros1 = [smd[int(dd[i,0])].nro] if dd[i,0] < n else result[int(dd[i,0])-n][6]
#        nros2 = [smd[int(dd[i,1])].nro] if dd[i,1] < n else result[int(dd[i,1])-n][6]
#        result.append((x1, y1, x2, y2, x, y, nros1+nros2))
#    return result


# transform linkages to a vertical dendrogram
def transform_vert(dd, n, smd):

    def tx(x):
        return int(400*(1-x)+20)

    def ty(y):
        return int(70*y+25)

    result = []
    ill = np.zeros(n, dtype=np.uint16)   # inverse leaves list -- positions of leaf nodes
    ll = scipy.cluster.hierarchy.leaves_list(dd)
    for i in range(dd.shape[0]+1):
        ill[ll[i]] = i
    for i in range(dd.shape[0]):
        if dd[i, 2] < 1:
            x1 = tx(0) if dd[i,0] < n else result[int(dd[i,0])-n][4]
            x2 = tx(0) if dd[i,1] < n else result[int(dd[i,1])-n][4]
            y1 = ty(ill[int(dd[i,0])]) if dd[i,0] < n else result[int(dd[i,0])-n][5]
            y2 = ty(ill[int(dd[i,1])]) if dd[i,1] < n else result[int(dd[i,1])-n][5]
            x = tx(dd[i,2])
            y = (y1 + y2) // 2
            nros1 = [smd[int(dd[i,0])].nro] if dd[i,0] < n else result[int(dd[i,0])-n][6]
            nros2 = [smd[int(dd[i,1])].nro] if dd[i,1] < n else result[int(dd[i,1])-n][6]
            result.append((x1, y1, x2, y2, x, y, nros1+nros2))
    return result

def render(theme_id=None, method='complete', dist='al'):
    p_ids, smd = [], []
    upper, name, desc = None, None, None
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        db.execute(\
          'SELECT t4.theme_id, t4.name, t3.theme_id, t3.name,'
          '       t2.theme_id, t2.name, t1.theme_id, t1.name,'
          '       t1.description'
           ' FROM themes t1'
           '  LEFT OUTER JOIN themes t2 on t1.par_id = t2.t_id'
           '  LEFT OUTER JOIN themes t3 on t2.par_id = t3.t_id'
           '  LEFT OUTER JOIN themes t4 on t3.par_id = t4.t_id'
           ' WHERE t1.theme_id = %s;', (theme_id,));
        r = db.fetchall()[0]
        upper = [(r[2*i], r[2*i+1]) for i in range(3) if r[2*i] is not None]
        name = r[7]
        desc = r[8]

        if theme_id is not None:
            p_ids = get_p_ids_by_theme(db, theme_id)
        if p_ids:
            smd = get_structured_metadata(db, p_ids = p_ids)
        d = get_dist_mtx(db, p_ids, dist=dist)
        clust = cluster(d, method)
        ll = scipy.cluster.hierarchy.leaves_list(clust)
        dd = transform_vert(clust, len(p_ids), smd)
    return render_template('dendrogram.html', theme_id=theme_id, smd=smd,
        ll=ll, dd=dd, n=len(p_ids), upper=upper, name=name, desc=desc,
        dist=dist, method=method)

