import re
import unittest
from datetime import time
from typing import List

from registro import horario_to_time, Registro


class ReplaceTests(unittest.TestCase):
    def test_basic(self):
        src = [1, 2, 3, 4, 5]
        self.assertEqual([1, 2, 0, 4, 5], replace(src, 3, 0))
        self.assertEqual([1, 2, 3, 4, 5], src)

    def test_left_corner_case(self):
        src = [1, 2, 3, 4, 5]
        self.assertEqual([99, 2, 3, 4, 5], replace(src, 1, 99))
        self.assertEqual([1, 2, 3, 4, 5], src)

    def test_right_corner_case(self):
        src = [1, 2, 3, 4, 5]
        self.assertEqual([1, 2, 3, 4, 98], replace(src, 5, 98))
        self.assertEqual([1, 2, 3, 4, 5], src)

    def test_no_change_exc(self):
        src = [1, 2, 3, 4, 5]
        self.assertRaises(ValueError, replace, src, 42, 0)
        self.assertEqual([1, 2, 3, 4, 5], src)


def replace(l: List, what, _with) -> List:
    pos = l.index(what)
    return l[:pos] + [_with] + l[pos + 1:]


class TestSplitTime(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(time(hour=8, minute=45), horario_to_time('08:45'))

    def test_extra(self):
        self.assertEqual(time(hour=8, minute=32), horario_to_time('08:32:45'))


class DateRegexp(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.re = re.compile(Registro.REG)

    def test_basic(self):
        self.assertIsNotNone(self.re.match('(3/3)'))
        self.assertIsNotNone(self.re.match('(03/3)'))
        self.assertIsNotNone(self.re.match('(3/03)'))
        self.assertIsNotNone(self.re.match('(13/23)'))
        self.assertIsNone(self.re.match('(/23)'))
        self.assertIsNone(self.re.match('(213/23)'))
        self.assertIsNone(self.re.match('(213/243)'))
        self.assertIsNone(self.re.match('(23/243)'))
        self.assertIsNone(self.re.match('(23/)'))

    def test_basic_with_sapces(self):
        self.assertIsNotNone(self.re.match('(3/3 \t)'))
        self.assertIsNotNone(self.re.match('( 3/03)'))
        self.assertIsNotNone(self.re.match('(\t13/23)'))
        self.assertIsNotNone(self.re.match('(\t13/23)'))

    def test_basic_many(self):
        self.assertIsNotNone(self.re.match('(3/3 4/5 \t 6/7\t)'))

    def test_basic_many_desde(self):
        self.assertIsNotNone(self.re.match('(desde3/3 4/5 \t 6/7\t)'))
        self.assertIsNotNone(self.re.match('(desde:3/3 4/5 \t 6/7\t)'))
        self.assertIsNotNone(self.re.match('(desde: 3/3 4/5 \t 6/7\t)'))
        self.assertIsNotNone(self.re.match('(\tdesde: 3/3 4/5 \t 6/7\t)'))

    def test_search(self):
        SRC = '2/2 33/3 44/4 (\tdesde: 3/3 4/5 \t 6/7\t) 44/4'
        self.assertEqual(Registro.findsplits_materias(SRC), [1, 6, 11, 41])
        self.assertEqual(list(Registro.split_materias(SRC)),
                         ['2', '2 33', '3 44', '4 (\tdesde: 3/3 4/5 \t 6/7\t) 44', '4'])

    def test_materias_split(self):
        cases = [
            ('Electrodinámica Cuántica de Circuitos (FISI870188)/Electrodinámica Cuántica de Circuitos (DOC8801158)',
             ['Electrodinámica Cuántica de Circuitos (FISI870188)',
              'Electrodinámica Cuántica de Circuitos (DOC8801158)']),
            ('Introducción a la Fisiología Animal (BIOL190019)/Introducción a la Fisiología Molecular (BIOL840093)',
             ['Introducción a la Fisiología Animal (BIOL190019)',
              'Introducción a la Fisiología Molecular (BIOL840093)']),
            ('Teoría de Juegos (MATE820488)/Tópicos de Teoría de Juegos (DOC8800967)',
             ['Teoría de Juegos (MATE820488)', 'Tópicos de Teoría de Juegos (DOC8800967)']),

            ('Biometría (BIOL840002)(desde 20/03)', ['Biometría (BIOL840002)(desde 20/03)']),
            ('Introducción a la Fisiología Animal (BIOL190019)/Introducción a la Fisiología Molecular (BIOL840093)',
             ['Introducción a la Fisiología Animal (BIOL190019)',
              'Introducción a la Fisiología Molecular (BIOL840093)']),

            ('SEMANA DE LA MATEMATICA', ['SEMANA DE LA MATEMATICA']),
            ('Biometría (BIOL840002)(desde 20/03)', ['Biometría (BIOL840002)(desde 20/03)']),
            ('Laboratorio de Datos (LCDA210004) IC2', ['Laboratorio de Datos (LCDA210004) IC2']),
            ('Biometría (BIOL840002)(desde 20/03)', ['Biometría (BIOL840002)(desde 20/03)']),
            ('Bioinformática', ['Bioinformática']),
            ('Estadística 1', ['Estadística 1']),
            ('Meteorología Sinóptica (ATMO890028)', ['Meteorología Sinóptica (ATMO890028)']),
            ('Química Física I (QUIM870012)/Ecología y Comportamiento Animal',
             ['Química Física I (QUIM870012)', 'Ecología y Comportamiento Animal']),

            ('Ecología General (BIOL840003) (25/3-08/4-17/6)', ['Ecología General (BIOL840003) (25/3-08/4-17/6)']),
        ]

        for src, expected in cases:
            result = list(Registro.split_materias(src))
            print(result)
            self.assertEqual(expected, result)
