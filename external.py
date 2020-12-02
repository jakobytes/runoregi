import urllib.parse

from config import BASE_URL, SHINY_URL


MAP_CODE = '''"u <- \\"{}{}\\"
d <- read_csv(content(GET(u))) %>% 
  mutate(place = str_replace(location, \\".* — \\", \\"\\")) %>%
  filter(!is.na(place)) %>%
  count(place)
o$tmap <- renderTmap(
  tm_shape(
    areas %>% left_join(d,by=c(\\"parish_name\\"=\\"place\\"))
  ) + tm_polygons(col=\\"n\\",id=\\"parish_name\\",palette=\\"plasma\\")
)
o$dt <- DT::renderDataTable(d)"'''.replace('\n', '\\n')

# TODO remove unused UI elements (e.g. the query string input)
UI_CODE = '''"wellPanel(
  textInput(\\"query\\",\\"Query string\\"),
  actionButton(\\"submit\\",\\"Query\\"),
  tmapOutput(\\"tmap\\"),
  DT::dataTableOutput(\\"dt\\")
)"'''.replace('\n', '\\n')


def make_map_link(view, **kwargs):
    params = '/' + view + '?' + \
        '&'.join(key+'='+str(val) for key, val in kwargs.items()) + \
        '&format=csv'
    code = MAP_CODE.format(BASE_URL, params)
    return SHINY_URL + '/?_inputs_&' + \
        urllib.parse.urlencode({
                'submit': 121,            # TODO explain
                'route': '"custom"',      # TODO explain
                'uic': UI_CODE,
                'c': code },
            quote_via=urllib.parse.quote)

