import config

def get_page_content(db, view):
    if not config.TABLES['runoregi_pages']: return
    db.execute('SELECT position, title, helptext, content FROM runoregi_pages'
               ' WHERE view = %s;', (view,))
    return [
      { 'position': r[0], 'title': r[1], 'helptext': r[2], 'content': r[3] } \
      for r in db.fetchall()
    ]
