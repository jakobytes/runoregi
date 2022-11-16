from collections import defaultdict
from flask import render_template
import pymysql
import re
from subprocess import Popen, PIPE

from shortsim.align import align
from shortsim.ngrcos import vectorize

import config
from data import Poem, render_csv, render_themes_tree
from utils import link


DEFAULTS = {
  'nro1': None,
  'nro2': None,
  't': 0.75,
  'format': 'html'
}

COLOR_NORMAL = None
COLOR_CHARDIFF = 'blue'
COLOR_LINEDIFF = 'grey'


def generate_page_links(args):
    global DEFAULTS

    def pagelink(**kwargs):
        return link('poemdiff', dict(args, **kwargs), DEFAULTS)

    return {
        'csv': pagelink(format='csv'),
        'tsv': pagelink(format='tsv'),
        '-t': pagelink(t=max(args['t']-0.05, 0)),
        '+t': pagelink(t=min(args['t']+0.05, 1)),
    }


def get_sim_mtx(db, nros):
    nros_str = ','.join(['"{}"'.format(nro) for nro in nros])
    idx = { nro: i for i, nro in enumerate(nros) }
    m = np.zeros(shape=(len(nros), len(nros))) + np.eye(len(nros))
    m_onesided = np.zeros(shape=(len(nros), len(nros))) + np.eye(len(nros))
    q = 'SELECT p1.nro, p2.nro, sim_al, sim_al_l FROM p_sim s'\
        '  JOIN poems p1 ON p1.p_id = s.p1_id'\
        '  JOIN poems p2 ON p2.p_id = s.p2_id'\
        '  WHERE p1.nro IN ({}) AND p2.nro IN ({});'\
        .format(nros_str, nros_str)
    db.execute(q)
    for nro1, nro2, sim, sim_l in db.fetchall():
        m[idx[nro1],idx[nro2]] = sim
        m_onesided[idx[nro1],idx[nro2]] = sim_l
    return m, m_onesided


def compute_similarity(text_1, text_2, threshold):
    verses = set((v.v_id, v.text_cl if v.text_cl is not None else '') \
                 for v in text_1 + text_2)
    v_ids, v_texts, ngr_ids, m = vectorize(verses)
    sim = m.dot(m.T)
    sim[sim < threshold] = 0
    return v_ids, sim


def render(**args):

    # FIXME code duplication with poem.py!
    def _makecolcomp(value):
        result = hex(255-int(value*255))[2:]
        if len(result) == 1:
            result = '0'+result
        return result

    def _makecol(value):
        if value is None:
            value = 0
        rg = _makecolcomp(value)
        b = _makecolcomp(max(value-0.5, 0))
        return '#'+rg+rg+b 

    # TODO
    # - some refactoring
    # - bold for captions
    with pymysql.connect(**config.MYSQL_PARAMS) as db:
        poem_1 = Poem.from_db_by_nro(db, args['nro1'])
        poem_2 = Poem.from_db_by_nro(db, args['nro2'])
    poem_1_text = list(poem_1.text_verses())
    poem_2_text = list(poem_2.text_verses())
    v_ids, sims = compute_similarity(poem_1_text, poem_2_text, args['t'])
    v_ids_dict = { v_id: i for i, v_id in enumerate(v_ids) }
    al = align(
        poem_1_text,
        poem_2_text,
        insdel_cost=0,
        dist_fun=lambda i, j:
          sims[v_ids_dict[poem_1_text[i].v_id],
               v_ids_dict[poem_2_text[j].v_id]] \
          if poem_1_text[i].v_id in v_ids_dict and \
             poem_2_text[j].v_id in v_ids_dict \
          else 0,
        opt_fun=max,
        empty=None)
    if args['format'] in ('csv', 'tsv'):
        return render_csv([(x.text if x is not None else None,
                            y.text if y is not None else None,
                            w) for x, y, w in al],
                          header=(poem_1.smd.nro, poem_2.smd.nro, 'sim_cos'),
                          delimiter='\t' if args['format'] == 'tsv' else ',')

    # render HTML
    meta_keys = sorted(list(set(poem_1.meta.keys()) | set(poem_2.meta.keys())))
    meta_1, meta_2 = {}, {}
    for key in meta_keys:
        meta_1[key] = poem_1.meta[key] if key in poem_1.meta else ''
        meta_2[key] = poem_2.meta[key] if key in poem_2.meta else ''
    alignment = []
    # TODO rendering the verse-level alignments - ugly code, refactor this!
    for row in al:
        verse_1, verse_2 = [], []
        if row[2] > 0:
            v_al = align(row[0].text, row[1].text)
            chunk_1, chunk_2, different, col = [], [], False, COLOR_NORMAL
            for x, y, c in v_al:
                if (x != y) != different:
                    if chunk_1:
                        verse_1.append((col, ''.join(chunk_1)))
                    if chunk_2:
                        verse_2.append((col, ''.join(chunk_2)))
                    chunk_1, chunk_2 = [], []
                    different = (x != y)
                    col = COLOR_CHARDIFF if different else COLOR_NORMAL
                if x == ' ' and different: x = '_'
                if y == ' ' and different: y = '_'
                chunk_1.append(x)
                chunk_2.append(y)
            if chunk_1:
                verse_1.append((col, ''.join(chunk_1)))
            if chunk_2:
                verse_2.append((col, ''.join(chunk_2)))
        else:
            if row[0] is not None:
                verse_1.append((COLOR_LINEDIFF, row[0].text))
            if row[1] is not None:
                verse_2.append((COLOR_LINEDIFF, row[1].text))
        alignment.append((verse_1, verse_2, (row[2], _makecol(row[2]**2))))
    raw_sim = sum(w for x, y, w in al)
    scores = [
        raw_sim,
        2*raw_sim / (len(poem_1_text) + len(poem_2_text)),
        raw_sim / len(poem_1_text),
        raw_sim / len(poem_2_text),
        sum([int(w > 0) for x, y, w in al]) / len(al),
    ]
    links = generate_page_links(args)
    data = {
        'p1': poem_1, 'p2': poem_2, 'meta_keys': meta_keys,
        'alignment': alignment, 'scores': scores,
        'themes_1': render_themes_tree(poem_1.smd.themes),
        'themes_2': render_themes_tree(poem_2.smd.themes)
    }
    return render_template('poemdiff.html', args=args, data=data, links=links)

