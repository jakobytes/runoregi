from collections import namedtuple

CollectorData = namedtuple('CollectorData', ['id', 'name'])
PlaceData = namedtuple('PlaceData', ['county_id', 'county_name', 'parish_id', 'parish_name'])


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


def get_collector_data(db, col_id):
    db.execute('SELECT name FROM collectors WHERE col_orig_id = %s;', (col_id,))
    try:
        return CollectorData(col_id, db.fetchall()[0][0])
    except IndexError:
        return CollectorData(None, None)


def get_place_data(db, place_id):
    db.execute(\
      'SELECT pl1.name, pl2.place_orig_id, pl2.name'
      ' FROM places pl1'
      '   LEFT JOIN places pl2 ON pl1.par_id = pl2.pl_id'
      ' WHERE pl1.place_orig_id = %s;', (place_id,))
    try:
        result = db.fetchall()[0]
        if result[1] is not None and result[2] is not None:
            return PlaceData(result[1], result[2], place_id, result[0])
        else:
            return PlaceData(place_id, result[0], None, None)
    except IndexError:
        return PlaceData(None, None, None, None)

