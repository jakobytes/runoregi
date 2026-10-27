import re

import config
from utils import render_type_links, render_xml


# Emulation of MariaDB's full-text search (MATCH ... AGAINST ... IN BOOLEAN
# MODE) by scanning the text column with regular expressions in DuckDB.
# Like the MariaDB setup, matching ignores case (but not accents) and words
# shorter than FT_MIN_WORD_LEN; there is no relevance ranking.

FT_MIN_WORD_LEN = 3
_NONWORD = r'[^\pL\pN_]'


def _term_regex(words, prefix):
    body = (_NONWORD + '+').join(re.escape(w.lower()) for w in words)
    end = '' if prefix else '($|{})'.format(_NONWORD)
    return '(^|{}){}{}'.format(_NONWORD, body, end)


def parse_boolean_query(q):
    'Split a boolean-mode query into (required, optional, excluded) regexes.'
    required, optional, excluded = [], [], []
    for op, phrase, word in re.findall(r'([+-]?)(?:"([^"]*)"|([^\s"]+))', q):
        if phrase:
            words, prefix = re.findall(r'\w+', phrase), False
        else:
            words, prefix = re.findall(r'\w+', word), word.endswith('*')
        if not words or (len(words) == 1 and not prefix
                         and len(words[0]) < FT_MIN_WORD_LEN):
            continue
        {'+': required, '-': excluded, '': optional}[op].append(
            _term_regex(words, prefix))
    return required, optional, excluded


def match_condition(column, q):
    'SQL condition (with %s placeholders) and arguments for MATCH(column) AGAINST(q).'
    required, optional, excluded = parse_boolean_query(q)
    col = 'lower({})'.format(column)
    match = 'regexp_matches({}, %s)'.format(col)
    conds, args = [], []
    for regex in required:
        conds.append(match)
        args.append(regex)
    if optional and not required:
        conds.append('(' + ' OR '.join([match] * len(optional)) + ')')
        args.extend(optional)
    if not conds:
        # MariaDB returns nothing for a query with only excluded words
        return 'FALSE', []
    for regex in excluded:
        conds.append('NOT ' + match)
        args.append(regex)
    return ' AND '.join(conds), args



def extract_keywords(q):
    'Extract keywords from a search query.'
    keywords = [w.replace('*', '\w*') \
        for w in re.findall('\w+\*?', q) \
        if w.lower() not in ['and', 'or', ]]
    return re.compile('|'.join(keywords), flags=re.IGNORECASE)


# FIXME this operates on strings, which are actually XML.
# If the search terms overlap with XML tags, this might lead to problems.
# To do it correctly, we would need to match the pattern only in
# the text within the XML.
def highlight(pattern, text):
    idx = 0
    result = []
    m = pattern.search(text, idx)
    while m is not None:
        result.append(text[idx:m.start()])
        result.append('<span class="selected">')
        result.append(text[m.start():m.end()])
        result.append('</span>')
        idx = m.end()
        m = pattern.search(text, idx)
    result.append(text[idx:])
    return ''.join(result)


def search_verses(db, q):
    result = []
    cond, args = match_condition('text', q)
    db.execute(\
        'SELECT nro, pos, type, text FROM verses'
        ' NATURAL JOIN verse_poem'
        ' NATURAL JOIN poems'
        ' WHERE ' + cond + ' ORDER BY nro, pos LIMIT %s;',
        (*args, config.SEARCH_LIMIT))
    kwd = extract_keywords(q)
    result = [(nro, pos, vtype, highlight(kwd, render_xml(text))) \
              for (nro, pos, vtype, text) in db.fetchall()]
    return result


def search_types(db, q):
    result = []
    # ignore if the table is not available
    if not config.TABLES['types']:
        return result
    name_cond, name_args = match_condition('t1.name', q)
    descr_cond, descr_args = match_condition('t1.description', q)
    db.execute(\
      'SELECT t4.name, t3.name, t2.name, t1.type_orig_id, t1.name,'
      '       t1.description'
      ' FROM types t1'
      '  LEFT OUTER JOIN types t2 on t1.par_id = t2.t_id'
      '  LEFT OUTER JOIN types t3 on t2.par_id = t3.t_id'
      '  LEFT OUTER JOIN types t4 on t3.par_id = t4.t_id'
      '  WHERE ' + name_cond +
      ' UNION '
      'SELECT t4.name, t3.name, t2.name, t1.type_orig_id, t1.name,'
      '       t1.description'
      ' FROM types t1'
      '  LEFT OUTER JOIN types t2 on t1.par_id = t2.t_id'
      '  LEFT OUTER JOIN types t3 on t2.par_id = t3.t_id'
      '  LEFT OUTER JOIN types t4 on t3.par_id = t4.t_id'
      '  WHERE ' + descr_cond + ';', (*name_args, *descr_args))
    kwd = extract_keywords(q)
    result = [(r[3], highlight(kwd, r[4]), highlight(kwd, render_type_links(render_xml(r[5]))),
               [r[i] for i in range(3) if r[i]]) \
              for r in db.fetchall()]
    return result



def search_translated(db, q):
    result = []
    if not config.TABLES['verses_translated']:
        return result
    cond, args = match_condition('vt.verse_in_english', q)
    db.execute(
        'SELECT p.nro, vt.pos, v.text, vt.verse_in_english'
        ' FROM verses_translated vt'
        ' JOIN poems p ON vt.p_id = p.p_id'
        # translations are aligned with the poem text by position
        ' LEFT JOIN verse_poem vp ON vp.p_id = vt.p_id AND vp.pos = vt.pos'
        ' LEFT JOIN verses v ON v.v_id = vp.v_id'
        ' WHERE ' + cond + ' ORDER BY p.nro, vt.pos LIMIT %s;',
        (*args, config.SEARCH_LIMIT))
    kwd = extract_keywords(q)
    result = [(nro, pos, render_xml(orig) if orig else '',
               highlight(kwd, verse))
              for (nro, pos, orig, verse) in db.fetchall()]
    return result


def search_smd(db, q):
    result = []
    kwd = extract_keywords(q)
    if config.TABLES['collectors'] and config.TABLES['p_col']:
        cond, args = match_condition('name', q)
        db.execute(\
            'SELECT col_orig_id, name FROM collectors'
            ' WHERE ' + cond + ' ORDER BY name;', args)
        result.extend([('collector', col_id, highlight(kwd, name)) \
                       for (col_id, name) in db.fetchall()])
    if config.TABLES['places'] and config.TABLES['p_pl']:
        cond, args = match_condition('name', q)
        db.execute(\
            'SELECT place_orig_id, name FROM places'
            ' WHERE ' + cond + ' ORDER BY name;', args)
        result.extend([('place', place_id, highlight(kwd, name)) \
                       for (place_id, name) in db.fetchall()])
    return result

