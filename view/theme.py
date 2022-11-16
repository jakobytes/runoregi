from collections import defaultdict
from flask import render_template
from operator import itemgetter
import pymysql

import config
from data import get_structured_metadata, render_themes_tree


DEFAULTS = { 'id': None }


def render(**args):
    subcat, poems, smd = [], [], []
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        db.execute(\
          'SELECT t4.theme_id, t4.name, t3.theme_id, t3.name,'
          '       t2.theme_id, t2.name, t1.theme_id, t1.name,'
          '       t1.description'
           ' FROM themes t1'
           '  LEFT OUTER JOIN themes t2 on t1.par_id = t2.t_id'
           '  LEFT OUTER JOIN themes t3 on t2.par_id = t3.t_id'
           '  LEFT OUTER JOIN themes t4 on t3.par_id = t4.t_id'
           ' WHERE t1.theme_id = %s;', (args['id'],));
        r = db.fetchall()[0]
        upper = [(r[2*i], r[2*i+1]) for i in range(3) if r[2*i] is not None]
        name = r[7]
        desc = r[8]
        db.execute(\
          'SELECT GROUP_CONCAT(DISTINCT'
           '  CONCAT(IFNULL(CONCAT(t2.theme_id, "@", t2.name), ""),'
	       '         IFNULL(CONCAT("::", t3.theme_id, "@", t3.name), ""),'
	       '         IFNULL(CONCAT("::", t4.theme_id, "@", t4.name), ""))'
           '  SEPARATOR ";;;")'
           ' FROM themes t1'
           '  LEFT OUTER JOIN themes t2 on t1.t_id = t2.par_id'
           '  LEFT OUTER JOIN themes t3 on t2.t_id = t3.par_id'
           '  LEFT OUTER JOIN themes t4 on t3.t_id = t4.par_id'
           ' WHERE t1.theme_id = %s;', (args['id'],));
        subcat_str = db.fetchall()
        if subcat_str and subcat_str[0][0]:
            subcat_lst = sorted(
                [tuple(t.split('@')) for t in tt.split('::')] \
                for tt in subcat_str[0][0].split(';;;'))
            subcat = render_themes_tree(subcat_lst)
        db.execute(\
            'SELECT p_id, is_minor FROM poem_theme'
            ' NATURAL JOIN themes'
            ' WHERE theme_id = %s;',
            (args['id'],))
        poems = list(db.fetchall())
        poem_ids = list(map(itemgetter(0), poems))
        if poem_ids:
            smd = get_structured_metadata(db, p_ids = poem_ids)
    data = { 'name': name, 'desc': desc,
             'upper': upper, 'subcat': subcat, 'poems': list(zip(poems, smd)) }
    return render_template('theme.html', args=args, data=data, links={})

