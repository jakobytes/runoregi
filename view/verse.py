from collections import defaultdict, OrderedDict
from flask import render_template
import pymysql

import config
from data.poems import Poems
from data.verses import \
    get_clusterings, get_verses, get_verse_cluster_neighbors
from external import make_map_link
from utils import print_type_list, render_csv


DEFAULTS = {
  'format': 'html',
  'nro': None,
  'pos': 0,
  'v_id': 0,
  'clustering': 0
}


def render(**args):

    def _group_by_source(verses):
        results = OrderedDict()
        for v in verses:
            if v.nro not in results:
                results[v.nro] = []
            results[v.nro].append(v)
        return results

    def _group_nbclust(verses_nbclust, verses):
        nbclust, seen_clust = defaultdict(list), set()
        v_id_to_nro = { v.v_id: v.nro for v in verses }
        for v1_id, v2, sim in verses_nbclust:
            if v2.clust_id not in seen_clust:
                nbclust[v_id_to_nro[v1_id]].append(v2)
                seen_clust.add(v2.clust_id)
        return nbclust

    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        # the target verse (with nro and pos specified in args)
        verse = get_verses(
            db, nro=args['nro'], start_pos=args['pos'],
            end_pos=args['pos'], clustering_id=args['clustering'])[0]
        # verse cluster
        verses = get_verses(db, clust_id=(verse.clust_id,),
                            clustering_id=args['clustering'])
        verses_by_src = _group_by_source(verses)
        # poem metadata
        poems = Poems(nros=list(verses_by_src.keys()))
        poems.get_structured_metadata(db)
        # poem types
        types = poems.get_types(db)
        types.get_names(db)
        # neighboring clusters
        verses_nbclust = get_verse_cluster_neighbors(
            db, (verse.clust_id,), clustering_id=args['clustering'])
        # clusterings
        clusterings = get_clusterings(db)

    nbclust = _group_nbclust(verses_nbclust, verses)

    if args['format'] in ('csv', 'tsv'):
        return render_csv([
            (v.nro, v.pos, v.text, poems[v.nro].smd.location,
             poems[v.nro].smd.collector,
             print_type_list(poems[v.nro], types))
            for v in verses],
            header=('nro', 'pos', 'text', 'location', 'collector', 'themes'),
            delimiter='\t' if args['format'] == 'tsv' else ',')
    else:
        data = {
            'verse': verse,
            'verses': verses_by_src,
            'poems': poems,
            'types': types,
            'nbclust': nbclust,
            'clusterings': clusterings
        }
        links = {
            'map_lnk': make_map_link('verse', nro=args['nro'], pos=args['pos'],
                                     clustering=args['clustering'])
        }
        return render_template('verse.html', args=args, data=data, links=links)

