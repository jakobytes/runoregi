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
