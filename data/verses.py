from collections import namedtuple
from utils import clean_special_chars as csc


Verse = \
    namedtuple('Verse',
               ['nro', 'pos', 'v_id', 'v_type', 'text', 'text_cl',
                'clust_id', 'clust_freq'])


def get_clusterings(db):
    db.execute('SELECT * FROM v_clusterings;')
    return db.fetchall()


def get_verses(db, nro=None, start_pos=None, end_pos=None,
                   clust_id=None, clustering_id=0):
    query = \
        'SELECT '\
        '  p.nro, vp.pos, v.v_id, v.type, v.text, v_cl.text, '\
        '  vcf.clust_id, vcf.freq '\
        'FROM verses v'\
        '  JOIN verse_poem vp ON vp.v_id = v.v_id'\
        '  JOIN poems p ON vp.p_id = p.p_id'\
        '  LEFT OUTER JOIN verses_cl v_cl ON v_cl.v_id = v.v_id'\
        '  LEFT OUTER JOIN v_clust vc ON vc.v_id = v.v_id '\
        '                                AND vc.clustering_id = %s '\
        '  LEFT OUTER JOIN v_clust_freq vcf '\
        '    ON vcf.clust_id = vc.clust_id '\
        '       AND vcf.clustering_id = vc.clustering_id '
    query_args = [clustering_id]

    if isinstance(nro, str):
        # get by passage of one poem
        query += 'WHERE p.nro = %s'
        query_args.append(nro)
        if start_pos is not None and end_pos is not None:
            query += ' AND vp.pos BETWEEN %s AND %s'
            query_args.extend((start_pos, end_pos))
    elif isinstance(nro, tuple) or isinstance(nro, list):
        # get by poem IDs for multiple poems
        query += 'WHERE p.nro IN %s'
        query_args.append(tuple(nro))
    elif isinstance(clust_id, tuple) or isinstance(clust_id, list):
        # get by cluster IDs
        query += 'WHERE vc.clust_id IN %s'
        query_args.append(tuple(clust_id))
    else:
        raise Exception('TODO message')

    query += ' ORDER BY p.p_id, vp.pos;';
    db.execute(query, tuple(query_args))
    result = []
    for nro, pos, v_id, v_type, v_text, \
            v_text_cl, clust_id, clust_freq in db.fetchall():
        result.append(Verse(
            nro, pos, v_id, v_type, csc(v_text), v_text_cl, clust_id, clust_freq))
    return result


# TODO if this is too slow, consider grouping by vc2.clust_id
# and returning just one verse per neighboring cluster
def get_verse_cluster_neighbors(
        db, clust_id, clustering_id=0, by_cluster=False, limit=None):

    query_args = [clustering_id, clustering_id, clust_id, clust_id]
    if by_cluster:
        query_lst = [
            'SELECT ',
            '   p1.nro, vp1.pos, v1.v_id, v1.type, v1.text, v1_cl.text,',
            '   vc1.clust_id, vcf1.freq, ',
            '   p2.nro, vp2.pos, v2.v_id, v2.type, v2.text, v2_cl.text,',
            '   vc2.clust_id, vcf2.freq, ',
            '   SUM(s.sim_cos) AS sim ',
            'FROM v_sim s ',
            '  JOIN verses v1 ON s.v1_id = v1.v_id',
            '  JOIN verses_cl v1_cl ON s.v1_id = v1_cl.v_id',
            '  JOIN verse_poem vp1 ON s.v1_id = vp1.v_id',
            '  JOIN poems p1 ON vp1.p_id = p1.p_id',
            '  JOIN v_clust vc1 ON s.v1_id = vc1.v_id ',
            '                      AND vc1.clustering_id = %s ',
            '  JOIN v_clust_freq vcf1 ON vc1.clust_id = vcf1.clust_id',
            '                         AND vc1.clustering_id = vcf1.clustering_id ',
            '  JOIN verses v2 ON s.v2_id = v2.v_id',
            '  JOIN verses_cl v2_cl ON s.v2_id = v2_cl.v_id',
            '  JOIN verse_poem vp2 ON s.v2_id = vp2.v_id',
            '  JOIN poems p2 ON vp2.p_id = p2.p_id',
            '  JOIN v_clust vc2 ON s.v2_id = vc2.v_id ',
            '                      AND vc2.clustering_id = %s ',
            '  JOIN v_clust_freq vcf2 ON vc2.clust_id = vcf2.clust_id',
            '                         AND vc2.clustering_id = vcf2.clustering_id ',
            'WHERE vc1.clust_id IN %s AND vc2.clust_id NOT IN %s ',
            'GROUP BY vc1.clust_id, vc2.clust_id',
            'ORDER BY sim DESC '
        ]
    else:
        query_lst = [
            'SELECT ',
            '   s.v1_id,',
            '   p2.nro, vp2.pos, v2.v_id, v2.type, v2.text, v2_cl.text,',
            '   vc2.clust_id, vcf2.freq, ',
            '   s.sim_cos ',
            'FROM v_sim s ',
            '  JOIN v_clust vc1 ON s.v1_id = vc1.v_id ',
            '                      AND vc1.clustering_id = %s ',
            '  JOIN verses v2 ON s.v2_id = v2.v_id',
            '  JOIN verses_cl v2_cl ON s.v2_id = v2_cl.v_id',
            '  JOIN verse_poem vp2 ON s.v2_id = vp2.v_id',
            '  JOIN poems p2 ON vp2.p_id = p2.p_id',
            '  JOIN v_clust vc2 ON s.v2_id = vc2.v_id ',
            '                      AND vc2.clustering_id = %s ',
            '  JOIN v_clust_freq vcf2 ON vc2.clust_id = vcf2.clust_id',
            '                         AND vc2.clustering_id = vcf2.clustering_id ',
            'WHERE vc1.clust_id IN %s AND vc2.clust_id NOT IN %s ',
            'ORDER BY s.v1_id, s.sim_cos DESC;'
        ]
    if limit is not None:
        query_lst.append('LIMIT %s')
        query_args.append(limit)
    query_lst.append(';')
    db.execute(' '.join(query_lst), tuple(query_args))
    result = []
    for row in db.fetchall():
        if by_cluster:
            result.append((Verse(*row[:4], csc(row[4]), *row[5:8]),
                           Verse(*row[8:12], csc(row[12]), *row[13:16]),
                           row[16]))
        else:
            result.append((row[0], Verse(*row[1:5], csc(row[5]), *row[6:-1]), row[-1]))
    return result

