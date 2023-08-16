from collections import defaultdict
from flask import render_template
import pymysql

import config
from data.logging import profile
from data.search import search_meta, search_types, search_verses
from data.types import get_nonleaf_categories, render_type_tree, Types


DEFAULTS = {
  'q': None,
  'method': 'plain',
  'verses': False,
  'types': False,
  'meta': False,
}


@profile
def render(**args):
    maintenance = config.check_maintenance()
    if args['q'] is None:
        with pymysql.connect(**config.MYSQL_PARAMS) as db:
            types = get_nonleaf_categories(db)
            # FIXME hardcoding Kanteletar's table of contents for now,
            # should be handled more flexibly later
            if config.TABLES['types']:
                types_kt = Types(ids=['kt_t010000', 'kt_t020000', 'kt_t030000'])
                types_kt.get_descendents(db, add=True)
                types_kt.get_names(db)
            else:
                types_kt = Types(ids=[])
        tree = { 'skvr': [], 'erab': [] , 'kt': render_type_tree(types_kt) }
        for line in render_type_tree(types):
            tree[line.type_id[:line.type_id.index('_')]].append(line)
        types = Types(types = [t for t in list(types.values()) + list(types_kt.values()) ])
        data = { 'tree': tree, 'types': types,
                 'logging_enabled': config.ENABLE_LOGGING_TO_DB,
                 'maintenance': maintenance }
        return render_template('search_idx.html', data = data)
    else:
        r_verses, r_types, r_meta = [], [], []
        with pymysql.connect(**config.MYSQL_PARAMS) as db:
            r_types = search_types(db, args['q'])
            r_meta = search_meta(db, args['q'])
            r_verses = search_verses(db, args['q'])
        data = { 'r_verses': r_verses, 'r_types': r_types, 'r_meta': r_meta,
                 'limit': config.SEARCH_LIMIT, 'maintenance': maintenance }
        return render_template('search_results.html', args=args, data=data, links={})

