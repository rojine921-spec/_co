import re
import sys
from pathlib import Path

TOKEN = re.compile(r'//[^\n]*|/\*.*?\*/|"[^"\n]*"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[{}()\[\].,;+\-*/&|<>=~]|\s+|.', re.S)
SEG = {'static':'static','field':'this','arg':'argument','var':'local'}
OPS = {'+':'add','-':'sub','*':'call Math.multiply 2','/':'call Math.divide 2','&':'and','|':'or','<':'lt','>':'gt','=':'eq'}

class Compiler:
    def __init__(self, source):
        self.tokens = [t for t in TOKEN.findall(source) if not t.isspace() and not t.startswith(('//','/*'))]
        self.i = 0
        self.code = []
        self.cls = {}
        self.sub = {}
        self.count = dict.fromkeys(SEG,0)
        self.serial = 0
    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None
    def take(self, expected=None):
        t = self.peek()
        if t is None or (expected is not None and t != expected):
            raise SyntaxError(f'Token {self.i}: expected {expected}, got {t}')
        self.i += 1
        return t
    def emit(self,*lines): self.code.extend(lines)
    def define(self,name,typ,kind):
        table = self.cls if kind in ('static','field') else self.sub
        if name in table: raise SyntaxError(f'Duplicate variable: {name}')
        table[name] = (typ,kind,self.count[kind]); self.count[kind] += 1
    def lookup(self,name):
        return self.sub.get(name,self.cls.get(name))
    def access(self,name,action='push'):
        item = self.lookup(name)
        if item is None: raise SyntaxError(f'Undefined variable: {name}')
        _,kind,index = item
        self.emit(f'{action} {SEG[kind]} {index}')
    def label(self):
        self.serial += 1
        return f'L{self.serial}'
    def declaration(self,kind):
        typ = self.take()
        self.define(self.take(),typ,kind)
        while self.peek() == ',':
            self.take(','); self.define(self.take(),typ,kind)
        self.take(';')
    def compile(self):
        self.take('class'); self.name = self.take(); self.take('{')
        while self.peek() in ('static','field'):
            self.declaration(self.take())
        while self.peek() in ('constructor','function','method'):
            self.subroutine()
        self.take('}')
        if self.peek() is not None: raise SyntaxError('Extra tokens after class')
        return '\n'.join(self.code)+'\n'
    def subroutine(self):
        kind = self.take(); self.take(); name = self.take()
        self.sub = {}; self.count['arg'] = self.count['var'] = 0
        if kind == 'method': self.define('this',self.name,'arg')
        self.take('(')
        if self.peek() != ')':
            while True:
                typ = self.take(); self.define(self.take(),typ,'arg')
                if self.peek() != ',': break
                self.take(',')
        self.take(')'); self.take('{')
        while self.peek() == 'var':
            self.take(); self.declaration('var')
        self.emit(f'function {self.name}.{name} {self.count["var"]}')
        if kind == 'constructor':
            self.emit(f'push constant {self.count["field"]}','call Memory.alloc 1','pop pointer 0')
        elif kind == 'method': self.emit('push argument 0','pop pointer 0')
        self.statements(); self.take('}')
    def statements(self):
        while self.peek() in ('let','if','while','do','return'):
            getattr(self,'stmt_'+self.take())()
    def stmt_let(self):
        name = self.take(); array = self.peek() == '['
        if array:
            self.access(name); self.take('['); self.expression(); self.take(']'); self.emit('add')
        self.take('='); self.expression(); self.take(';')
        if array: self.emit('pop temp 0','pop pointer 1','push temp 0','pop that 0')
        else: self.access(name,'pop')
    def stmt_if(self):
        yes,no,end = self.label(),self.label(),self.label()
        self.take('('); self.expression(); self.take(')')
        self.emit(f'if-goto {yes}',f'goto {no}',f'label {yes}')
        self.take('{'); self.statements(); self.take('}')
        if self.peek() == 'else':
            self.emit(f'goto {end}',f'label {no}'); self.take(); self.take('{'); self.statements(); self.take('}'); self.emit(f'label {end}')
        else: self.emit(f'label {no}')
    def stmt_while(self):
        start,body,end = self.label(),self.label(),self.label()
        self.emit(f'label {start}'); self.take('('); self.expression(); self.take(')')
        self.emit(f'if-goto {body}',f'goto {end}',f'label {body}')
        self.take('{'); self.statements(); self.take('}'); self.emit(f'goto {start}',f'label {end}')
    def stmt_do(self):
        self.call(self.take()); self.take(';'); self.emit('pop temp 0')
    def stmt_return(self):
        if self.peek() == ';': self.emit('push constant 0')
        else: self.expression()
        self.take(';'); self.emit('return')
    def expression(self):
        self.term()
        while self.peek() in OPS:
            op = self.take(); self.term(); self.emit(OPS[op])
    def term(self):
        t = self.take()
        if t.isdigit():
            if int(t)>32767: raise SyntaxError('Integer exceeds Jack range')
            self.emit(f'push constant {int(t)}')
        elif t.startswith('"') and t.endswith('"'):
            s = t[1:-1]; self.emit(f'push constant {len(s)}','call String.new 1')
            for c in s: self.emit(f'push constant {ord(c)}','call String.appendChar 2')
        elif t in ('true','false','null','this'):
            if t == 'this': self.emit('push pointer 0')
            else:
                self.emit('push constant 0')
                if t == 'true': self.emit('not')
        elif t in ('-','~'):
            self.term(); self.emit('neg' if t == '-' else 'not')
        elif t == '(':
            self.expression(); self.take(')')
        elif self.peek() == '[':
            self.access(t); self.take('['); self.expression(); self.take(']'); self.emit('add','pop pointer 1','push that 0')
        elif self.peek() in ('(','.'): self.call(t)
        else: self.access(t)
    def call(self,first):
        n = 0
        if self.peek() == '.':
            self.take('.'); name = self.take(); item = self.lookup(first)
            if item is not None:
                self.access(first); n = 1; target = item[0]+'.'+name
            else: target = first+'.'+name
        else:
            self.emit('push pointer 0'); n = 1; target = self.name+'.'+first
        self.take('(')
        if self.peek() != ')':
            while True:
                self.expression(); n += 1
                if self.peek() != ',': break
                self.take(',')
        self.take(')'); self.emit(f'call {target} {n}')

def main():
    if len(sys.argv) != 2: raise SystemExit('Usage: python JackCompiler.py <file.jack or folder>')
    path = Path(sys.argv[1])
    files = sorted(path.glob('*.jack')) if path.is_dir() else [path]
    if not files or any(not p.is_file() or p.suffix != '.jack' for p in files):
        raise SystemExit('No Jack source files found')
    for p in files:
        try: result = Compiler(p.read_text(encoding='utf-8-sig')).compile()
        except SyntaxError as e: raise SystemExit(f'{p}: {e}')
        out = p.with_suffix('.vm'); out.write_text(result,encoding='utf-8'); print(f'Compiled: {out}')

if __name__ == '__main__': main()
