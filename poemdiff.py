import numpy as np
import pymysql
from subprocess import Popen, PIPE

from align import align
import config
from data import Poem


COLOR_CHARDIFF = 'blue'
COLOR_LINEDIFF = 'grey'

SIM_SELECT = '''
SELECT
    s.v1_id, s.v2_id, s.sim_cos
FROM
    v_sim_cos s
    JOIN v_so v_so1 ON s.v1_id = v_so1.v_id
    JOIN v_so v_so2 ON s.v2_id = v_so2.v_id
WHERE
    v_so1.so_id = %s
    AND v_so2.so_id = %s
;
'''


def get_data_from_db(nro_1, nro_2, mysql_params):
    poem_1, poem_2, sim_list = None, None, None
    with pymysql.connect(**mysql_params) as db:
        poem_1 = Poem.from_db_by_nro(db, nro_1, fmt='mysql')
        poem_2 = Poem.from_db_by_nro(db, nro_2, fmt='mysql')
        db.execute(SIM_SELECT, (poem_1.so_id, poem_2.so_id))
        sims_list = db.fetchall()
    return poem_1, poem_2, sims_list


def build_similarity_matrix(poem_1, poem_2, sims_list):
    # create a verse similarity matrix for the poems
    poem_1_v_ids = { v.v_id : i for i, v in enumerate(poem_1.text_verses()) }
    poem_2_v_ids = { v.v_id : i for i, v in enumerate(poem_2.text_verses()) }
    sims = np.zeros(
        shape=(len(poem_1_v_ids), len(poem_2_v_ids)),
        dtype=np.float32)
    for v1_id, v2_id, s in sims_list:
        sims[poem_1_v_ids[v1_id], poem_2_v_ids[v2_id]] = float(s)
    return sims


def render(nro_1, nro_2):
    # TODO
    # - some refactoring
    # - bold for captions
    poem_1, poem_2, sims_list = \
        get_data_from_db(nro_1, nro_2, config.MYSQL_PARAMS)
    sims = build_similarity_matrix(poem_1, poem_2, sims_list)
    result = ['<table>']
    result.append(
        '<tr><td><h2>{}</h2><small>[<a href="/poem?nro={}">to poem</a>]</td>'\
        .format(nro_1, nro_1))
    result.append(
        '<td><h2>{}</h2><small>[<a href="/poem?nro={}">to poem</a>]</td></tr>'\
        .format(nro_2, nro_2))
    al = align(
        list(poem_1.text_verses()),
        list(poem_2.text_verses()),
        insdel_cost=0,
        dist_fun=lambda i, j: sims[i,j],
        opt_fun=max,
        empty=None)
    for key in sorted(list(set(poem_1.meta.keys()) | set(poem_2.meta.keys()))):
        result.append('<tr><td><small><b>{}:</b> {}</small></td>'.format(
                      key, poem_1.meta[key] if key in poem_1.meta else ''))
        result.append('<td><small><b>{}: </b>{}</small></td></tr>'.format(
                      key, poem_2.meta[key] if key in poem_2.meta else ''))
    result.append('<tr><td>&nbsp;</td><td></td></tr>')
    for row in al:
        if row[2] > 0:
            v_al = align(row[0].text, row[1].text)
            verse_1, verse_2 = [], []
            different = False
            for x, y, c in v_al:
                if x != y:
                    if not different:
                        verse_1.append(
                            '<font color="{}">'.format(COLOR_CHARDIFF))
                        verse_2.append(
                            '<font color="{}">'.format(COLOR_CHARDIFF))
                        different = True
                    if x == ' ': x = '_'
                    verse_1.append(x)
                    if y == ' ': y = '_'
                    verse_2.append(y)
                else:
                    if different:
                        different = False
                        verse_1.append('</font>')
                        verse_2.append('</font>')
                    verse_1.append(x)
                    verse_2.append(y)
            if different:
                verse_1.append('</font>')
                verse_2.append('</font>')
            result.append('<tr><td>{}</td><td>{}</td></tr>'.format(
                ''.join(verse_1), ''.join(verse_2)))
        else:
            result.append('<tr><td>{}</td><td>{}</td></tr>'.format(
                    '<font color="{}">{}</font>'.format(\
                        COLOR_LINEDIFF, row[0].text) \
                      if row[0] is not None else '',
                    '<font color="{}">{}</font>'.format(\
                        COLOR_LINEDIFF, row[1].text) \
                      if row[1] is not None else ''))
    result.append('</table>')
    return '\n'.join(result)

