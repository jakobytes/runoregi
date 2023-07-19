from collections import namedtuple, OrderedDict
from operator import itemgetter
import re

import config
from .types import Types, render_type_tree
from .verses import get_verses


Reference = namedtuple('Reference', ['num', 'type', 'text'])
SimilarPoemLink = \
    namedtuple('SimilarPoemLink', ['nro', 'sim_al', 'sim_al_l', 'sim_al_r'])
StructuredMetadata = \
    namedtuple('StructuredMetadata',
               ['collection', 'title', 'location', 'collector', 'year'])


class Poem:
    def __init__(self, nro):
        self.nro = nro
        self.meta = {}
        self.smd = None
        self.text = None
        self.type_ids = []
        self.minor_type_ids = []
        self.type_tree = []
        self.refs = []
        self.sim_poems = []
        self.p_clust_id = None
        self.p_clust_size = None
        self.duplicates = []
        self.parents = []


class Poems:
    def __init__(self, poems=None, nros=None, p_ids=None):
        if poems is not None:
            self.c = OrderedDict((p.nro, p) for p in poems)
        elif nros is not None:
            self.c = OrderedDict()
            for nro in nros:
                self.c[nro] = Poem(nro=nro)

    def __contains__(self, key):
        return key in self.c

    def __getitem__(self, key):
        return self.c[key]

    def __iter__(self):
        return self.c.__iter__()

    def __len__(self):
        return self.c.__len__()

    def items(self):
        return self.c.items()

    def values(self):
        return self.c.values()

    def get_duplicates_and_parents(self, db):
        if not self: return    # empty set? -> do nothing
        # ignore if the table is not available
        if not config.TABLES['p_dupl']: return
        db.execute(
            'SELECT p.nro, mp.nro '
            'FROM p_dupl d '
            '  JOIN poems p ON d.p_id = p.p_id '
            '  JOIN poems mp ON d.master_p_id = mp.p_id '
            'WHERE p.nro IN %s OR mp.nro IN %s;',
            (tuple(self), tuple(self)))
        for nro in self:
            self[nro].duplicates = []
            self[nro].parents = []
        for nro, master_nro in db.fetchall():
            if nro in self:
                self[nro].parents.append(master_nro)
            if master_nro in self:
                self[master_nro].duplicates.append(nro)

    def get_poem_cluster_info(self, db):
        if not self: return    # empty set? -> do nothing
        # ignore if the table is not available
        if not config.TABLES['p_clust'] or not config.TABLES['p_clust_freq']:
            return
        db.execute(
            'SELECT nro, clust_id, freq '
            'FROM poems NATURAL JOIN p_clust NATURAL JOIN p_clust_freq '
            'WHERE nro IN %s', (tuple(self),))
        for nro, clust_id, freq in db.fetchall():
            self[nro].p_clust_id = clust_id
            self[nro].p_clust_size = freq

    def get_raw_meta(self, db):
        if not self: return    # empty set? -> do nothing
        # ignore if the table is not available
        if not config.TABLES['raw_meta']: return
        db.execute(
            'SELECT nro, field, value '
            'FROM poems NATURAL JOIN raw_meta '
            'WHERE nro IN %s;',
            (tuple(self),))
        for nro in self:
            self[nro].meta = {}
        for nro, field, value in db.fetchall():
            self[nro].meta[field] = value

    def get_refs(self, db):
        if not self: return    # empty set? -> do nothing
        # ignore if the table is not available
        if not config.TABLES['refs']: return
        for nro in self:
            self[nro].refs = []
        db.execute(
            'SELECT nro, num, type, text FROM poems NATURAL JOIN refs '
            'WHERE nro IN %s;', (tuple(self),))
        for nro, num, type_, text in db.fetchall():
            self[nro].refs.append(Reference(num, type_, text))

    def get_similar_poems(self, db, within=False, sim_thr=None, sim_onesided_thr=None):
        if not self: return    # empty set? -> do nothing
        # ignore if the table is not available
        if not config.TABLES['p_sim']: return
        query_args = [tuple(self)]
        query_lst = [
            'SELECT ',
            '  p1.nro, p2.nro, s.sim_al, s.sim_al_l, s.sim_al_r ',
            'FROM p_sim s ',
            '  JOIN poems p1 ON p1.p_id = s.p1_id ',
            '  JOIN poems p2 ON p2.p_id = s.p2_id ',
            'WHERE ',
            '  p1.nro IN %s'
        ]
        if within:
            query_lst.append('  AND p2.nro IN %s')
            query_args.append(tuple(self))
        if sim_thr is not None:
            if sim_onesided_thr is not None:
                query_lst.append('  AND (s.sim_al >= %s')
                query_lst.append('       OR s.sim_al_l >= %s ')
                query_lst.append('       OR s.sim_al_r >= %s)')
                query_args.append(sim_thr)
                query_args.append(sim_onesided_thr)
                query_args.append(sim_onesided_thr)
            else:
                query_lst.append('  AND s.sim_al >= %s')
                query_args.append(sim_thr)
        query_lst.append(';')
        db.execute(' '.join(query_lst), tuple(query_args))
        for nro in self:
            self[nro].sim_poems = []
        for nro_1, nro_2, sim_al, sim_al_l, sim_al_r in db.fetchall():
            self[nro_1].sim_poems.append(
                SimilarPoemLink(nro_2, sim_al, sim_al_l, sim_al_r))

    def get_structured_metadata(self, db):

        def _make_title(nro, osa, _id, collection):
            if collection == 'skvr' and osa and _id:
                return 'SKVR {} {}'.format(osa, _id)
            elif collection == 'erab' and _id:
                return _id
            elif collection == 'jr' and _id:
                return 'JR {}'.format(_id)
            elif nro.startswith('kt'):
                return 'Kanteletar {}:{}'.format(int(nro[2:4]), int(nro[4:]))
            elif collection == 'literary' and osa and _id:
                return '{} {}'.format(osa, _id)
            else:
                return nro

        if not self: return    # empty set? -> do nothing
        get_collector = config.TABLES['collectors'] and config.TABLES['p_col']
        get_location = config.TABLES['locations'] and config.TABLES['p_loc']
        query_lst = [
            'SELECT poems.nro, collection,',
            ('rm_osa.value as osa, rm_id.value as id,' \
             if config.TABLES['raw_meta'] else 'NULL, NULL,'),
            ('GROUP_CONCAT(DISTINCT IFNULL(CONCAT(l2.name, " — ", l.name), l.name)'
             ' SEPARATOR "; "),'\
             if get_location else 'NULL,'),
            ('GROUP_CONCAT(DISTINCT c.name SEPARATOR "; "),'\
             if get_collector else 'NULL,'),
            ('year' if config.TABLES['p_year'] else 'NULL'),
            'FROM poems']
        if config.TABLES['raw_meta']:
            query_lst.extend([
              'LEFT OUTER JOIN raw_meta rm_osa'
              '  ON poems.p_id = rm_osa.p_id AND rm_osa.field = "OSA"',
              'LEFT OUTER JOIN raw_meta rm_id'
              '  ON poems.p_id = rm_id.p_id AND rm_id.field = "ID"',
            ])
        if get_location:
            query_lst.extend([
              'LEFT OUTER JOIN p_loc ON poems.p_id = p_loc.p_id',
              'LEFT OUTER JOIN locations l ON p_loc.loc_id = l.loc_id',
              'LEFT OUTER JOIN locations l2 ON l.par_id = l2.loc_id'
            ])
        if get_collector:
            query_lst.extend([
              'LEFT OUTER JOIN p_col ON poems.p_id = p_col.p_id',
              'LEFT OUTER JOIN collectors c ON p_col.col_id = c.col_id'
            ])
        if config.TABLES['p_year']:
            query_lst.append('LEFT OUTER JOIN p_year ON poems.p_id = p_year.p_id')
        query_lst.append('WHERE poems.nro IN %s')
        # if GROUP_CONCATs present -- return one row per poem
        if get_location or get_collector:
            query_lst.append('GROUP BY poems.p_id')
        query_lst.append(';')
        db.execute(' '.join(query_lst), (tuple(self),))
        #print(db._executed)
        results = []
        for nro, collection, osa, _id, loc, col, year in db.fetchall():
            tit = _make_title(nro, osa, _id, collection)
            self[nro].smd = StructuredMetadata(collection, tit, loc, col, year)

    def get_text(self, db, clustering_id=0):
        if not self: return    # empty set? -> do nothing
        for nro in self:
            self[nro].text = []
        for v in get_verses(db, nro=tuple(self)):
            self[v.nro].text.append(v)

    def get_types(self, db):
        if not self: return Types(ids=[])    # empty set? -> do nothing
        # ignore if the table is not available
        if not config.TABLES['poem_theme'] or not config.TABLES['themes']:
            return Types(ids=[])
        db.execute(
            'SELECT nro, theme_id, is_minor '
            'FROM poems NATURAL JOIN poem_theme NATURAL JOIN themes '
            'WHERE nro IN %s ;', (tuple(self),))
        for nro in self:
            self[nro].type_ids = []
            self[nro].minor_type_ids = []
        type_ids = set()
        for nro, type_id, is_minor in db.fetchall():
            if is_minor:
                self[nro].minor_type_ids.append(type_id)
            else:
                self[nro].type_ids.append(type_id)
            type_ids.add(type_id)
        types = Types(ids=sorted(type_ids))
        types.get_ancestors(db, add=True)
        # render trees
        for nro in self:
            local_type_ids = self[nro].type_ids + self[nro].minor_type_ids
            local_types = Types(types=[types[t_id] for t_id in local_type_ids])
            self[nro].type_tree = render_type_tree(
                local_types,
                minor_type_ids=self[nro].minor_type_ids)
        return types

    @staticmethod
    def get_by_cluster(db, clust_id):
        # ignore if the table is not available
        if not config.TABLES['p_clust']:
            warnings.warn('Poem clustering not available. This function '
                          'should not have been called.')
            return Poems(nros=[])
        db.execute(
            'SELECT p.nro '
            'FROM p_clust pc '
            '  JOIN poems p ON pc.p_id = p.p_id '
            'WHERE pc.clust_id = %s ;',
            (clust_id,))
        nros = list(map(itemgetter(0), db.fetchall()))
        return Poems(nros=nros)

