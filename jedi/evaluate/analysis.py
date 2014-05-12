"""
Module for statical analysis.
"""

from jedi import debug
from jedi.parser import representation as pr
from jedi.evaluate.compiled import CompiledObject


CODES = {
    'attribute-error': (1, AttributeError, 'Potential AttributeError.'),
    'import-error': (2, ImportError, 'Potential ImportError.'),
    'type-error-generator': (3, TypeError, "TypeError: 'generator' object is not subscriptable."),
}


class Error(object):
    def __init__(self, name, module_path, start_pos):
        self.path = module_path
        self._start_pos = start_pos
        self.name = name

    @property
    def line(self):
        return self._start_pos[0]

    @property
    def column(self):
        return self._start_pos[1]

    @property
    def code(self):
        # The class name start
        first = self.__class__.__name__[0]
        return first + str(CODES[self.name][0])

    def description(self):
        return CODES[self.name][2]

    def __str__(self):
        return '%s: %s:%s' % (self.code, self.line, self.description())

    def __eq__(self, other):
        return (self.path == other.path and self.name == other.name
                and self._start_pos == other._start_pos)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.path, self._start_pos, self.name))

    def __repr__(self):
        return '<%s %s: %s@%s,%s' % (self.__class__.__name__,
                                     self.name, self.path,
                                     self._start_pos[0], self._start_pos[1])


class Warning(Error):
    pass


def add(evaluator, name, jedi_obj, typ=Error):
    exception = CODES[name][1]
    if _check_for_exception_catch(evaluator, jedi_obj, exception):
        return

    module_path = jedi_obj.get_parent_until().path
    instance = typ(name, module_path, jedi_obj.start_pos)
    debug.warning(str(instance))
    evaluator.analysis.append(instance)


def _check_for_exception_catch(evaluator, jedi_obj, exception):
    def check_match(cls):
        return isinstance(cls, CompiledObject) and cls.obj == exception

    def check_try_for_except(obj):
        while obj.next is not None:
            obj = obj.next
            for i in obj.inputs:
                except_classes = evaluator.eval_statement(i)
                for cls in except_classes:
                    from jedi.evaluate import iterable
                    if isinstance(cls, iterable.Array) and cls.type == 'tuple':
                        # multiple exceptions
                        for c in cls.values():
                            if check_match(c):
                                return True
                    else:
                        if check_match(cls):
                            return True
        return False

    while jedi_obj is not None and not jedi_obj.isinstance(pr.Function, pr.Class):
        if jedi_obj.isinstance(pr.Flow) and jedi_obj.command == 'try':
            if check_try_for_except(jedi_obj):
                return True
        jedi_obj = jedi_obj.parent
    return False
