from collections import defaultdict
from flask import render_template
import pymysql

import config
from data.search import search_meta, search_themes, search_verses
from data.types import get_nonleaf_categories, render_type_tree, Types


DEFAULTS = {
  'q': None,
  'method': 'plain',
  'verses': False,
  'themes': False,
  'meta': False,
}


def render(**args):
    if args['q'] is None:
        with pymysql.connect(**config.MYSQL_PARAMS) as db:
            types = get_nonleaf_categories(db)
            types_kt = Types(ids=['kt_t010000', 'kt_t020000', 'kt_t030000'])
            types_kt.get_descendents(db, add=True)
            types_kt.get_names(db)
        tree = { 'skvr': [], 'erab': [] , 'kt': render_type_tree(types_kt) }
        for line in render_type_tree(types):
            tree[line.type_id[:line.type_id.index('_')]].append(line)
        types = Types(types = [t for t in list(types.values()) + list(types_kt.values()) ])
        data = { 'tree': tree, 'types': types }
        return render_template('search_idx.html', data = data)
    else:
        r_verses, r_themes, r_meta = [], [], []
        with pymysql.connect(**config.MYSQL_PARAMS) as db:
            if args['verses']:
                r_verses = search_verses(db, args['q'], args['method'],
                                         config.SEARCH_LIMIT)
            if args['themes']:
                r_themes = search_themes(db, args['q'], args['method'],
                                         config.SEARCH_LIMIT)
            if args['meta']:
                r_meta = search_meta(db, args['q'], args['method'],
                                     config.SEARCH_LIMIT)
        data = { 'r_verses': r_verses, 'r_themes': r_themes, 'r_meta': r_meta,
                 'limit': config.SEARCH_LIMIT }
        return render_template('search_results.html', args=args, data=data, links={})

