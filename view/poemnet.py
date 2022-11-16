from flask import render_template
from operator import itemgetter
import pymysql

import config
from data import get_structured_metadata, render_themes_tree
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

    return {
        '+maxdepth':
            pagelink(maxdepth=args['maxdepth']+1),
        '-maxdepth':
            pagelink(maxdepth=max(0, args['maxdepth']-1)),
        '+nodes':
            pagelink(maxnodes=args['maxnodes']+10),
        '-nodes':
            pagelink(maxnodes=max(0, args['maxnodes']-10)),
        '+threshold':
            pagelink(t=min(1, args['t']+0.05)),
        '-threshold':
            pagelink(t=max(0, args['t']-0.05)),
    }


def get_poem_network(db, nro=None, t=0.1, maxdepth=3, maxnodes=30):
    depth = 0
    db.execute('SELECT p_id FROM poems WHERE nro IN ({})'\
               .format(','.join('"{}"'.format(x) for x in nro)))
    nodes = list(map(itemgetter(0), db.fetchall()))
    nodes_set = set(nodes)
    while depth < maxdepth and len(nodes) < maxnodes:
        depth += 1
        nodes_str = ', '.join(map(str, nodes))
        query = 'SELECT DISTINCT p2_id FROM p_sim s WHERE p1_id IN ({}) AND sim_al > {} ORDER BY sim_al DESC LIMIT %s;'\
                .format(nodes_str, t)
        db.execute(query, maxnodes)
        for row in db.fetchall():
            if row[0] not in nodes_set:
                nodes_set.add(row[0])
                nodes.append(row[0])
    nodes_str = ', '.join(map(str, nodes))
    query = \
        '''SELECT
          p1_id, p2_id, sim_al
         FROM
           p_sim
         WHERE
           p1_id IN ({})
           AND p2_id IN ({})
           AND sim_al > {}
         ;'''\
        .format(nodes_str, nodes_str, t)
    db.execute(query)
    edges = db.fetchall()
    return { 'nodes': nodes, 'edges': edges }


def render(**args):
    poemnet, smd = None, None
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        poemnet = get_poem_network(db, **args)
        smd = get_structured_metadata(db, p_ids=poemnet['nodes'])
    tt = { md.p_id: '\n'.join(t[-2][1] if t[-1][0] == '*' else t[-1][1] \
                              for t in md.themes if t != [('',)]) \
                    for md in smd }
    nros_by_id = { md.p_id : md.nro for md in smd }
    links = generate_page_links(args)
    data = {
        'poemnet': poemnet,
        'smd': smd,
        'tt': tt,
        'nros_by_id': nros_by_id
    }
    return render_template('poemnet.html', args=args, data=data, links=links)

