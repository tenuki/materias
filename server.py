import os
import unittest
from datetime import time, datetime, timedelta, timezone
from pprint import pprint
import sys
from typing import List, Optional

import pygsheets
import unicodedata


from flask import Flask, url_for, Response, render_template
from jinja2 import Template

from registro import Registro, InvalidRegister, EmptyRegister, horario_to_time, time_plus_td, time_minus_td, phtml


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
    return get_timezone()==timezone.utc

utc_offset = lambda offset: timezone(timedelta(seconds=offset))

def now():
    if at_utc():
       return datetime.now(tz=utc_offset(-3*60*60))
    return datetime.now()


app = Flask(__name__)


# ['Asignatura', 'Turno', 'Docente', 'Día', 'Fecha', 'Desde', 'Hasta', 'Pab.', 'Aula'
# ['Actividades', 'Turno', 'Clase', 'Día', 'Inicio', 'Fin', 'Pab.', 'Aula', 'RA', 'DOCENTE', '',

DATA = None
DATA_DATE = None
RAW_DATA = [[]]


class TestSplitTime(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(time(hour=8,minute=45), horario_to_time('08:45'))
    def test_extra(self):
        self.assertEqual(time(hour=8,minute=32), horario_to_time('08:32:45'))



def load(s_id):
    c = pygsheets.authorize(service_file=auth_key_file)
    s2 = c.open_by_key(s_id)
    pprint(s2._sheet_list)
    print(1, file =sys.stderr)
    lines = []
    #for sheetidx in range(6):
    for ws in s2._sheet_list:
        if not ws.title.startswith('2025-1'): continue
        #ws = s2.worksheet('index', sheetidx)
        for line in ws.get_all_values():
            # print(', '.join(line))
            if all(x=='' for x in line): continue
            lines.append(line)
    print(repr(lines))
    return lines


def update():
    global DATA_DATE
    try:
        today = get_today()
        if DATA_DATE!=today:
            DATA_DATE = today
            reload()
    except:
        pass


def reload():
    new_raw = load(SPREADSHEET)
    get_data(new_raw)
    return new_raw


def get_data(raw_data=None) -> List[Registro]:
    global DATA
    if raw_data is None:
       raw_data = RAW_DATA
    if DATA is None:
        DATA = format_data(raw_data)
    return DATA


def format_data(lines) -> List[Registro]:
    title = None
    keys = {}
    regs = []
    for line in lines:
        if title is None:
            title = ' '.join(line)
            continue
        if len(keys)==0:
            for idx, key in enumerate(line):
                keys[idx]=key
            continue
        try:
            reg = Registro({keys[idx]:value for idx, value in enumerate(line) if value != ''})
        except EmptyRegister as err:
            continue
        except InvalidRegister as err:
            print('Error with: ',err)
            continue
        regs.append(reg)
    print('title ->', title)
    print('keys ->', list(keys.keys()))
    return regs


def render(template, **kw):
    myTemplate = Template(template)
    return myTemplate.render(datetime=datetime, str=str, repr=repr, enumerate=enumerate, phtml=phtml, **kw)


with open(os.path.join(DIR_NAME, 'templates', 'table.ejs'), 'r') as f:
    TABLE_EJS = f.read()


def renderfile(template_fname, **kw):
    lines = clines = 0
    chunks = []
    chunk = []
    for reg in kw.get('regs', []):
        lines += reg.lines
        clines += reg.lines
        if clines>kw.get('MAX_LINES', 1000):
            chunks.append(chunk)
            clines = reg.lines
            chunk = []
        chunk.append(reg.to_dict(kw.get('desde',   horario_to_time(now_time_to_string()) )))
    if chunk!=[] and (chunks==[] or chunk!=chunks[-1]):
        chunks.append(chunk)

    print("lines  -->", lines, file=sys.stderr)
    print("mats -->", [len(c) for c in chunks], file=sys.stdout)
    print("clines -->", [sum(len(x['materia']) for x in c) for c in chunks], file=sys.stdout)
    if chunks == []:
        chunks = [[]]
    return render_template(template_fname,
                           TABLE_EJS=TABLE_EJS, datetime=datetime, str=str, len=len, range=range, data=chunks,
                           repr=repr, enumerate=enumerate, phtml=phtml, now=now, **kw)


cinco_min = timedelta(minutes=5)


def replace(l: List, what, _with) -> List:
    pos = l.index(what)
    return l[:pos]+[_with]+l[pos+1:]


class ReplaceTests(unittest.TestCase):
    def test_basic(self):
        src = [1,2,3,4,5]
        self.assertEqual([1,2,0,4,5], replace(src, 3, 0))
        self.assertEqual([1, 2, 3, 4, 5], src)

    def test_left_corner_case(self):
        src = [1,2,3,4,5]
        self.assertEqual([99,2,3,4,5], replace(src, 1, 99))
        self.assertEqual([1, 2, 3, 4, 5], src)

    def test_right_corner_case(self):
        src = [1,2,3,4,5]
        self.assertEqual([1,2,3,4,98], replace(src, 5, 98))
        self.assertEqual([1, 2, 3, 4, 5], src)

    def test_no_change_exc(self):
        src = [1,2,3,4,5]
        self.assertRaises(ValueError, replace, src, 42, 0)
        self.assertEqual([1, 2, 3, 4, 5], src)


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
    <title>Hello Bulma!</title>
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


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route('/reloadxxx')
def _reload():
    img = reload()
    return repr(img)


@app.route("/human/")
def human():
    return choose('Elegir pabellón',
        [
            ('0+inf', url_for('bypabellon', pabellon='0')),
            ('1', url_for('bypabellon', pabellon='1')),
            ('2', url_for('bypabellon', pabellon='2')),
        ]
    )
               
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
        ]
    )


@app.route("/human/<pabellon>/<day>")
def byday(pabellon, day):
    update()
    _day = strip_accents(day.lower())
    regs = [reg for reg in get_data() if reg.pabellon == pabellon and strip_accents(reg.dia.lower()) == _day]
    regs.sort(key=lambda reg: reg.desde_num)
    return renderfile('original.jinja', regs=regs, dia=day, pabellon=pabellon,
                  data_url=[('data', url_for('json_bypabellon', day=day, pabellon=pabellon))])
    # return render(TEMPLATE, regs=regs, dia=day, pabellon=pabellon,
    #               data_url=[('data', url_for('json_bypabellon', day=day, pabellon=pabellon))])


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


def now_time_to_string():
    _now = now()
    return '%02d:%02d' % (_now.hour, _now.minute)

def last_url_(pabellon, MAX_LINES, WAIT_SECS, fname, desde=None):
    if not(desde is None):
        desde = horario_to_time(desde)
    else:
        desde = horario_to_time(now_time_to_string())

    _prev =  url_for(fname, pabellon=pabellon, desde=time_minus_td(desde, cinco_min))
    _next = url_for(fname, pabellon=pabellon, desde=time_minus_td(desde, -1*cinco_min))
    return bypabellon_parts(get_today(), pabellon, MAX_LINES=MAX_LINES, WAIT_SECS=WAIT_SECS, desde=desde,
                            prev=_prev, next=_next)



@app.route("/final/<day>/<pabellon>")
@app.route("/final/<day>/<pabellon>/")
@app.route("/final/<day>/<pabellon>/<desde>")
@app.route("/final/<day>/<pabellon>/<desde>/")
def bypabellon_parts(day, pabellon, desde=None, MAX_LINES=10, WAIT_SECS=7, prev=None, next=None):
    update()
    if not(desde is None):
        desde = horario_to_time(desde)
    _day = strip_accents(day.lower())
    if _day=='today':
        day = _day = get_today()

    regs = [reg for reg in get_data() if reg.pabellon == pabellon and strip_accents(reg.dia.lower()) == _day]
    regs.sort(key=lambda reg: reg.desde_num)
    if desde is None:
        if regs != []:
            desde = time_minus_td(regs[0].desde_num, cinco_min)
        else:
            desde = horario_to_time('05:00')

    _from, _to = time_minus_td(desde, timedelta(minutes=10)), time_plus_td(desde, timedelta(minutes=45))
    regs = [reg for reg in regs if
            (reg.desde_num<=_to and reg.hasta_num>=_from)]

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
    prev =  url_for('bypabellon_parts', day=day, pabellon=pabellon, desde=time_minus_td(desde, cinco_min)) if prev is None else prev
    next = url_for('bypabellon_parts', day=day, pabellon=pabellon, desde=time_minus_td(desde, -1*cinco_min)) if next is None else next
    data = renderfile('final2.jinja', regs=regs, dia=_day, pabellon=pabellon,
                      desde=desde, _from=_from, _to=_to, MAX_LINES=MAX_LINES, WAIT_SECS=WAIT_SECS,
                  data_url=[ ('prev', prev), ('next', next) ])
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


if __name__ == "__main__":
  # data = load("1pjtykzqGhaTkVfTNK7RsHHuu_u67hiA3jEsn0uMPLFY")
  pass  # get_data()
