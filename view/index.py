import os
import re


def render(q):
    result = []
    result.append('<center><h2>')
    index_letters = []
    for filename in sorted(os.listdir('data/index/')):
        m = re.match('index-([a-zäö]).txt', filename)
        if m is not None:
            index_letters.append(m.group(1))
    result.append(' |\n'.join(
        ('<a href="/?q={}">{}</a>'.format(x, x.upper()) if x != q \
         else '<b>{}</b>'.format(x.upper())) \
        for x in index_letters))
    result.append('</h2></center>')
    result.append('<table border="1">')
    result.append('<tr><td><b>code</b></td><td><b>title</b></td><td><b>poems</b></td></tr>')
    with open('data/index/index-{}.txt'.format(q)) as fp:
        for line in fp:
            code, title, poems = line.rstrip().split('\t')
            result.append('<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
                code,
                title,
                ',\n'.join('<a href="/poem?nro={}">{}</a>'.format(x, x) \
                           for x in poems.split(','))))
    result.append('</table>')
    return '\n'.join(result)

