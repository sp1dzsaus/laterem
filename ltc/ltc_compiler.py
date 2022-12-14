try:
    from .ltc_builtins import *
    from .ltc_core import *
    from context_objects import LATEREM_FLAGS, LTC_CheckerShortcuts, LTC_SingleStorage
except ImportError:
    from ltc_builtins import *
    from ltc_core import *
    LTC_CheckerShortcuts = LTC_SingleStorage = True
    LATEREM_FLAGS = {True}

VERSION = 0.4
RECOMPILATION_ATTEMPTS = 100


class LTC:
    def __init__(self, field_table, namespace, checker_functions, forbidden_cases):
        self.field_table = field_table
        self.checker_functions = checker_functions
        self.forbidden_cases = forbidden_cases
        self.namespace = namespace
        self.executed = False
    
    def get_answer_fields(self):
        return [x[0] for x in self.checker_functions]
    
    def mask_answer_dict(self, __dict):
        return {key: __dict[key] for key in self.get_answer_fields()}

    @classmethod
    def from_dict(cls, data):
        executed = True
        namespace = {}
        field_table = data['field_values']
        checker_functions = []
        forbidden_cases = []
        for checkerobj in data['checkers']:
            function = KEYWORD_TABLE[checkerobj['function']](*checkerobj['args'])
            field = checkerobj['field']
            checker_functions.append((field, function))
        for checkerobj in data['forbidders']:
            function = KEYWORD_TABLE[checkerobj['function']](*checkerobj['args'])
            field = checkerobj['field']
            forbidden_cases.append((field, function))
        ltc = cls(field_table, namespace, checker_functions, forbidden_cases)
        ltc.executed = executed 
        return ltc

    def to_dict(self):
        if not self.executed: self.execute()
        mainobj = {}
        mainobj['field_values'] = self.field_table
        mainobj['checkers'] = []
        mainobj['forbidders'] = []
        for field, checker in self.checker_functions:
            checkerobj = {}
            checkerobj['function'] = INVERSE_TABLE[checker.__class__]
            checkerobj['args'] = checker.args
            checkerobj['field'] = field
            mainobj['checkers'].append(checkerobj)
        for field, checker in self.forbidden_cases:
            checkerobj = {}
            checkerobj['function'] = INVERSE_TABLE[checker.__class__]
            checkerobj['args'] = checker.args
            checkerobj['field'] = field
            mainobj['forbidders'].append(checkerobj)
        return mainobj
    
    def execute(self, timeout=RECOMPILATION_ATTEMPTS):
        if not timeout:
            raise LTCError(f"LTC could not fit user forbidden cases conditions for {RECOMPILATION_ATTEMPTS} attempts of recompilation.")
        new_field_table = {}
        new_checker_functions = []
        new_forbidden_cases = []

        for key, value in self.field_table.items():
            new_field_table[key] = value.compile(new_field_table)(ns=new_field_table)
        for field, value in self.checker_functions:
            new_checker_functions.append((field, value.compile(new_field_table)))
        for field, value in self.forbidden_cases:
            new_forbidden_cases.append((field, value.compile(new_field_table)))

        if not LTC.validate(new_field_table, new_checker_functions, new_forbidden_cases):
            return self.execute(timeout-1)
        
        del self.field_table
        del self.checker_functions
        del self.forbidden_cases
        self.field_table = new_field_table
        self.checker_functions = new_checker_functions
        self.forbidden_cases = new_forbidden_cases
        self.executed = True
    
    @staticmethod
    def validate(field_table, checker_functions, forbidden_cases):
        valid = True
        for field, checker in forbidden_cases:
            valid = valid and not checker(field_table[field])
        return valid

    def check(self, fields):
        valid = True
        for field, checker in self.checker_functions:
            valid = valid and checker(fields[field])
        return valid
    

class LTCCompiler:
    def _typevalue(txt: str):
        txt = txt.strip()
        if txt[-1] == txt[0] == '"':
            txt = txt.strip('"')
            return LTCValue(txt)
        elif txt[-1] == txt[0] == "'":
            txt = txt.strip("'")
            return LTCValue(txt)
        elif txt.lstrip('-').replace(".", "", 1).isdigit():
            return LTCValue(txt)
        elif txt[0] == '[' and txt[-1] == ']':
            args = txt[1:-1].split(',')
            args = LTCCompiler._combine_kws(args, ',')
            args = [LTCCompiler._typevalue(arg) for arg in args]
            return LTCValue(args)
        elif '(' in txt and txt[-1] == ')':
            return LTCCompiler._build_func(txt)
        else:
            return LTCAllias(txt)

    def _build_func(txt):
        fname = txt[:txt.find('(')]
        try:
            func = KEYWORD_TABLE[fname]
        except KeyError:
            raise LTCCompileError('Unknown function ' + fname + '. Maybe you forgot to import it?')
        args = txt[txt.find('(') + 1:-1].split(',')
        args = LTCCompiler._combine_kws(args, ',')
        fargs = [LTCCompiler._typevalue(arg) for arg in args]
        return func(*fargs)

    def _combine_kws(kws, joiner=' '):
        for i, kw in enumerate(kws):
            if kw is None:
                continue
            kw = kw.strip()
            if kw.startswith('['):
                LTCCompiler._combine_kw(i, '[', ']', kws, joiner)
            elif kw.startswith('"'):
                LTCCompiler._combine_kw(i, '"', '"', kws, joiner)
            elif kw.startswith("'"):
                LTCCompiler._combine_kw(i, "'", "'", kws, joiner)
            elif '(' in kw:
                LTCCompiler._combine_kw(i, '(', ')', kws, joiner)
            
        kws = [kw for kw in kws if kw]
        return kws

    def _combine_kw(origin, opener, closer, kws, joiner=' '):
        kw = kws[origin]
        ff = kw
        if opener != closer:
            runf = lambda _: ff.count(opener) != ff.count(closer) 
        else:
            runf = lambda _: ff.count(opener) % 2 != 0
        i = origin
        while runf(...):
            i += 1
            ff += joiner + kws[i]
            kws[i] = None
        kws[origin] = ff

    def compile(self, txt):
        COMPILER_VERSION = 0.4
        if COMPILER_VERSION != VERSION:
            raise NotImplemented

        if LTC_SingleStorage in LATEREM_FLAGS:
            namespace = field_table = {}
        else:
            namespace = {}
            field_table = {}

        checker_functions = []
        forbidden_cases = []
        if txt[:9] == '[VERBAL]\n':
            return self.compile_alt(txt[9:])

        code = txt.split('\n')

        for line in code:
            if '#' in line:
                line = line[:line.find('#')]
            line = line.strip()
            if not line:
                continue
            if ':=' in line:
                linemode = 'contain'
                line = line.replace(':=', ' ')
            elif '=' in line:
                linemode = 'set'
                line = line.replace('=', ' ')
            elif line.startswith('\\'):
                linemode = 'forbid'
                line = line.lstrip('\\').strip().replace('?', ' ')
            elif '?' in line:
                linemode = 'check'
                line = line.replace('?', ' ')
            else:
                raise LTCCompileError('LTC line has no known operators: ' + line)
            kws = LTCCompiler._combine_kws(line.strip().split())
            if linemode == 'set':
                try:
                    field = kws[0]
                    value = kws[1]
                    value = LTCCompiler._typevalue(value)
                    field_table[field] = value
                    if 'as' in kws:
                        allias = kws[kws.index('as') + 1]
                        namespace[allias] = value
                except IndexError:
                    raise LTCCompileError('Uncomplete operation: not enough keywords in ' + line)
            elif linemode == 'check':
                try:
                    field = kws[0]
                    function = LTCCompiler._build_func(kws[1])
                    
                    if not function._is_checker:
                        if LTC_CheckerShortcuts in LATEREM_FLAGS:
                            function = IsEqual(function)
                        else:
                            raise LTCCompileError(kws[1] + 'cannot be a Checker Function in: ' + line)
                    checker_functions.append((field, function))
                except IndexError:
                    raise LTCCompileError('Uncomplete operation: not enough keywords in ' + line)
            elif linemode == 'contain':
                allias = kws[0]
                value = kws[1]
                value = LTCCompiler._typevalue(value)
                namespace[allias] = value
            elif linemode == 'forbid':
                try:
                    field = kws[0]
                    function = LTCCompiler._build_func(kws[1])
                    
                    if not function._is_checker:
                        if LTC_CheckerShortcuts in LATEREM_FLAGS:
                            function = IsEqual(function)
                        else:
                            raise LTCCompileError(kws[1] + 'cannot be a Checker Function in: ' + line)
                    forbidden_cases.append((field, function))
                except IndexError:
                    raise LTCCompileError('Uncomplete operation: not enough keywords in ' + line)
            
        return LTC(field_table=field_table, 
                   namespace=namespace, 
                   checker_functions=checker_functions,
                   forbidden_cases=forbidden_cases)


    def compile_alt(self, txt):
        COMPILER_VERSION = 0.2
        if COMPILER_VERSION != VERSION:
            raise NotImplemented

        namespace = {}
        field_table = {}
        checker_functions = []
        code = txt.split('\n')
        for line in code:
            if '#' in line:
                line = line[:line.find('#')]
            line = line.strip()
            if not line:
                continue
            kws = LTCCompiler._combine_kws(line.strip().split())
            if kws[0] == 'set':
                try: 
                    if 'to' not in kws:
                        raise LTCCompileError('Uncomplete operation: expected "to" keyword in ' + line)
                    field = kws[1]
                    value = kws[kws.index('to') + 1]
                    value = LTCCompiler._typevalue(value)
                    field_table[field] = value
                    if 'as' in kws:
                        allias = kws[kws.index('as') + 1]
                        namespace[allias] = value
                except IndexError:
                    raise LTCCompileError('Uncomplete operation: not enough keywords in ' + line)
            elif kws[0] == 'check':
                try:
                    if 'for' not in kws:
                        raise LTCCompileError('Uncomplete operation: expected "for" keyword in ' + line)
                    field = kws[1]
                    checker_functions.append((field, LTCCompiler._build_func(kws[3])))
                except IndexError:
                    raise LTCCompileError('Uncomplete operation: not enough keywords in ' + line)
            elif kws[0] == 'contain':
                try: 
                    if 'as' not in kws:
                        raise LTCCompileError('Uncomplete operation: expected "as" keyword in ' + line)
                    allias = kws[1]
                    value = kws[kws.index('as') + 1]
                    value = LTCCompiler._typevalue(value)
                    namespace[allias] = value
                except IndexError:
                    raise LTCCompileError('Uncomplete operation: not enough keywords in ' + line)
            
            else:
                raise LTCCompileError('Unknown operation ' + kws[0])        

        return LTC(field_table=field_table, 
                   namespace=namespace, 
                   checker_functions=checker_functions)



if __name__ == '__main__':
    test = '''
a = Rand10(0, 10)
\\a?Equal(5)'''

    ltcc = LTCCompiler()
    
    for _ in range(1000):
        ltc = ltcc.compile(test)
        ltc.execute()
        print(ltc.field_table)

    raise   
    print(ltc.field_table)
    print(ltc.check({'input': '42'}))
    print(ltc.check({'input': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'}))
    print(ltc.to_dict())