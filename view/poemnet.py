from flask import render_template
from operator import itemgetter
import pymysql

import config
from data import get_structured_metadata, render_themes_tree


DEFAULTS = {
  'maxdepth': 1,
  'maxnodes': 20,
  't': 0.1,
}


def get_poem_network(db, nros, t=0.1, maxdepth=3, maxnodes=30):
    depth = 0
    db.execute('SELECT p_id FROM poems WHERE nro IN ({})'\
               .format(','.join('"{}"'.format(nro) for nro in nros)))
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


# TODO merge with view.poem.link()?
def link(nro, options, defaults):
    'Generates a link to the same view with specified option settings.'

    def _str(value):
        if isinstance(value, list):
            return ','.join(map(str, value))
        elif isinstance(value, bool):
            return str(value).lower()
        else:
            return str(value)

    link = '/poemnet?nro={}'.format(_str(nro))
    opt_str = '&'.join('{}={}'.format(key, _str(options[key]))
                       for key in options if options[key] != defaults[key])
    if opt_str:
        return link + '&' + opt_str
    else:
        return link


def generate_page_links(nro, options, defaults):
    return {
        '+depth':
            link(nro, dict(options, maxdepth=options['maxdepth']+1), defaults),
        '-depth':
            link(nro, dict(options, maxdepth=max(0, options['maxdepth']-1)), defaults),
        '+nodes':
            link(nro, dict(options, maxnodes=options['maxnodes']+10), defaults),
        '-nodes':
            link(nro, dict(options, maxnodes=max(0, options['maxnodes']-10)), defaults),
        '+threshold':
            link(nro, dict(options, t=min(1, options['t']+0.05)), defaults),
        '-threshold':
            link(nro, dict(options, t=max(0, options['t']-0.05)), defaults),
    }


def render(nro, **options):
    nros = nro.split(',')
    poemnet, smd = None, None
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        poemnet = get_poem_network(db, nros, **options)
        smd = get_structured_metadata(db, p_ids=poemnet['nodes'])
    tt = { md.p_id: '\n'.join(t[-2][1] if t[-1][0] == '*' else t[-1][1] \
                              for t in md.themes if t != [('',)]) \
                    for md in smd }
    nros_by_id = { md.p_id : md.nro for md in smd }
    links = generate_page_links(nros, options, DEFAULTS)
    return render_template('poemnet.html', nro=nros, poemnet=poemnet, smd=smd,
                           tt=tt, nros_by_id=nros_by_id, links=links)
