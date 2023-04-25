from collections import defaultdict
from shortsim.ngrcos import vectorize


def compute_verse_similarity(poems, threshold):
    verses = set((v.v_id, v.text_cl if v.text_cl is not None else '') \
                 for p in poems.values() for v in p.text if v.v_type == 'V')
    v_ids, v_texts, ngr_ids, m = vectorize(verses)
    sim = m.dot(m.T)
    sim[sim < threshold] = 0
    v_sim = defaultdict(dict)
    for i, j in list(zip(*sim.nonzero())):
        v_sim[v_ids[i]][v_ids[j]] = float(sim[i,j])
    return v_sim

