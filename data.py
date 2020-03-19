def _format_query(query, fmt):
    if fmt == 'sqlite':
        return query.replace('%s', '?')
    elif fmt == 'mysql':
        return query
    else:
        raise Exception('Unknown query format: {}'.format(fmt))

class Verse:
    def __init__(self, v_id, type, text, clustfreq):
        self.v_id = v_id
        self.type = type
        self.text = text
        self.clustfreq = clustfreq

    @staticmethod
    def from_db(cursor, v_id):
        raise NotImplementedError()


class Runo:
    def __init__(self, so_id, meta, verses):
        self.so_id = so_id
        self.meta = meta
        self.verses = verses

    def text_verses(self):
        return (v for v in self.verses if v.type == 'V')

    @staticmethod
    def from_db(cursor, so_id, fmt='mysql'):
        query = _format_query(
            'SELECT v.v_id, v.type, v.text, cf.freq FROM verses v'\
            ' JOIN v_so ON v_so.v_id = v.v_id'\
            ' JOIN v_clust vc ON v_so.v_id = vc.v_id'\
            ' JOIN v_clust_freq cf ON vc.clust_id = cf.clust_id'\
            ' WHERE v_so.so_id=%s;',
            fmt)
        cursor.execute(query, (so_id,))
        verses = [Verse(v_id, type, text, cf) \
                  for v_id, type, text, cf in cursor.fetchall()]
        query = _format_query(
            'SELECT field, value FROM so_meta WHERE so_id = %s', fmt)
        cursor.execute(query, (so_id,))
        meta = { field : value for field, value in cursor.fetchall() }
        return Runo(so_id, meta, verses)

    @staticmethod
    def from_db_by_nro(cursor, nro, fmt='mysql'):
        query = _format_query('SELECT so_id FROM sources WHERE nro=%s;', fmt)
        cursor.execute(query, (nro,))
        so_id = cursor.fetchall()[0]
        return Runo.from_db(cursor, so_id, fmt)
