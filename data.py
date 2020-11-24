from collections import namedtuple
from operator import itemgetter


StructuredMetadata = \
    namedtuple('StructuredMetadata',
               ['p_id', 'nro', 'title', 'location', 'collector', 'year', 'themes'])


def render_themes_tree(themes):

    def _themes_to_lines(themes):
        lines = []
        current = []
        for theme_lst in themes:
            # if the last element of a list is '*', it's a "minor" theme
            # that will be specially marked in the UI
            minor = False
            if theme_lst[-1] == '*':
                minor = True
                theme_lst.pop()
            for i, t in enumerate(theme_lst):
                if i >= len(current) or t != current[i]:
                    pref = ['│'] * (i-1) + ['├'] * (i > 0)
                    if i == len(theme_lst)-1:
                        # only the leaf node is marked as "minor"
                        lines.append((i, pref, minor, t))
                    else:
                        lines.append((i, pref, False, t))
                    current = current[:i] + [t]
        return lines

    def _fix_prefixes(lines):
        # this removes the tree branches ("|") that lead nowhere
        max_d = max(lines, key=itemgetter(0))[0]
        for i in range(len(lines)-1, -1, -1):
            d = lines[i][0]
            next_d = lines[i+1][0] if i+1 < len(lines) else 0
            if next_d < d:
                for j in range(next_d, d-1):
                    lines[i][1][j] = ' '
            if i+1 < len(lines):
                for j in range(d-1):
                    if j < next_d and lines[i+1][1][j] == ' ':
                        lines[i][1][j] = ' '
            if d > 0 and (d > next_d or lines[i+1][1][d-1] == ' '):
                lines[i][1][d-1] = '└'

    lines = _themes_to_lines(themes)
    _fix_prefixes(lines)
    return lines


def get_structured_metadata(
        db, p_id = None, p_ids = None, clust_id = None, nro = None,
        title = True, location = True, collector = True, year = True,
        themes = True):

    def _make_title(nro, osa, _id):
        if nro.startswith('skvr'):
            return 'SKVR {} {}'.format(osa, _id)
        else:
            return _id

    query_lst = [
        'SELECT DISTINCT poems.p_id, nro,',
        ('rm_osa.value as osa, rm_id.value as id,' if title else '"", "",'),
        ('GROUP_CONCAT(DISTINCT CONCAT(l.region, " — ", l.name)'
         ' SEPARATOR "; "),'\
         if location else '"no location",'),
        ('GROUP_CONCAT(DISTINCT c.name SEPARATOR "; "),'\
         if collector else '"no collector",'),
        ('year,' if year else '"no year",'),
        ('GROUP_CONCAT(DISTINCT'
         '  CONCAT(IFNULL(CONCAT(t4.name, "::"), ""),'
	     '         IFNULL(CONCAT(t3.name, "::"), ""),'
         '         IFNULL(CONCAT(t2.name, "::"), ""),'
         '         IFNULL(t1.name, ""),'
         '         IF(pt.is_minor OR (t1.theme_id LIKE "orig%"), "::*", ""))'
         '  SEPARATOR ";;;")' if themes else '""'),
        'FROM poems']
    if title:
        query_lst.extend([
          'LEFT OUTER JOIN raw_meta rm_osa'
          '  ON poems.p_id = rm_osa.p_id AND rm_osa.field = "OSA"',
          'LEFT OUTER JOIN raw_meta rm_id'
          '  ON poems.p_id = rm_id.p_id AND rm_id.field = "ID"',
        ])
    if location:
        query_lst.extend([
          'LEFT OUTER JOIN p_loc ON poems.p_id = p_loc.p_id',
          'LEFT OUTER JOIN locations l ON p_loc.loc_id = l.loc_id'
        ])
    if collector:
        query_lst.extend([
          'LEFT OUTER JOIN p_col ON poems.p_id = p_col.p_id',
          'LEFT OUTER JOIN collectors c ON p_col.col_id = c.col_id'
        ])
    if year:
        query_lst.append('LEFT OUTER JOIN p_year ON poems.p_id = p_year.p_id')
    if themes:
        query_lst.extend([
          'LEFT OUTER JOIN poem_theme pt on pt.p_id = poems.p_id',
          'LEFT OUTER JOIN themes t1 on pt.t_id = t1.t_id',
          'LEFT OUTER JOIN themes t2 on t1.par_id = t2.t_id',
          'LEFT OUTER JOIN themes t3 on t2.par_id = t3.t_id',
          'LEFT OUTER JOIN themes t4 on t3.par_id = t4.t_id',
        ])
    if p_id is not None:
        query_lst.append('WHERE poems.p_id = {}'.format(p_id))
    elif p_ids is not None:
        query_lst.append('WHERE poems.p_id IN ({})'.format(','.join(map(str, p_ids))))
    elif nro is not None:
        query_lst.append('WHERE nro = "{}"'.format(nro))
    elif clust_id is not None:
        query_lst.extend([
            'JOIN verse_poem vp ON vp.p_id = poems.p_id',
            'NATURAL JOIN v_clust',
            'WHERE clust_id = {}'.format(clust_id)
        ])
    else:
        raise Exception('Either of: (p_id, p_ids, clust_id, nro) must be specified!')
    if location or collector or themes:
        query_lst.append('GROUP BY poems.p_id')
    db.execute(' '.join(query_lst))
    results = []
    for p_id, nro, osa, _id, loc, col, year, themes_str in db.fetchall():
        themes = sorted(t.split('::') for t in themes_str.split(';;;'))
        tit = _make_title(nro, osa, _id) if title else nro
        results.append(StructuredMetadata(p_id, nro, tit, loc, col, year, themes))
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
        verses = [Verse(v_id, type, text, cf) \
                  for v_id, type, text, cf in db.fetchall()]
        db.execute('SELECT field, value FROM raw_meta WHERE p_id = %s', (p_id,))
        meta = { field : value for field, value in db.fetchall() }
        # cursor.execute(
        #     'SELECT f.code, t.code, f.title, t.title_1 FROM so_type st'
        #     ' JOIN types t ON st.t_id = t.t_id'
        #     ' JOIN files f ON t.f_id = f.f_id'
        #     ' WHERE st.so_id = %s;',
        #     (so_id,))
        # topics = cursor.fetchall()
        topics = []
        db.execute('SELECT text FROM refs WHERE p_id = %s', (p_id,))
        refs = [x[0] for x in db.fetchall()]
        smd = get_structured_metadata(db, nro=nro)[0]
        return Poem(p_id, smd, meta, verses, refs)

    @staticmethod
    def from_db_by_nro(db, nro):
        #query = _format_query('SELECT p_id FROM poems WHERE nro=%s;', fmt)
        db.execute('SELECT p_id FROM poems WHERE nro=%s;', (nro,))
        p_id = db.fetchall()[0][0]
        return Poem.from_db(db, p_id)

