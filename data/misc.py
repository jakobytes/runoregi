# Pick a single value from the query results
def _scalar(data):
    if data and isinstance(data[0], tuple):
        return data[0][0]
    else:
        return None

def get_parishes(db, place_id):
  db.execute(\
    'SELECT plp.place_orig_id, plp.name, SUM(pls.npoems)'
    ' FROM places plp'
    '   JOIN places plc ON plp.par_id = plc.pl_id'
    '   JOIN place_stats pls ON pls.pl_id = plp.pl_id'
    ' WHERE plp.type = "parish" AND plc.place_orig_id = %s'
    ' GROUP BY plp.pl_id;',
    (place_id,))
  return list(db.fetchall())

def get_collector_name (db, col_id):
    db.execute('SELECT name FROM collectors WHERE col_orig_id = %s;', (col_id,))
    return _scalar(list(db.fetchall()))

def get_place_name(db, place_id):
    db.execute('SELECT name FROM places WHERE place_orig_id = %s;', (place_id,))
    return _scalar(list(db.fetchall()))

