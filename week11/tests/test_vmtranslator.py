"""Self-contained Hack assembler/CPU checks for VMTranslator.js.
Run: python tests/test_vmtranslator.py
"""
import pathlib
import subprocess
import tempfile
import unittest

PROJECT = pathlib.Path(__file__).resolve().parents[1]
JS = PROJECT / 'VMTranslator.js'
COMPS = {
    '0': '0101010', '1':'0111111', '-1':'0111010', 'D':'0001100',
    'A':'0110000', '!D':'0001101','!A':'0110001','-D':'0001111','-A':'0110011',
    'D+1':'0011111','A+1':'0110111','D-1':'0001110','A-1':'0110010',
    'D+A':'0000010','D-A':'0010011','A-D':'0000111','D&A':'0000000','D|A':'0010101',
    'M':'1110000','!M':'1110001','-M':'1110011','M+1':'1110111','M-1':'1110010',
    'D+M':'1000010','D-M':'1010011','M-D':'1000111','D&M':'1000000','D|M':'1010101'
}
PREDEFINED = {'SP':0,'LCL':1,'ARG':2,'THIS':3,'THAT':4,'SCREEN':16384,'KBD':24576,
              **{f'R{i}':i for i in range(16)}}


def assembler(asm):
    lines = [line.split('//')[0].strip() for line in asm.splitlines()]
    lines = [line for line in lines if line]
    labels = dict(PREDEFINED)
    rom = []
    for line in lines:
        if line.startswith('('):
            assert line.endswith(')'), line
            labels[line[1:-1]] = len(rom)
        else:
            rom.append(line)
    next_var = 16
    instructions = []
    for line in rom:
        if line.startswith('@'):
            symbol = line[1:]
            if symbol.isdecimal():
                value = int(symbol)
            else:
                if symbol not in labels:
                    labels[symbol] = next_var
                    next_var += 1
                value = labels[symbol]
            assert 0 <= value <= 32767, line
            instructions.append(value)
        else:
            dest, sep, tail = line.partition('=')
            if not sep:
                dest, tail = '', dest
            comp, sep, jump = tail.partition(';')
            assert comp in COMPS, f'Unsupported Hack computation: {line}'
            assert all(c in 'ADM' for c in dest), line
            assert jump in ('','JGT','JEQ','JGE','JLT','JNE','JLE','JMP'), line
            d = sum(1 << {'M':0, 'D':1, 'A':2}[c] for c in dest)
            j = {'':0,'JGT':1,'JEQ':2,'JGE':3,'JLT':4,'JNE':5,'JLE':6,'JMP':7}[jump]
            instructions.append(0xe000 | (int(COMPS[comp],2) << 6) | (d << 3) | j)
    return instructions


def signed(v):
    return v if v < 32768 else v - 65536


def cpu_run(rom, cycles=12000, initial=None):
    ram = [0]*32768
    ram[0] = 256
    if initial:
        for address, value in initial.items():
            ram[address] = value & 0xffff
    a = d = pc = 0
    for _ in range(cycles):
        if not (0 <= pc < len(rom)):
            break
        instr = rom[pc]
        if instr < 32768:
            a = instr
            pc += 1
            continue
        comp = (instr >> 6) & 127
        dest = (instr >> 3) & 7
        jump = instr & 7
        m = ram[a & 32767]
        # Using a direct reference evaluator avoids independent Hack ALU implementation bugs.
        values = {
            0b0101010:0, 0b0111111:1, 0b0111010:-1,
            0b0001100:d, 0b0110000:a, 0b1110000:m,
            0b0001101:~d,0b0110001:~a,0b1110001:~m,
            0b0001111:-d,0b0110011:-a,0b1110011:-m,
            0b0011111:d+1,0b0110111:a+1,0b1110111:m+1,
            0b0001110:d-1,0b0110010:a-1,0b1110010:m-1,
            0b0000010:d+a,0b1000010:d+m,
            0b0010011:d-a,0b1010011:d-m,
            0b0000111:a-d,0b1000111:m-d,
            0b0000000:d&a,0b1000000:d&m,
            0b0010101:d|a,0b1010101:d|m,
        }
        v = values[comp] & 0xffff
        old_a = a
        if dest & 1: ram[old_a & 32767] = v
        if dest & 2: d = v
        if dest & 4: a = v
        sv = signed(v)
        jumps = [False, sv>0, sv==0, sv>=0, sv<0, sv!=0, sv<=0, True]
        pc = (old_a & 32767) if jumps[jump] else pc+1
    return ram


class VMTranslatorTest(unittest.TestCase):
    def translate(self, text, initial=None, cycles=4000):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp)/'Test.vm'
            source.write_text(text, encoding='utf8')
            subprocess.run(['node',str(JS),str(source)], capture_output=True, check=True)
            asm = source.with_suffix('.asm').read_text(encoding='utf8')
            return cpu_run(assembler(asm), cycles, initial)

    def test_add(self):
        ram = self.translate('push constant 7\npush constant 8\nadd')
        self.assertEqual(ram[0], 257)
        self.assertEqual(ram[256], 15)

    def test_math_and_logic(self):
        cases = [
            ('push constant 7\npush constant 4\nsub', 3),
            ('push constant 2\nneg', -2),
            ('push constant 7\npush constant 3\nand', 3),
            ('push constant 7\npush constant 8\nor', 15),
            ('push constant 0\nnot', -1),
            ('push constant 42\npush constant 42\neq', -1),
            ('push constant 42\npush constant 5\neq', 0),
            ('push constant 5\npush constant 42\nlt', -1),
            ('push constant 5\npush constant 42\ngt', 0),
            ('push constant 32767\npush constant 1\nneg\ngt', -1),
            ('push constant 1\nneg\npush constant 32767\nlt', -1),
            ('push constant 1\nneg\npush constant 32767\ngt', 0),
            ('push constant 32767\npush constant 1\nneg\nlt', 0),
        ]
        for src, expected in cases:
            with self.subTest(src=src):
                ram = self.translate(src)
                self.assertEqual(signed(ram[256]), expected)
                self.assertEqual(ram[0], 257)

    def test_memory_segments(self):
        src = '''
            push constant 23
            pop local 2
            push local 2
            pop argument 1
            push argument 1
            pop this 3
            push this 3
            pop that 0
            push that 0
            pop temp 6
            push temp 6
            pop pointer 0
            push pointer 0
            pop static 3
            push static 3
        '''
        ram = self.translate(src, {1:300,2:310,3:320,4:330})
        self.assertEqual(ram[302],23)
        self.assertEqual(ram[311],23)
        self.assertEqual(ram[323],23)
        self.assertEqual(ram[330],23)
        self.assertEqual(ram[11],23)
        self.assertEqual(ram[3],23)
        self.assertEqual(ram[256],23)

    def test_branching(self):
        src = '''
            push constant 3
            label LOOP
            push constant 1
            sub
            pop temp 0
            push temp 0
            push constant 0
            eq
            if-goto END
            push temp 0
            goto LOOP
            label END
        '''
        ram = self.translate(src, cycles=900)
        self.assertEqual(ram[5], 0)
        self.assertEqual(ram[0], 256)

    def test_function_call_and_return(self):
        source = PROJECT / 'examples' / 'SysDemo' / 'SysDemo.asm'
        ram = cpu_run(assembler(source.read_text(encoding='utf8')), cycles=5000)
        self.assertEqual(ram[0], 262)
        self.assertEqual(ram[261], 246)
        self.assertEqual(ram[1], 261)  # caller LCL restored by return

    def test_nested_calls_and_local_vars(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = pathlib.Path(temp) / 'Nested'
            folder.mkdir()
            (folder/'Sys.vm').write_text("""function Sys.init 0
push constant 5
call A.addTwo 1
pop temp 0
label END
goto END
""", encoding='utf8')
            (folder/'A.vm').write_text("""function A.addTwo 2
push argument 0
pop local 0
push local 0
call B.inc 1
push constant 1
add
return
""", encoding='utf8')
            (folder/'B.vm').write_text("""function B.inc 0
push argument 0
push constant 1
add
return
""", encoding='utf8')
            subprocess.run(['node',str(JS),str(folder)], capture_output=True, check=True)
            ram = cpu_run(assembler((folder/'Nested.asm').read_text()), cycles=6000)
            self.assertEqual(ram[5],7)
            self.assertEqual(ram[0],261)

    def test_static_separate_files(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = pathlib.Path(temp) / 'Statics'
            folder.mkdir()
            (folder/'Sys.vm').write_text("""function Sys.init 0
call A.set 0
pop temp 7
call B.set 0
pop temp 7
call A.get 0
pop temp 0
call B.get 0
pop temp 1
label END
goto END
""", encoding='utf8')
            (folder/'A.vm').write_text("""function A.set 0
push constant 11
pop static 0
push constant 0
return
function A.get 0
push static 0
return
""", encoding='utf8')
            (folder/'B.vm').write_text("""function B.set 0
push constant 22
pop static 0
push constant 0
return
function B.get 0
push static 0
return
""", encoding='utf8')
            subprocess.run(['node',str(JS),str(folder)], capture_output=True, check=True)
            ram = cpu_run(assembler((folder/'Statics.asm').read_text()), cycles=14000)
            self.assertEqual(ram[5],11)
            self.assertEqual(ram[6],22)

    def test_bad_command(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp)/'Bad.vm'
            source.write_text('pop pointer 2', encoding='utf8')
            proc = subprocess.run(['node',str(JS),str(source)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode,0)
            self.assertIn('pointer index',proc.stderr)

if __name__ == '__main__':
    unittest.main(verbosity=2)
