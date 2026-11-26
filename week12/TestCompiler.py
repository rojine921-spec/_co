from pathlib import Path
import sys
from JackCompiler import Compiler

root = Path(sys.argv[1] if len(sys.argv)>1 else '11')
files = sorted(root.rglob('*.jack'))
if not files:
    raise SystemExit(f'No .jack files found in {root}')
passed = 0
for p in files:
    try:
        code = Compiler(p.read_text(encoding='utf-8-sig')).compile()
        p.with_suffix('.vm').write_text(code, encoding='utf-8')
        print(f'PASS: {p} (compiled)')
        passed += 1
    except Exception as e:
        print(f'FAIL: {p}: {e}')
print(f'Compilation: {passed}/{len(files)} passed')
print('Runtime correctness must be checked in VM Emulator.')
raise SystemExit(passed != len(files))
