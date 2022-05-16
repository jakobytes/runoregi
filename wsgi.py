from flask import Flask, Response, request
import re

import view.clustnet
import view.dendrogram
import view.index
import view.multidiff
import view.passage
import view.poem
import view.poemdiff
import view.search
import view.theme
import view.verse


application = Flask(__name__)

def _compact(string):
    'Remove empty lines from the HTML code.'
    return re.sub(r'\n(\s*\n)+', '\n', string)


@application.route('/clustnet')
def show_clustnet():
    nro = request.args.get('nro', None, type=str)
    pos = request.args.get('pos', 1, type=str)
    v_id = request.args.get('id', 1, type=int)
    clustering = request.args.get('clustering', 0, type=int)
    maxdepth = request.args.get('maxdepth', 1, type=int)
    maxnodes = request.args.get('maxnodes', 20, type=int)
    result = view.clustnet.render(nro=nro, pos=pos, v_id=v_id,
                                  clustering_id=clustering, maxdepth=maxdepth,
                                  maxnodes=maxnodes)
    return _compact(result)


@application.route('/dendrogram')
def show_dendrogram():
    theme_id = request.args.get('theme_id', type=str)
    method = request.args.get('method', 'complete', type=str)
    dist = request.args.get('dist', 'al', type=str)
    nb = request.args.get('nb', type=float)
    result = view.dendrogram.render(theme_id=theme_id, method=method, dist=dist, nb=nb)
    return _compact(result)


@application.route('/passage')
def show_passage():
    nro = request.args.get('nro', type=str)
    start_pos = request.args.get('start', 1, type=int)
    end_pos = request.args.get('end', 1, type=int)
    clustering = request.args.get('clustering', 0, type=int)
    dist = request.args.get('dist', 2, type=int)
    context = request.args.get('context', 2, type=int)
    hitfact = request.args.get('hitfact', 0.5, type=float)
    fmt = request.args.get('format', 'html', type=str)
    result = view.passage.render(
                 nro, start_pos, end_pos, clustering_id=clustering, dist=dist,
                 context=context, hitfact=hitfact, fmt=fmt)
    if fmt in ('csv', 'tsv'):
        return Response(result, mimetype='text/plain')
    else:
        return _compact(result)

@application.route('/poemdiff')
@application.route('/runodiff')
def show_diff():
    nro_1 = request.args.get('nro1', 1, type=str)
    nro_2 = request.args.get('nro2', 1, type=str)
    threshold = request.args.get('t', 0.75, type=float)
    return _compact(view.poemdiff.render(nro_1, nro_2, threshold=threshold))

@application.route('/multidiff')
def show_multidiff():
    nros_str = request.args.get('nro', 1, type=str)
    nros = nros_str.split(',')
    fmt = request.args.get('format', 'html', type=str)
    result = view.multidiff.render(nros, fmt=fmt)
    if fmt in ('csv', 'tsv'):
        return Response(result, mimetype='text/plain')
    else:
        return _compact(result)

@application.route('/poem')
@application.route('/runo')
def show_poem():
    nro = request.args.get('nro', 1, type=str)
    hl_str = request.args.get('hl', None, type=str)
    max_similar = request.args.get('max_similar', 50, type=int)
    sim_thr = request.args.get('sim_thr', 1, type=int)
    sim_order = request.args.get('sim_order', 'consecutive_rare', type=str)
    show_verse_themes = request.args.get('show_verse_themes', False, type=bool)
    show_shared_verses = request.args.get('show_shared_verses', False, type=bool)
    hl = list(map(int, hl_str.split(','))) if hl_str is not None else []
    return _compact(view.poem.render(nro, hl=hl, max_similar=max_similar,
                                     sim_thr=sim_thr, sim_order=sim_order,
                                     show_verse_themes=show_verse_themes,
                                     show_shared_verses=show_shared_verses))

@application.route('/verse')
def show_verse():
    nro = request.args.get('nro', None, type=str)
    pos = request.args.get('pos', 1, type=str)
    v_id = request.args.get('id', 1, type=int)
    clustering = request.args.get('clustering', 0, type=int)
    fmt = request.args.get('format', 'html', type=str)
    result = view.verse.render(nro=nro, pos=pos, v_id=v_id, fmt=fmt,
                               clustering_id=clustering)
    if fmt in ('csv', 'tsv'):
        return Response(result, mimetype='text/plain')
    else:
        return _compact(result)

@application.route('/search')
@application.route('/')
def show_search():
    q = request.args.get('q', None, type=str)
    method = request.args.get('method', 'plain', type=str)
    verses = request.args.get('verses', False, type=bool)
    themes = request.args.get('themes', False, type=bool)
    meta = request.args.get('meta', False, type=bool)
    return _compact(view.search.render(
        q, method=method, verses=verses, themes=themes, meta=meta))

@application.route('/theme')
def show_theme():
    theme_id = request.args.get('id', None, type=str)
    return _compact(view.theme.render(theme_id))

@application.route('/skvr-themes')
def show_skvr_static_index():
    return application.send_static_file('skvr-themes.html')
#    q = request.args.get('q', 'a', type=str).lower()
#    return view.index.render(q)

if __name__ == '__main__':
    application.run()

