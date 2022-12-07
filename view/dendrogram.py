from flask import render_template
from operator import itemgetter
import numpy as np
import pymysql
import scipy.cluster.hierarchy
from urllib.parse import urlencode

import config
from data.poems import Poems
from data.types import Types
from methods.hclust import cluster, make_sim_mtx, sim_to_dist
from utils import link


DEFAULTS = {
  'source': None,
  'nro': [],
  'theme_id': None,
  'dist': 'al',
  'nb': 1.0,
  'method': 'complete',
}


def generate_page_links(args):
    global DEFAULTS

    def pagelink(**kwargs):
        return link('dendrogram', dict(args, **kwargs), DEFAULTS)

    result = { 'method': {}, 'nb': { 'none': pagelink(nb=1.0) } }
    for nb in [ 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9 ]:
        nb_fmt = '{:.1}'.format(nb)
        result['nb'][nb_fmt] = pagelink(nb=nb)
    for method in ['complete', 'average', 'single', 'centroid', 'ward']:
        result['method'][method] = pagelink(method=method)
    if args['source'] == 'theme' and args['nb'] == 1:
        result['map'] = config.VISUALIZATIONS_URL \
            + '?vis=map_type&' \
            + urlencode({'theme_id': args['theme_id']})
        result['types'] = config.VISUALIZATIONS_URL \
            + '?vis=tree_type_cooc&' \
            + urlencode({'theme_id': args['theme_id'], 'incl_erab_orig': False})
    elif args['source'] == 'cluster' and args['nb'] == 1:
        result['map'] = config.VISUALIZATIONS_URL \
            + '?vis=map_poem_cluster&' \
            + urlencode({'nro': args['nro'][0]})
        result['types'] = config.VISUALIZATIONS_URL \
            + '?vis=tree_poem_cluster&' \
            + urlencode({'nro': args['nro'][0], 'incl_erab_orig': False})
    return result


# transform linkages to a vertical dendrogram
def transform_vert(dd, n, nros):

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
            nros1 = [nros[int(dd[i,0])]] if dd[i,0] < n else result[int(dd[i,0])-n][6]
            nros2 = [nros[int(dd[i,1])]] if dd[i,1] < n else result[int(dd[i,1])-n][6]
            result.append((x1, y1, x2, y2, x, y, nros1+nros2))
    return result


def render(**args):
    poems, types, inner = None, None, None
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        if args['source'] == 'theme':
            types = Types(ids=[args['theme_id']])
            types.get_descriptions(db)
            nros, minor_nros = types.get_poem_ids(db, minor=True)
            poems = Poems(nros=nros+minor_nros)
            types.get_ancestors(db, add=True)
            types.get_names(db)
        elif args['source'] == 'cluster':
            poems = Poems(nros=[args['nro'][0]])
            poems.get_poem_cluster_info(db)
            poems = Poems.get_by_cluster(db, poems[args['nro'][0]].p_clust_id)
            poems.get_poem_cluster_info(db)
        elif args['source'] == 'nros':
            poems = Poems(nros=args['nro'])
        inner = set(poems)
        if args['nb'] is not None and args['nb'] < 1:
            poems.get_similar_poems(db, sim_thr=args['nb'])
            new_nros = set(poems)
            for nro in poems:
                for s in poems[nro].sim_poems:
                    new_nros.add(s.nro)
            poems = Poems(nros=new_nros)
        poems.get_structured_metadata(db)
        poems.get_similar_poems(db, within=True)

    d = sim_to_dist(make_sim_mtx(poems))
    clust = cluster(d, args['method'])
    ll = scipy.cluster.hierarchy.leaves_list(clust)
    dd = transform_vert(clust, len(poems), list(poems))
    data = {
        'poems': poems,
        'nros': list(poems),
        'types': types,
        'inner': inner,
        'll': ll, 'dd': dd, 'n': len(poems)
    }
    links = generate_page_links(args) 
    return render_template('dendrogram.html', args=args, data=data, links=links)

