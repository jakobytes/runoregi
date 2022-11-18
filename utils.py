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
