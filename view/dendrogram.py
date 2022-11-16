from flask import render_template
from operator import itemgetter
import numpy as np
import pymysql
import scipy.cluster.hierarchy
from scipy.spatial.distance import squareform

import config
from data import get_structured_metadata
from utils import link


DEFAULTS = {
  'source': None,
  'nro': [],
  'theme_id': None,
  'dist': 'al',
  'nb': 1,
  'method': 'complete',
}


def generate_page_links(args):
    global DEFAULTS

    def pagelink(**kwargs):
        return link('dendrogram', dict(args, **kwargs), DEFAULTS)

    result = {
        '-nb': pagelink(nb=min(args['nb']+0.1, 1)),
        '+nb': pagelink(nb=max(args['nb']-0.1, 0)),
        '0nb': pagelink(nb=1),
    }
    for method in ['complete', 'average', 'single', 'centroid', 'ward']:
        result['method-{}'.format(method)] = pagelink(method=method)
    return result


def get_dist_mtx(db, p_ids):
    p_ids_str = ','.join(map(str, p_ids))
    idx = { p_id: i for i, p_id in enumerate(p_ids) }
    m = np.zeros(shape=(len(p_ids), len(p_ids))) + np.eye(len(p_ids))
    q = 'SELECT p1_id, p2_id, sim_al FROM p_sim'\
        '  WHERE p1_id IN ({}) AND p2_id IN ({});'\
        .format(p_ids_str, p_ids_str)
    db.execute(q)
    for p1_id, p2_id, sim in db.fetchall():
        m[idx[p1_id],idx[p2_id]] = sim
    d = 1-m
    d[d < 0] = 0
    return squareform(d)


def get_p_ids_for_cluster(db, nro):
    db.execute('SELECT pc2.p_id '
               'FROM p_clust pc1'
               '  JOIN poems p1 ON p1.p_id = pc1.p_id'
               '  JOIN p_clust pc2 ON pc1.clust_id = pc2.clust_id '
               'WHERE p1.nro = %s;', (nro,))
    return list(map(itemgetter(0), db.fetchall()))


def get_p_ids_by_nros(db, nros):
    db.execute('SELECT p_id FROM poems '
               'WHERE nro IN ({});'\
               .format(','.join(['"{}"'.format(x) for x in nros]),))
    return list(map(itemgetter(0), db.fetchall()))


def get_p_ids_by_theme(db, theme_id):
    db.execute(\
        'SELECT p_id, is_minor FROM poem_theme'
        ' NATURAL JOIN themes'
        ' WHERE theme_id = %s;',
        (theme_id,))
    return list(map(itemgetter(0), db.fetchall()))


def get_theme_info(db, theme_id):
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
    return upper, name, desc


def get_expanded_p_ids(db, p_ids, nb):
    p_ids_str = ','.join(map(str, p_ids))
    q = 'SELECT DISTINCT p2_id FROM p_sim'\
        '  WHERE p1_id IN ({}) AND p2_id NOT IN ({}) AND sim_al >= {};'\
        .format(p_ids_str, p_ids_str, nb)
    db.execute(q)
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


def render(**args):
    links = generate_page_links(args) 
    p_ids, smd, nt = [], [], 0  # `nt` is the number of poems in the theme
    upper, name, desc = None, None, None
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        if args['source'] == 'theme':
            upper, name, desc = get_theme_info(db, args['theme_id'])
            p_ids = get_p_ids_by_theme(db, args['theme_id'])
            thm = set(p_ids)
            if args['nb'] is not None and args['nb'] < 1:
                p_ids.extend(get_expanded_p_ids(db, p_ids, args['nb']))
                p_ids.sort()
        elif args['source'] == 'cluster':
            p_ids = get_p_ids_for_cluster(db, args['nro'])
            thm = set(p_ids)
        elif args['source'] == 'nros':
            p_ids = get_p_ids_by_nros(db, args['nro'].split(','))
            thm = set(p_ids)
        if p_ids:
            smd = get_structured_metadata(db, p_ids = p_ids)
        d = get_dist_mtx(db, p_ids)
        clust = cluster(d, args['method'])
        ll = scipy.cluster.hierarchy.leaves_list(clust)
        dd = transform_vert(clust, len(p_ids), smd)
    data = {
        'smd': smd, 'll': ll, 'dd': dd, 'n': len(p_ids), 'thm': thm,
        'upper': upper, 'name': name, 'desc': desc
    }
    return render_template('dendrogram.html', args=args, data=data, links=links)

