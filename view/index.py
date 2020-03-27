from flask import render_template
import os
import re


def render(q):
    index_letters = []
    for filename in sorted(os.listdir('data/index/')):
        m = re.match('index-([a-zäö]).txt', filename)
        if m is not None:
            index_letters.append(m.group(1))
    themes = []
    with open('data/index/index-{}.txt'.format(q)) as fp:
        for line in fp:
            code, title, poems = line.rstrip().split('\t')
            themes.append((code, title, poems.split(',')))
    return render_template('index.html', q=q, index_letters=index_letters,
                           themes=themes)

