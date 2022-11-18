def search_verses(db, q, method, limit):
    result = []
    db.execute(\
        'SELECT nro, pos, text FROM verses'
        ' NATURAL JOIN verse_poem'
        ' NATURAL JOIN poems'
        ' WHERE text {} %s LIMIT %s;'\
        .format('LIKE' if method == 'plain' else 'REGEXP'),
        (('%{}%'.format(q) if method == 'plain' else q),
         limit))
    result = db.fetchall()
    return result


def search_themes(db, q, method, limit):
    result = []
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
       limit))
    result = [(r[3], r[4], r[5],
               [r[i] for i in range(3) if r[i]]) \
              for r in db.fetchall()]
    return result


def search_meta(db, q, method, limit):
    result = []
    db.execute(\
        'SELECT nro, field, value FROM raw_meta'
        ' NATURAL JOIN poems'
        ' WHERE value {} %s LIMIT %s;'\
        .format('LIKE' if method == 'plain' else 'REGEXP'),
        (('%{}%'.format(q) if method == 'plain' else q),
         limit))
    result = db.fetchall()
    return result

