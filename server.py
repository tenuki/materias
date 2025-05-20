import os
import sys
from datetime import datetime, timedelta, timezone
from itertools import combinations
from typing import List, Optional, Tuple

import pygsheets
import unicodedata


from flask import Flask, url_for, Response, render_template
from jinja2 import Template
from markdown import markdown
from markdown.extensions.tables import TableExtension

from registro import Registro, InvalidRegister, EmptyRegister, horario_to_time, time_plus_td, time_minus_td, phtml
from tests import replace


MAX_LINES = 10
DIR_NAME = os.path.dirname(os.path.realpath(__file__))
SPREADSHEET = "1pjtykzqGhaTkVfTNK7RsHHuu_u67hiA3jEsn0uMPLFY"
auth_key_file = os.path.join(DIR_NAME, 'sacc-aulas-sa-private-key.json')


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def get_timezone():
    return datetime.now(timezone.utc).astimezone().tzinfo


def at_utc():
    return get_timezone() == timezone.utc


utc_offset = lambda offset: timezone(timedelta(seconds=offset))


def now():
    if at_utc():
        return datetime.now(tz=utc_offset(-3 * 60 * 60))
    return datetime.now()


app = Flask(__name__, static_folder='static')

# ['Asignatura', 'Turno', 'Docente', 'Día', 'Fecha', 'Desde', 'Hasta', 'Pab.', 'Aula'
# ['Actividades', 'Turno', 'Clase', 'Día', 'Inicio', 'Fin', 'Pab.', 'Aula', 'RA', 'DOCENTE', '',

DATA = None
DATA_DATE = None
RAW_DATA = [[]]


def load(s_id):
    c = pygsheets.authorize(service_file=auth_key_file)
    s2 = c.open_by_key(s_id)
    # pprint(s2._sheet_list)
    lines = []
    # for sheetidx in range(6):
    for ws in s2._sheet_list:
        # print("%6s"% ws.hidden ," : ","%6s"% ws.title.startswith('2025-1'), ": ", ws.title)
        if ws.hidden: continue
        # if not ws.title.startswith('2025-1'): continue
        # ws = s2.worksheet('index', sheetidx)
        for line in ws.get_all_values():
            # print(', '.join(line))
            if all(x == '' for x in line): continue
            lines.append(line)
    return lines


def update():
    global DATA_DATE
    try:
        today = get_today()
        if DATA_DATE != today:
            DATA_DATE = today
            reload()
    except Exception as err:
        print(repr(err), file=sys.stderr)
        DATA_DATE = None


def reload():
    new_raw = load(SPREADSHEET)
    get_data(new_raw)
    return new_raw


def get_data(raw_data=None) -> List[Registro]:
    global DATA, RAW_DATA
    if raw_data is not None:
        DATA = RAW_DATA = format_data(raw_data)
    return DATA


def format_data(lines) -> List[Registro]:
    title = None
    keys = {}
    regs = []
    for line in lines:
        if title is None:
            title = ' '.join(line)
            continue
        if len(keys) == 0:
            for idx, key in enumerate(line):
                keys[idx] = key
            continue
        try:
            reg = Registro({keys[idx]: value for idx, value in enumerate(line) if value != ''})
        except EmptyRegister as err:
            continue
        except InvalidRegister as err:
            print('Error with: ', err)
            continue
        regs.append(reg)
    print('title ->', title)
    print('keys ->', list(keys.keys()))
    return regs


def render(template, **kw):
    myTemplate = Template(template)
    return myTemplate.render(datetime=datetime, str=str, repr=repr, enumerate=enumerate, phtml=phtml, **kw)


def readfile(*filename: str) -> str:
    if not isinstance(filename, str):
        filename = os.path.join(*filename)
    with open(filename, 'rb') as f:
        return f.read().decode('utf-8')


TABLE_EJS = readfile(DIR_NAME, 'templates', 'table.ejs')
READMEmd = readfile(DIR_NAME, 'README.md')


def renderfile(template_fname, **kw):
    lines = clines = 0
    chunks = []
    chunk = []
    for reg in kw.get('regs', []):
        lines += reg.lines
        clines += reg.lines
        if clines > kw.get('MAX_LINES', 1000):
            chunks.append(chunk)
            clines = reg.lines
            chunk = []
        chunk.append(reg.to_dict(kw.get('desde', horario_to_time(now_time_to_string()))))
    if chunk != [] and (chunks == [] or chunk != chunks[-1]):
        chunks.append(chunk)

    print("lines  -->", lines, file=sys.stderr)
    print("mats -->", [len(c) for c in chunks], file=sys.stdout)
    print("clines -->", [sum(len(x['materia']) for x in c) for c in chunks], file=sys.stdout)
    if chunks == []:
        chunks = [[]]
    kw.update({
        'None': None,
        'isinstance': isinstance,
        'list': list,
    })
    return render_template(template_fname, KEEP_AWAKE=False,
                           TABLE_EJS=TABLE_EJS, datetime=datetime, str=str, len=len, range=range, data=chunks,
                           repr=repr, enumerate=enumerate, phtml=phtml, now=now, **kw)


cinco_min = timedelta(minutes=5)


def merge(regs):
    extract = []

    def find_match(w: Registro) -> Optional[Registro]:
        for x in extract:
            if w.cmp_reg_eq(x):
                return x

    for reg in regs:
        match = find_match(reg)
        if match:
            if not match.is_composite():
                composite = match.to_composite()
                extract = replace(extract, match, composite)
                match = composite
            match.add_composition(reg)
        else:
            extract.append(reg)
    return extract


################################################## WebAPP endpoints ####################################################

def choose(msg, options):
    choose_tpl = """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>-</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css">
  </head>
  <body>
  <section class="section">
    <div class="container">
      <h1 class="title">{{msg}}</h1>
    </div>
  </section>
  <section>
    <div class="container">
                <nav class="pagination is-centered" role="navigation" aria-label="pagination"> 
                  <ul class="pagination-list">    
                    {% for name, link in options %}
                           <li>
                              <a href="{{link}}" class="pagination-link" aria-label="elije pabellon {{name}}">{{name}}</a>
                            </li>
                    {%endfor%}
                  </ul>
                </nav>
    </div>
  </section>
  </body>
</html>"""

    """<nav class="pagination" role="navigation" aria-label="pagination">
  <a class="pagination-previous is-disabled" title="This is the first page"
    >Previous</a
  >
  <a href="#" class="pagination-next">Next page</a>
  <ul class="pagination-list">
    <li>
      <a
        class="pagination-link is-current"
        aria-label="Page 1"
        aria-current="page"
        >1</a
      >
    </li>
    <li>
      <a href="#" class="pagination-link" aria-label="Goto page 2">2</a>
    </li>
    <li>
      <a href="#" class="pagination-link" aria-label="Goto page 3">3</a>
    </li>
  </ul>
</nav>"""
    return render(choose_tpl, msg=msg, options=options)


@app.route('/reloadxxx')
def _reload():
    img = reload()
    return repr(img)


@app.route("/human/")
def human():
    names = {0:'0+inf', 1:'1', 2:'2', 3:'3'}
    aulas = [0, 1, 2]
    opts = []
    for l in range(1, len(aulas)+1):
        for comb in combinations(aulas, l):
            opts.append(
                (
                    ' + '.join(names[x] for x in comb),
                    url_for('bypabellon', pabellon=''.join(str(x) for x in comb)),
                )
            )
    return choose('Elegir pabellón', opts)


@app.route("/human/<pabellon>")
def bypabellon(pabellon):
    return choose('Elegir día',
                  [
                      ('auto', url_for('byday', pabellon=pabellon, day='today')),
                      ('lunes', url_for('byday', pabellon=pabellon, day='lunes')),
                      ('martes', url_for('byday', pabellon=pabellon, day='martes')),
                      ('miércoles', url_for('byday', pabellon=pabellon, day='miercoles')),
                      ('jueves', url_for('byday', pabellon=pabellon, day='jueves')),
                      ('viernes', url_for('byday', pabellon=pabellon, day='viernes')),
                      ('sábado', url_for('byday', pabellon=pabellon, day='sabado')),
                  ])


@app.route("/human/<pabellon>/<day>")
def byday(pabellon, day):
    update()
    _day = strip_accents(day.lower())
    regs = [reg for reg in get_data() if reg.pabellon == pabellon and strip_accents(reg.dia.lower()) == _day]
    regs.sort(key=lambda reg: reg.desde_num)
    return renderfile('original.jinja', regs=regs, dia=day, pabellon=pabellon,
                      data_url=[('data', url_for('json_bypabellon', day=day, pabellon=pabellon))])


def get_today():
    m = now().date().weekday()
    if m == 0:
        _day = "lunes"
    elif m == 1:
        _day = "martes"
    elif m == 2:
        _day = "miercoles"
    elif m == 3:
        _day = "jueves"
    elif m == 4:
        _day = "viernes"
    elif m == 5:
        _day = "sabado"
    else:
        _day = "domingo"
    return _day


@app.route("/v/<pabellon>")
@app.route("/v/<pabellon>/")
@app.route("/v/<pabellon>/<desde>")
@app.route("/v/<pabellon>/<desde>/")
def last_url_v(pabellon, desde=None):
    return last_url_(pabellon, 20, 14, 'last_url_v', desde)


@app.route("/h/<pabellon>")
@app.route("/h/<pabellon>/")
@app.route("/h/<pabellon>/<desde>")
@app.route("/h/<pabellon>/<desde>/")
def last_url_h(pabellon, desde=None):
    return last_url_(pabellon, 10, 7, 'last_url_h', desde)


@app.route("/x/<pabellon>")
@app.route("/x/<pabellon>/")
@app.route("/x/<pabellon>/<desde>")
@app.route("/x/<pabellon>/<desde>/")
def last_url_x(pabellon, desde=None):
    desde = horario_to_time('14:00' if desde is None else desde)
    return last_url_(pabellon, 20, 14, 'last_url_x', desde, 'lunes')


@app.route("/y/<pabellon>")
@app.route("/y/<pabellon>/")
@app.route("/y/<pabellon>/<desde>")
@app.route("/y/<pabellon>/<desde>/")
def last_url_y(pabellon, desde=None):
    desde = horario_to_time('14:00' if desde is None else desde)
    return last_url_(pabellon, 10, 7, 'last_url_y', desde, 'lunes')


def now_time_to_string():
    _now = now()
    return '%02d:%02d' % (_now.hour, _now.minute)


def last_url_(pabellon, MAX_LINES, WAIT_SECS, fname, desde=None, dia=None):
    # if not(desde is None):
    #     desde = horario_to_time(desde)
    # else:
    #     desde = horario_to_time(now_time_to_string())
    desde = horario_to_time(now_time_to_string() if desde is None else desde)
    dia = get_today() if dia is None else dia
    _prev = url_for(fname, pabellon=pabellon, desde=time_minus_td(desde, cinco_min))
    _next = url_for(fname, pabellon=pabellon, desde=time_minus_td(desde, -1 * cinco_min))
    return bypabellon_parts(dia, pabellon, MAX_LINES=MAX_LINES, WAIT_SECS=WAIT_SECS, desde=desde, prev=_prev,
                            next=_next)



@app.route("/final/<day>/<pabellon>/")
@app.route("/final/<day>/<pabellon>/<desde>")
@app.route("/final/<day>/<pabellon>/<desde>/")
def bypabellon_parts(day, pabellon, desde=None, MAX_LINES=10, WAIT_SECS=7, prev=None, next=None):
    update()
    if not (desde is None):
        desde = horario_to_time(desde)
    _day = strip_accents(day.lower())
    if _day == 'today':
        day = _day = get_today()

    print(f"filtering for: {_day} @ {desde}")
    s_pabellon = set(pabellon)
    regs = [reg for reg in get_data() if reg.pabellon in s_pabellon and strip_accents(reg.dia.lower()) == _day]
    regs.sort(key=lambda reg: reg.desde_num)
    print("Unfiltered len: {}".format(len(regs)))
    if desde is None:
        if regs != []:
            desde = time_minus_td(regs[0].desde_num, cinco_min)
        else:
            desde = horario_to_time('05:00')

    _from, _to = time_minus_td(desde, timedelta(minutes=10)), time_plus_td(desde, timedelta(minutes=45))
    regs = [reg for reg in regs if
            (reg.desde_num <= _to and reg.hasta_num >= _from)]

    # |<--------->| pre |now| dur |<---------->|
    #   |<-->|
    #   |<--------->|
    #   |<--------------->|
    #   |<--------------------->|
    #   |<------------------------------>|
    #                 |<-->|
    #                 |<--------->|
    #                 |<--------------->|
    #                    |<-->|
    #                    |<--------->|
    #                    |<--------------->|
    #                         |<-->|
    #                         |<--------->|
    #                         |<--------------->|
    #                                 |<-->|
    #
    regs = merge(regs)
    show_pabellon = 0 if len(pabellon) == 1 else 1
    prev = url_for('bypabellon_parts', day=day, pabellon=pabellon,
                   desde=time_minus_td(desde, cinco_min)) if prev is None else prev
    next = url_for('bypabellon_parts', day=day, pabellon=pabellon,
                   desde=time_minus_td(desde, -1 * cinco_min)) if next is None else next
    data = renderfile('final2.jinja', regs=regs, dia=_day, pabellon=pabellon, show_pabellon=show_pabellon,
                      desde=desde, _from=_from, _to=_to, MAX_LINES=MAX_LINES, WAIT_SECS=WAIT_SECS,
                      data_url=[('prev', prev), ('next', next)])
    response = Response(data)
    response.headers['Permissions-Policy'] = 'fullscreen=*'
    return response


@app.route("/")
def root(pabellon='0', desde=None):
    READMEhtml = markdown(READMEmd, extensions=['def_list', TableExtension(use_align_attribute=True)])
    data = READMEhtml + '<br/><br/>' + human()
    desde = horario_to_time(now_time_to_string() if desde is None else desde)
    data = renderfile('alerta.jinja', regs=[], pabellon=pabellon,
                      desde=desde,  MAX_LINES=MAX_LINES, WAIT_SECS=10,
                      url=None,
                      content=data,
                      )
    response = Response(data)
    response.headers['Permissions-Policy'] = 'fullscreen=*'
    return response



@app.route("/json/")
def _json():
    update()
    return get_data()


@app.route("/json/<day>")
def json_byday(day):
    update()
    _day = strip_accents(day.lower())
    regs = [reg for reg in get_data() if strip_accents(reg.dia.lower()) == _day]
    regs.sort(key=lambda reg: reg.desde_num)
    return regs


@app.route("/json/<day>/<pabellon>")
def json_bypabellon(day, pabellon):
    update()
    _day = strip_accents(day.lower())
    regs = [reg for reg in get_data() if reg.pabellon == pabellon and strip_accents(reg.dia.lower()) == _day]
    regs.sort(key=lambda reg: reg.desde_num)
    return regs


def get_app():
    """Used to return _app_ instance to waitress server. Do not remove!"""
    return app


if __name__ == "__main__":
    pass
