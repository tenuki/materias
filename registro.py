from datetime import timedelta, datetime, time


def horario_to_time(charstring):
    if isinstance(charstring, time):
        return charstring
    charstring = charstring.replace(';', ':')
    various = charstring.split(':')
    return time(hour=int(various[0]), minute=int(various[1]))


def time_minus_td(atime: time, adelta: timedelta) -> time:
    dtfrom = datetime(1980, 1, 1, atime.hour, atime.minute, atime.second)
    result = dtfrom - adelta
    return result.time()


#def time_plus_td(atime: time, adelta: timedelta) -> time:
def time_plus_td(atime, adelta):
    try:
        dtfrom = datetime(1980, 1, 1, atime.hour, atime.minute, atime.second)
    except Exception as err:
        dtfrom = dtfrom
    result = dtfrom + adelta
    return result.time()


class InvalidRegister(Exception):
    pass


class EmptyRegister(Exception):
    pass


class Registro(dict):
    # CompositionRegisters = ['Asignatura', 'Desde', 'Hasta', 'Día', 'Pab.']
    CompositionRegisters = ['Actividades', 'Inicio', 'Fin', 'Día', 'Pab.']

    def __init__(self, registro):
        if registro == {}:
            raise EmptyRegister(f'Empty registro: %r')
        super(Registro, self).__init__(registro)
        for req in self.CompositionRegisters + ['Aula']:
            if self.get(req) is None:
                raise InvalidRegister(f'Invalid {req} registro: %r' % self)

    def to_dict(self, desde):
        return {'desde':self.desde, 'hasta':self.hasta,
                'is_composite':self.is_composite(),
                'aula':self.aula,
                'turno': self.turno,
                'materia': self.materia.split('/'),
                'classcolor': self.color_to_class(desde),
                'phtml': phtml(self),
                'fecha': self.fecha,
                }

    @property
    def materia(self):
        return self['Actividades']

    @property
    def desde(self):
        return self['Inicio']

    @property
    def hasta(self):
        return self['Fin']

    @property
    def desde_num(self):
        return horario_to_time(self.desde)

    @property
    def hasta_num(self):
        return horario_to_time(self.hasta)

    @property
    def dia(self):
        return self['Día']

    @property
    def turno(self):
        return self.get('Turno', '')

    @property
    def pabellon(self):
        return self['Pab.']

    @property
    def aula(self):
        return self['Aula']

    @property
    def fecha(self):
        return self.get('Fecha', '')

    def is_composite(self):
        return False

    def to_composite(self):
        return CompositeReg(self)

    def cmp_reg_eq(self, other):
        return all(self[key] == other[key] for key in self.CompositionRegisters)

    def terminando(self, at):
        return self.hasta_num <= time_plus_td(at, timedelta(minutes=40))

    def empezadas(self, at):
        return not self.terminando(at) and not self.por_empezar(at)

    def por_empezar(self, at):
        return self.desde_num >= time_plus_td(at, timedelta(minutes=10))

    def color(self, at):
        if self.terminando(at):
            return 'red'
        if self.por_empezar(at):
            return 'blue'
        return 'lightgreen'

    def color_to_class(self, at):
        if self.terminando(at):
            return 'has-text-danger'
        if self.por_empezar(at):
            return 'has-text-warning'
        return 'has-text-success'

    @property
    def lines(self):
        lines = 1 if self.is_composite() else 0
        return lines + self.materia.count('/') + 1


class CompositeReg(Registro):
    def __init__(self, registro):
        self.components = {}
        super(CompositeReg, self).__init__(registro)

    def add_composition(self, other):
        self.components[other.aula] = other

    def is_composite(self):
        return True

    def to_composite(self):
        return self

    def to_dict(self, desde):
        ret = super().to_dict(desde)
        ret.update({'components': [sub.to_dict(desde)
                                    for aula, sub in self.components.items()]})
        return ret


def phtml(adict):
    return '\n'.join(  '%s : %s'%kv for kv in adict.items()   )
