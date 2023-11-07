from collections import defaultdict
from flask import render_template
from operator import itemgetter
import pymysql
from urllib.parse import urlencode

import config
from data.logging import profile
from data.poems import Poems
from data.types import Types, render_type_tree


DEFAULTS = { 'source': None, 'id': None }


def get_by_type(db, type_id):
    upper = Types(ids=[type_id])
    nros, minor_nros = upper.get_poem_ids(db, minor=True)
    poems = None
    if nros or minor_nros:
        poems = Poems(nros=nros+minor_nros)
        poems.get_structured_metadata(db)
    upper.get_descriptions(db)
    upper.get_ancestors(db, add=True)
    upper.get_names(db)
    subcat = Types(ids=[type_id])
    subcat.get_descriptions(db)
    subcat.get_descendents(db, add=True)
    subcat.get_names(db)

    tree = render_type_tree(subcat)
    # remove the top hierarchy level from the tree
    tree.pop(0)
    for line in tree:
        line.prefix.pop(0)
    types = Types(types=[upper[t] for t in upper] + \
                        [subcat[t] for t in subcat if t != type_id])
    return { 'poems': poems,
             'types': types,
             'minor': set(minor_nros), 
             'tree': tree
           }


@profile
def render(**args):
    data = {}
    with pymysql.connect(**config.MYSQL_PARAMS).cursor() as db:
        if args['source'] == 'type':
            data = get_by_type(db, args['id'])

    data['maintenance'] = config.check_maintenance()

    links = {}
    if args['source'] == 'type':
        links['map'] = config.VISUALIZATIONS_URL + '/?vis=map_type&' \
            + urlencode({'type_id': args['id']}) \
            if config.VISUALIZATIONS_URL else None,
        links['cooc-types'] = config.VISUALIZATIONS_URL + '?vis=tree_types_cooc&' \
            + urlencode({'type_id': args['id'], 'include_erab_orig': False}) \
            if config.VISUALIZATIONS_URL else None

    return render_template('poemlist.html', args=args, data=data, links=links)

