import csv
from io import StringIO
from operator import itemgetter
import re


def clean_special_chars(text):
    text = re.sub('[@$^_\xb0\xa8\u02c7\u20ac\u2020]', '', text)
    return text


def link(view, args, defaults):
    'Generates a link to a certain view with specified option settings.'

    def _str(value):
        if isinstance(value, list):
            return ','.join(map(str, value))
        elif isinstance(value, bool):
            return str(value).lower()
        else:
            return str(value)

    link = '/{}?'.format(view) + \
        '&'.join('{}={}'.format(key, _str(args[key]))
        for key in args if args[key] != defaults[key])
    return link


def render_csv(rows, header=None, delimiter=','):
    stream = StringIO()
    writer = csv.writer(stream, delimiter=delimiter, lineterminator='\n')
    if header is not None:
        writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue()


def print_type_list(poem, types):
    result = []
    for type_id in poem.type_ids + poem.minor_type_ids:
        t_ids = [type_id] + types[type_id].ancestors
        t_ids.reverse()
        result.append(' > '.join(types[x].name for x in t_ids))
    return '\n'.join(result)

def makecol(value, base, max_value):
    'Converts a numeric value to a color (higher value=darker color).'

    def _makecolcomp(value, base, max_value):
        result = hex(base + int((255-base)*(1-value/max_value)))[2:]
        if len(result) == 1:
            result = '0'+result
        return result

    if value is None:
        value = 1
    val_norm = min(value, max_value)
    val_norm = max(0, val_norm)
    base_rgb = (int(base[:2], base=16),
                int(base[2:4], base=16),
                int(base[4:6], base=16))
    r = _makecolcomp(val_norm, base_rgb[0], max_value)
    g = _makecolcomp(val_norm, base_rgb[1], max_value)
    b = _makecolcomp(val_norm, base_rgb[2], max_value)
    return '#'+r+g+b
