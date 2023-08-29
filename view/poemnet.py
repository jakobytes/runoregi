from flask import render_template
from operator import itemgetter
import pymysql

import config
from data.logging import profile
from data.poems import Poems
from utils import link


DEFAULTS = {
  'nro': [],
  'maxdepth': 1,
  'maxnodes': 20,
  't': 0.1,
}


def generate_page_links(args):
    global DEFAULTS

    def pagelink(**kwargs):
        return link('poemnet', dict(args, **kwargs), DEFAULTS)

    result = { 'maxdepth': {}, 'maxnodes': {}, 't': {} }
    for val in [1, 2, 3, 4, 5, 6]:
        result['maxdepth'][val] = pagelink(maxdepth=val)
    for val in [10, 20, 30, 50, 70, 100, 150, 200]:
        result['maxnodes'][val] = pagelink(maxnodes=val)
    for val in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]:
        result['t'][val] = pagelink(t=val)
    return result


def get_poem_network(db, poems, t=0.1, maxdepth=3, maxnodes=30):
    poem_depth = { nro: 0 for nro in poems }
    depth = 0
    while depth < maxdepth and len(poems) < maxnodes:
        # get candidates for new nodes
        poems.get_similar_poems(db, sim_thr=t)
        sims = []
        sims.extend([s for p in poems.values() for s in p.sim_poems \
                           if s.nro not in poems])
        sims.sort(reverse=True, key=lambda s: s.sim_al)
        # for each new poem, store only the highest similarity
        sims_dict = {}
        for s in sims:
            if s.nro not in sims_dict:
                sims_dict[s.nro] = s
        # apply the limit on the number of nodes -- choose the best new nodes
        sims = list(sims_dict.values())[:maxnodes-len(poems)]
        depth += 1
        for s in sims:
            poem_depth[s.nro] = depth
        poems = Poems(nros = list(poems) + [s.nro for s in sims])

    poems.get_similar_poems(db, sim_thr=t, within=True)
    edges = []
    for nro, p in poems.items():
        for s in p.sim_poems:
            if poem_depth[nro] < poem_depth[s.nro]:
                edges.append((nro, s.nro, s.sim_al))

    return { 'nodes': poems, 'edges': edges }


@profile
def render(**args):
    poemnet, smd = None, None
    poems = Poems(nros=args['nro'])
    with pymysql.connect(**config.MYSQL_PARAMS).cursor() as db:
        poemnet = get_poem_network(
            db, poems, t=args['t'],
            maxdepth=args['maxdepth'], maxnodes=args['maxnodes'])
        poemnet['nodes'].get_structured_metadata(db)
        types = poemnet['nodes'].get_types(db)
        types.get_names(db)
    links = generate_page_links(args)
    data = { 'poemnet': poemnet, 'types': types,
             'maintenance': config.check_maintenance() }
    return render_template('poemnet.html', args=args, data=data, links=links)

