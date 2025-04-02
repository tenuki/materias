from datetime import time

import sys
from pprint import pprint

import pygsheets

auth_key_file = r'.\sacc-aulas-sa-private-key.json'


class InvalidRegister(Exception):
    pass


class EmptyRegister(Exception):
    pass


def horario_to_time(charstring):
    h, m = charstring.split(':')
    return time(hour=int(h), minute=int(m))


# class Registro(dict):
#     def __init__(self, registro):
#         if registro == {}:
#             raise EmptyRegister(f'Empty registro: %r')
#         super(Registro, self).__init__(registro)
#         for req in ['Asignatura', 'Desde', 'Hasta', 'Día', 'Pab.', 'Aula']:
#             if self.get(req) is None:
#                 raise InvalidRegister(f'Invalid {req} registro: %r' % self)
#
#     @property
#     def materia(self):
#         return self['Asignatura']
#
#     @property
#     def desde(self):
#         return self['Desde']
#
#     @property
#     def hasta(self):
#         return self['Hasta']
#
#     @property
#     def desde_num(self):
#         return horario_to_time(self['Desde'])
#
#     @property
#     def hasta_num(self):
#         return horario_to_time(self['Hasta'])
#
#     @property
#     def dia(self):
#         return self['Día']
#
#     @property
#     def turno(self):
#         return self.get('Turno', '-')
#
#     @property
#     def pabellon(self):
#         return self['Pab.']
#
#     @property
#     def aula(self):
#         return self['Aula']

def load(s_id):
    c = pygsheets.authorize(service_file=auth_key_file)
    s2 = c.open_by_key(s_id)
    pprint(s2._sheet_list)
    print(1, file=sys.stderr)
    lines = []
    if True:
        sheetidx = 6
        pass
    for sheetidx in range(6):
        ws = s2.worksheet('index', sheetidx)
        for line in ws.get_all_values():
            if all(x == '' for x in line):
                continue
            lines.append(line)
    print(repr(lines))
    return lines


if __name__ == "__main__":
    load("1pjtykzqGhaTkVfTNK7RsHHuu_u67hiA3jEsn0uMPLFY")
