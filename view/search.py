from collections import defaultdict
from flask import render_template
import pymysql

import config


def get_root_categories():
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        themes = defaultdict(lambda: list())
        db.execute(\
            'SELECT theme_id, name FROM themes'
            ' WHERE par_id = 0 AND (LENGTH(theme_id) = 8 OR theme_id LIKE "kt_t%");')
        for theme_id, name in db.fetchall():
            if theme_id.startswith('skvr_'):
                themes['skvr'].append((theme_id, name))
            elif theme_id.startswith('erab_'):
                themes['erab'].append((theme_id, name))
            elif theme_id.startswith('kt_t'):
                themes['kanteletar'].append((theme_id, name))
    return themes


def search_verses(q, method):
    result = []
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        db.execute(\
            'SELECT nro, pos, text FROM verses'
            ' NATURAL JOIN verse_poem'
            ' NATURAL JOIN poems'
            ' WHERE text {} %s LIMIT %s;'\
            .format('LIKE' if method == 'plain' else 'REGEXP'),
            (('%{}%'.format(q) if method == 'plain' else q),
             config.SEARCH_LIMIT))
        result = db.fetchall()
    return result


def search_themes(q, method):
    result = []
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        db.execute(\
          'SELECT t4.name, t3.name, t2.name, t1.theme_id, t1.name,'
          '       t1.description'
          ' FROM themes t1'
          '  LEFT OUTER JOIN themes t2 on t1.par_id = t2.t_id'
          '  LEFT OUTER JOIN themes t3 on t2.par_id = t3.t_id'
          '  LEFT OUTER JOIN themes t4 on t3.par_id = t4.t_id'
          ' WHERE t1.name {} %s LIMIT %s;'\
          .format('LIKE' if method == 'plain' else 'REGEXP'),
          (('%{}%'.format(q) if method == 'plain' else q),
           config.SEARCH_LIMIT))
        result = [(r[3], r[4], r[5],
                   [r[i] for i in range(3) if r[i]]) \
                  for r in db.fetchall()]
    return result


def search_meta(q, method):
    result = []
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        db.execute(\
            'SELECT nro, field, value FROM raw_meta'
            ' NATURAL JOIN poems'
            ' WHERE value {} %s LIMIT %s;'\
            .format('LIKE' if method == 'plain' else 'REGEXP'),
            (('%{}%'.format(q) if method == 'plain' else q),
             config.SEARCH_LIMIT))
        result = db.fetchall()
    return result


def render(**args):
    if args['q'] is None:
        return render_template('search_idx.html', cat = get_root_categories())
    else:
        r_verses, r_themes, r_meta = [], [], []
        if args['verses']:
            r_verses = search_verses(args['q'], args['method'])
        if args['themes']:
            r_themes = search_themes(args['q'], args['method'])
        if args['meta']:
            r_meta = search_meta(args['q'], args['method'])
        data = { 'r_verses': r_verses, 'r_themes': r_themes, 'r_meta': r_meta,
                 'limit': config.SEARCH_LIMIT }
        return render_template('search_results.html', args=args, data=data, links={})

