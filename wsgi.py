from flask import Flask, request

import view.index
import view.poem
import view.poemdiff
import view.verse


application = Flask(__name__)

@application.route('/poemdiff')
@application.route('/runodiff')
def show_diff():
    nro_1 = request.args.get('nro1', 1, type=str)
    nro_2 = request.args.get('nro2', 1, type=str)
    return view.poemdiff.render(nro_1, nro_2)

@application.route('/poem')
@application.route('/runo')
def show_poem():
    nro = request.args.get('nro', 1, type=str)
    hl = request.args.get('hl', None, type=int)
    return view.poem.render(nro, hl)

@application.route('/verse')
def show_verse():
    v_id = request.args.get('id', 1, type=str)
    return view.verse.render(v_id)

@application.route('/')
def index():
    q = request.args.get('q', 'a', type=str).lower()
    return view.index.render(q)

if __name__ == '__main__':
    application.run()

