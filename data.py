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


class Poem:
    def __init__(self, so_id, nro, loc, col, year, meta, topics, verses, refs=None):
        self.so_id = so_id
        self.nro = nro
        self.loc = loc
        self.col = col
        self.year = year
        self.meta = meta
        self.topics = topics
        self.verses = verses
        self.refs = refs

    def text_verses(self):
        return (v for v in self.verses if v.type == 'V')

    @staticmethod
    def from_db(cursor, so_id, fmt='mysql'):
        cursor.execute(
            'SELECT nro, region, name, collector, year FROM sources'
            ' NATURAL JOIN locations'
            ' NATURAL JOIN collectors'
            ' WHERE so_id = %s;',
            (so_id,))
        nro, loc_reg, loc_name, col, year = cursor.fetchall()[0]
        query = _format_query(
            'SELECT v.v_id, v.type, v.text, cf.freq FROM verses v'\
            ' JOIN v_so ON v_so.v_id = v.v_id'\
            ' LEFT OUTER JOIN v_clust vc ON v_so.v_id = vc.v_id'\
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
        cursor.execute(
            'SELECT f.code, t.code, f.title, t.title_1 FROM so_type st'
            ' JOIN types t ON st.t_id = t.t_id'
            ' JOIN files f ON t.f_id = f.f_id'
            ' WHERE st.so_id = %s;',
            (so_id,))
        topics = cursor.fetchall()
        query = _format_query(
            'SELECT refs FROM so_refs WHERE so_id = %s', fmt)
        cursor.execute(query, (so_id,))
        result = cursor.fetchall()
        refs = result[0][0] if result else None
        return Poem(so_id, nro, (loc_reg, loc_name), col, year,
                    meta, topics, verses, refs)

    @staticmethod
    def from_db_by_nro(cursor, nro, fmt='mysql'):
        query = _format_query('SELECT so_id FROM sources WHERE nro=%s;', fmt)
        cursor.execute(query, (nro,))
        so_id = cursor.fetchall()[0]
        return Poem.from_db(cursor, so_id, fmt)
