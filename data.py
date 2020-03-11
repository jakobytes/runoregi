def _format_query(query, fmt):
    if fmt == 'sqlite':
        return query.replace('%s', '?')
    elif fmt == 'mysql':
        return query
    else:
        raise Exception('Unknown query format: {}'.format(fmt))

class Verse:
    def __init__(self, v_id, type, text):
        self.v_id = v_id
        self.type = type
        self.text = text

    @staticmethod
    def from_db(cursor, v_id):
        raise NotImplementedError()


class Runo:
    def __init__(self, so_id, verses):
        self.so_id = so_id
        self.verses = verses

    def text_verses(self):
        return (v for v in self.verses if v.type == 'V')

    @staticmethod
    def from_db(cursor, so_id, fmt='mysql'):
        query = _format_query(
            'SELECT v.v_id, v.type, v.text FROM verses v'\
            ' JOIN v_so ON v_so.v_id = v.v_id'\
            ' WHERE v_so.so_id=%s;',
            fmt)
        cursor.execute(query, (so_id,))
        verses = [Verse(v_id, type, text) \
                  for v_id, type, text in cursor.fetchall()]
        return Runo(so_id, verses)

    @staticmethod
    def from_db_by_nro(cursor, nro, fmt='mysql'):
        query = _format_query('SELECT so_id FROM sources WHERE nro=%s;', fmt)
        cursor.execute(query, (nro,))
        so_id = cursor.fetchall()[0]
        return Runo.from_db(cursor, so_id, fmt)
