from collections import namedtuple


StructuredMetadata = \
    namedtuple('StructuredMetadata',
               ['p_id', 'nro', 'title', 'location', 'collector', 'year', 'themes'])


# TODO if getting by clust_id -> also verse ID and text!
def get_structured_metadata(
        db, p_id = None, p_ids = None, clust_id = None, nro = None,
        title = False, location = False, collector = False, year = False,
        themes = False):
    query_lst = [
        'SELECT DISTINCT p_id, nro,',
        'nro,',
        '"no location",',
        '"no collector",',
        '"no year",',
        '""',
        'FROM poems']
    if p_id is not None:
        query_lst.append('WHERE p_id = {}'.format(p_id))
    elif p_ids is not None:
        query_lst.append('WHERE p_id IN ({})'.format(','.join(map(str, p_ids))))
    elif nro is not None:
        query_lst.append('WHERE nro = "{}"'.format(nro))
    elif clust_id is not None:
        query_lst.extend([
            'NATURAL JOIN verse_poem',
            'NATURAL JOIN v_clust',
            'WHERE clust_id = {}'.format(clust_id)
        ])
    else:
        raise Exception('Either p_id or clust_id or nro or p_ids must be supplied!')
    print(' '.join(query_lst))
    db.execute(' '.join(query_lst))
    results = []
    for p_id, nro, title, loc, col, year, themes_str in db.fetchall():
        themes = themes_str.split(';;;') if themes_str else []
        results.append(StructuredMetadata(p_id, nro, title, loc, col, year, themes))
    return results


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
    def __init__(self, p_id, smd, meta, verses, refs=None):
        self.p_id = p_id
        self.smd = smd          # StructuredMetadata
        self.meta = meta        # unstructured metadata
        self.verses = verses
        self.refs = refs

    def text_verses(self):
        return (v for v in self.verses if v.type == 'V')

    @staticmethod
    def from_db(db, p_id):
        # cursor.execute(
        #     'SELECT nro, region, name, collector, year FROM sources'
        #     ' NATURAL JOIN locations'
        #     ' NATURAL JOIN collectors'
        #     ' WHERE so_id = %s;',
        #     (so_id,))
        db.execute(
            'SELECT nro, "No region", "No name", "No collector", "No year" FROM poems'
            ' WHERE p_id = %s;',
            (p_id,))
        nro, loc_reg, loc_name, col, year = db.fetchall()[0]
        db.execute( 
            'SELECT v.v_id, v.type, v.text, cf.freq FROM verses v'\
            ' JOIN verse_poem vp ON vp.v_id = v.v_id'\
            ' LEFT OUTER JOIN v_clust vc ON vp.v_id = vc.v_id'\
            ' LEFT OUTER JOIN v_clust_freq cf ON vc.clust_id = cf.clust_id'\
            ' WHERE vp.p_id=%s;',
            (p_id,))
        #db.execute(query, (p_id,))
        verses = [Verse(v_id, type, text, cf) \
                  for v_id, type, text, cf in db.fetchall()]
        # query = _format_query(
        #     'SELECT field, value FROM so_meta WHERE so_id = %s', fmt)
        # cursor.execute(query, (so_id,))
        # meta = { field : value for field, value in cursor.fetchall() }
        meta = { 'OSA': None, }
        # cursor.execute(
        #     'SELECT f.code, t.code, f.title, t.title_1 FROM so_type st'
        #     ' JOIN types t ON st.t_id = t.t_id'
        #     ' JOIN files f ON t.f_id = f.f_id'
        #     ' WHERE st.so_id = %s;',
        #     (so_id,))
        # topics = cursor.fetchall()
        topics = []
        # query = _format_query(
        #     'SELECT refs FROM so_refs WHERE so_id = %s', fmt)
        # cursor.execute(query, (so_id,))
        # result = cursor.fetchall()
        # refs = result[0][0] if result else None
        smd = get_structured_metadata(db, nro=nro)[0]
        refs = ''
        return Poem(p_id, smd, meta, verses, refs)

    @staticmethod
    def from_db_by_nro(db, nro):
        #query = _format_query('SELECT p_id FROM poems WHERE nro=%s;', fmt)
        db.execute('SELECT p_id FROM poems WHERE nro=%s;', (nro,))
        p_id = db.fetchall()[0]
        return Poem.from_db(db, p_id)

