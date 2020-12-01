import numpy as np
import sys


def align(s1, s2, empty='', insdel_cost=1, dist_fun=None, opt_fun=min):
    'Implements the Wagner-Fischer algorithm.'

    if dist_fun is None:
        dist_fun = lambda i, j: int(s1[i] != s2[j])

    # build the distance matrix
    d = np.zeros(shape=(len(s2)+1, len(s1)+1))
    for j, y in enumerate(s1, 1):
        d[0,j] = j*insdel_cost
    for i, x in enumerate(s2, 1):
        d[i,0] = i*insdel_cost
        for j, y in enumerate(s1, 1):
            d[i,j] = opt_fun(
                d[i-1, j]+insdel_cost,
                d[i,j-1]+insdel_cost,
                d[i-1, j-1] + dist_fun(j-1, i-1))

    # extract the alignment
    alignment = []
    i, j = len(s2), len(s1)
    while i > 0 and j > 0:
        if d[i, j] == d[i-1, j-1] + dist_fun(j-1, i-1):
            alignment.append((s1[j-1], s2[i-1], dist_fun(j-1, i-1)))
            i -= 1
            j -= 1
        elif d[i, j] == d[i-1, j] + insdel_cost:
            alignment.append((empty, s2[i-1], insdel_cost))
            i -= 1
        else:
            alignment.append((s1[j-1], empty, insdel_cost))
            j -= 1
    while i > 0:
        alignment.append((empty, s2[i-1], insdel_cost))
        i -= 1
    while j > 0:
        alignment.append((s1[j-1], empty, insdel_cost))
        j -= 1
    alignment.reverse()
    return alignment


def merge_alignments(alignments, empty=''):

    def _als_get(als, i):
        return als[i] if i < len(als) else (empty,)*len(als[-1])

    def _merge_one(als, a):
        result = []
        i = 0
        j = 0
        while j < len(a):
            if a[j][0] == empty:
                result.append((empty,)*len(als[0]) + (a[j][1],))
                j += 1
            elif a[j][1] == empty:
                while als[i][-1] == empty:
                    result.append(_als_get(als, i)+(empty,))
                    i += 1
                result.append(_als_get(als, i)+(empty,))
                i += 1
                j += 1
            elif i < len(als) and als[i][-1] == empty:
                result.append(_als_get(als, i)+(empty,))
                i += 1
            else:
                result.append(_als_get(als, i)+(a[j][1],))
                i += 1
                j += 1
        return result

    result = [(x, y) for (x, y, w) in alignments[0]]
    for a in alignments[1:]:
        result = _merge_one(result, a)
    return result


if __name__ == '__main__':
    for line in sys.stdin:
        v1_id, v1_text, v2_id, v2_text = line.rstrip().split('\t')
        al = align(v1_text, v2_text, empty='-')
        al_str = ' '.join('{}:{}'.format(x,y) for (x, y, c) in al)
        n_id = sum(c for (x,y,c) in al)
        d_lev = len(al)-n_id
        sim_nes = n_id/len(al)
        print(v1_id, v2_id, al_str, d_lev, sim_nes, sep='\t')

