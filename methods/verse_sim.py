from collections import defaultdict
from shortsim.ngrcos import vectorize


def compute_verse_similarity(poems, threshold):
    verses = [v for p in poems.values() for v in p.text if v.v_type == 'V']
    v_texts = [(v.text_cl if v.text_cl is not None else '') for v in verses]
    m = vectorize(v_texts)
    sim = m.dot(m.T)
    sim[sim < threshold] = 0
    v_sim = defaultdict(dict)
    for i, j in list(zip(*sim.nonzero())):
        v_sim[verses[i].v_id][verses[j].v_id] = float(sim[i,j])
    return v_sim

