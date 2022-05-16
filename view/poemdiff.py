from collections import defaultdict
from flask import render_template
import pymysql
import re
from subprocess import Popen, PIPE

from shortsim.align import align
from shortsim.ngrcos import vectorize

import config
from data import Poem, render_themes_tree


COLOR_NORMAL = None
COLOR_CHARDIFF = 'blue'
COLOR_LINEDIFF = 'grey'


def compute_similarity(text_1, text_2, threshold):
    verses = set((v.v_id, v.text_cl if v.text_cl is not None else '') \
                 for v in text_1 + text_2)
    v_ids, v_texts, ngr_ids, m = vectorize(verses)
    sim = m.dot(m.T)
    sim[sim < threshold] = 0
    return v_ids, sim


def render(nro_1, nro_2, threshold=0.75):

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
        poem_1 = Poem.from_db_by_nro(db, nro_1)
        poem_2 = Poem.from_db_by_nro(db, nro_2)
    poem_1_text = list(poem_1.text_verses())
    poem_2_text = list(poem_2.text_verses())
    v_ids, sims = compute_similarity(poem_1_text, poem_2_text, threshold)
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
    scores = [
        sum([int(w > 0) for x, y, w in al]) / len(al),
        sum([w for x, y, w in al]) / len(al),
        sum([w**2 for x, y, w in al]) / len(al)
    ]
    return render_template('poemdiff.html', p1=poem_1, p2=poem_2, threshold=threshold,
                           meta_keys=meta_keys, alignment=alignment, scores=scores,
                           themes_1=render_themes_tree(poem_1.smd.themes),
                           themes_2=render_themes_tree(poem_2.smd.themes))

