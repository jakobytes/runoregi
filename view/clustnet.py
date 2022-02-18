from flask import render_template
import pymysql

import config

# FIXME this is partially duplicate with get_similar_verses()
# (not exactly the same, but some queries might be redundant)
def get_cluster_network(db, clust_id, clustering_id=0, maxdepth=3, maxnodes=30):
    nodes_set = { clust_id }
    nodes = []
    depth = 0
    while depth < maxdepth and len(nodes) < maxnodes:
        depth += 1
        node_ids = ', '.join(map(str, nodes_set))
        query = \
            '''SELECT DISTINCT vc2.clust_id, v2.text, vcf2.freq, p2.nro, vp2.pos
             FROM
               v_sim s
               JOIN v_clust vc1 ON s.v1_id = vc1.v_id AND vc1.clustering_id = %s
               JOIN verses v2 ON s.v2_id = v2.v_id
               JOIN v_clust vc2 ON s.v2_id = vc2.v_id AND vc2.clustering_id = %s
               JOIN v_clust_freq vcf2 ON vc2.clust_id = vcf2.clust_id AND vcf2.clustering_id = %s
               JOIN verse_poem vp2 ON v2.v_id = vp2.v_id
               JOIN poems p2 ON vp2.p_id = p2.p_id
             WHERE
               vc1.clust_id IN ({})
               AND vc2.clust_id <> vc1.clust_id
             GROUP BY
               vc2.clust_id
             ORDER BY vcf2.freq DESC
             LIMIT %s;'''.format(node_ids)
        db.execute(query, (clustering_id, clustering_id, clustering_id, maxnodes))
        for c_id, text, freq, nro, pos in db.fetchall():
            if c_id not in nodes_set:
                nodes_set.add(c_id)
                nodes.append((c_id, text, freq, depth, nro, pos))
    node_ids = ', '.join(map(str, nodes_set))
    # FIXME inserting node_ids directly to db.execute() throws an error,
    # dunno why
    query = \
        '''SELECT
          vc1.clust_id, vc2.clust_id, SUM(s.sim_cos)
         FROM
           v_sim s
           JOIN v_clust vc1 ON s.v1_id = vc1.v_id AND vc1.clustering_id = %s
           JOIN v_clust vc2 ON s.v2_id = vc2.v_id AND vc2.clustering_id = %s
         WHERE
           vc1.clust_id IN ({})
           AND vc2.clust_id IN ({})
           AND vc1.clust_id < vc2.clust_id
         GROUP BY vc1.clust_id, vc2.clust_id;'''\
        .format(node_ids, node_ids)
    db.execute(query, (clustering_id, clustering_id))
    edges = db.fetchall()
    return { 'nodes': nodes, 'edges': edges }

def render(nro=None, pos=None, v_id=None, clustering_id=0, maxdepth=1, maxnodes=20):
    clustnet, clust_id, clusterings, text, freq = None, None, None, None, None
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        db.execute(
            'SELECT v_id, text, nro, clust_id, freq FROM verses'
            ' NATURAL JOIN verse_poem'
            ' NATURAL JOIN poems'
            ' NATURAL JOIN v_clust'
            ' NATURAL JOIN v_clust_freq'
            ' WHERE nro = %s AND pos = %s AND clustering_id = %s;',
            (nro, pos, clustering_id))
        v_id, text, nro, clust_id, freq = db.fetchall()[0]
        db.execute('SELECT * FROM v_clusterings;')
        clusterings = db.fetchall()
        clustnet = get_cluster_network(db, clust_id,
                                       clustering_id=clustering_id,
                                       maxdepth=maxdepth, maxnodes=maxnodes)
    return render_template('clustnet.html', nro=nro, pos=pos,
                           maxdepth=maxdepth, maxnodes=maxnodes,
                           clust_id=clust_id, text=text, freq=freq,
                           clustnet=clustnet, clustering_id=clustering_id,
                           clusterings=clusterings)
