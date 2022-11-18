from collections import defaultdict
from flask import render_template
import pymysql

import config
from data.search import search_meta, search_themes, search_verses
from data.types import get_root_categories


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
            types = get_root_categories(db)
            types.get_names(db)
        cat = defaultdict(list)
        for type_id, t in types.items():
            if type_id.startswith('skvr_'):
                cat['skvr'].append(t)
            elif type_id.startswith('erab_'):
                cat['erab'].append(t)
            elif type_id.startswith('kt_t'):
                cat['kanteletar'].append(t)
        return render_template('search_idx.html', cat = cat)
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

