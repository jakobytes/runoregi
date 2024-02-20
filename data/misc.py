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

