import urllib.parse

from config import BASE_URL, SHINY_URL


def make_map_link(view, **kwargs):
    params = '/' + view + '?' + \
        '&'.join(key+'='+str(val) for key, val in kwargs.items()) + \
        '&format=csv'
    myurl = BASE_URL + params
    return SHINY_URL + '/?_inputs_&' + \
        urllib.parse.urlencode({
                'route': '"rrmap"',
                'rrmap-d': '"'+myurl+'"' },
            quote_via=urllib.parse.quote)

