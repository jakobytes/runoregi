from flask import Flask, request
import re

import view.index
import view.multidiff
import view.passage
import view.poem
import view.poemdiff
import view.verse


application = Flask(__name__)

def _compact(string):
    'Remove empty lines from the HTML code.'
    return re.sub(r'\n(\s*\n)+', '\n', string)

@application.route('/passage')
def show_passage():
    nro = request.args.get('nro', type=str)
    start_pos = request.args.get('start', 1, type=int)
    end_pos = request.args.get('end', 1, type=int)
    dist = request.args.get('dist', 2, type=int)
    context = request.args.get('context', 2, type=int)
    hitfact = request.args.get('hitfact', 0.5, type=float)
    return _compact(view.passage.render(
                nro, start_pos, end_pos, dist=dist,
                context=context, hitfact=hitfact))

@application.route('/poemdiff')
@application.route('/runodiff')
def show_diff():
    nro_1 = request.args.get('nro1', 1, type=str)
    nro_2 = request.args.get('nro2', 1, type=str)
    return _compact(view.poemdiff.render(nro_1, nro_2))

@application.route('/multidiff')
def show_multidiff():
    nros_str = request.args.get('nro', 1, type=str)
    nros = nros_str.split(',')
    return _compact(view.multidiff.render(nros))

@application.route('/poem')
@application.route('/runo')
def show_poem():
    nro = request.args.get('nro', 1, type=str)
    hl_str = request.args.get('hl', None, type=str)
    hl = list(map(int, hl_str.split(','))) if hl_str is not None else []
    return _compact(view.poem.render(nro, hl))

@application.route('/verse')
def show_verse():
    nro = request.args.get('nro', None, type=str)
    pos = request.args.get('pos', 1, type=str)
    v_id = request.args.get('id', 1, type=int)
    return _compact(view.verse.render(nro=nro, pos=pos, v_id=v_id))

@application.route('/')
def index():
    return application.send_static_file('skvr-themes.html')
#    q = request.args.get('q', 'a', type=str).lower()
#    return view.index.render(q)

if __name__ == '__main__':
    application.run()

