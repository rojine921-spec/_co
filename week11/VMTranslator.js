#!/usr/bin/env node
'use strict';

// nand2tetris Project 7 + 8: VM language -> Hack assembly
// Usage: node VMTranslator.js Input.vm
//        node VMTranslator.js FolderWithVmFiles
const fs = require('fs');
const path = require('path');

const ARITHMETIC = new Set(['add', 'sub', 'neg', 'eq', 'gt', 'lt', 'and', 'or', 'not']);
const SEGMENTS = new Set(['constant', 'local', 'argument', 'this', 'that', 'temp', 'pointer', 'static']);
const BASES = { local: 'LCL', argument: 'ARG', this: 'THIS', that: 'THAT' };
const SYMBOL = /^[A-Za-z_.$:][A-Za-z0-9_.$:]*$/;

function parseFile(filename) {
  const commands = [];
  const lines = fs.readFileSync(filename, 'utf8').split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const source = lines[i].split('//')[0].trim();
    if (!source) continue;
    const args = source.split(/\s+/);
    const [op, a, b] = args;
    const fail = message => { throw new Error(`${filename}:${i + 1}: ${message}: ${source}`); };
    if (ARITHMETIC.has(op) || op === 'return') {
      if (args.length !== 1) fail('Expected one word');
    } else if (op === 'push' || op === 'pop') {
      if (args.length !== 3 || !SEGMENTS.has(a) || !/^\d+$/.test(b)) fail('Invalid memory command');
      const index = Number(b);
      if (!Number.isSafeInteger(index) || index > 32767) fail('Index outside Hack A-instruction range');
      if (op === 'pop' && a === 'constant') fail('Cannot pop to constant');
      if (a === 'pointer' && index > 1) fail('pointer index must be 0 or 1');
      if (a === 'temp' && index > 7) fail('temp index must be 0 through 7');
    } else if (op === 'label' || op === 'goto' || op === 'if-goto') {
      if (args.length !== 2 || !SYMBOL.test(a)) fail('Invalid label');
    } else if (op === 'function' || op === 'call') {
      if (args.length !== 3 || !SYMBOL.test(a) || !/^\d+$/.test(b)) fail('Invalid function command');
      if (!Number.isSafeInteger(Number(b)) || Number(b) > 32767) fail('Count outside Hack A-instruction range');
    } else {
      fail('Unknown VM instruction');
    }
    commands.push({ op, a, b: b === undefined ? undefined : Number(b) });
  }
  return commands;
}

class CodeWriter {
  constructor() {
    this.asm = [];
    this.counter = 0;
    this.filename = '';
    this.currentFunction = '';
  }
  emit(...lines) { this.asm.push(...lines); }
  pushD() { this.emit('@SP', 'A=M', 'M=D', '@SP', 'M=M+1'); }
  popToD() { this.emit('@SP', 'AM=M-1', 'D=M'); }
  unique(tag) { return `$VM.${tag}.${this.counter++}`; }
  setFile(filename) {
    this.filename = path.basename(filename, '.vm').replace(/[^A-Za-z0-9_.$:]/g, '_');
    if (!/^[A-Za-z_.$:]/.test(this.filename)) this.filename = '_' + this.filename;
    this.currentFunction = '';
  }
  scoped(label) { return this.currentFunction ? `${this.currentFunction}$${label}` : label; }

  // Signs are handled before subtraction, preventing signed overflow in gt/lt.
  compare(op) {
    const yes = this.unique('TRUE');
    const no = this.unique('FALSE');
    const end = this.unique('END');
    if (op === 'eq') {
      this.emit('@SP', 'AM=M-1', 'D=M', 'A=A-1', 'D=M-D', `@${yes}`, 'D;JEQ', `@${no}`, '0;JMP');
    } else {
      const xneg = this.unique('XNEG');
      const both = this.unique('SAME_SIGN');
      this.popToD();
      this.emit('@R13', 'M=D', '@SP', 'A=M-1', 'D=M', '@R14', 'M=D'); // y and x
      this.emit('@R14', 'D=M', `@${xneg}`, 'D;JLT');
      // x >= 0: if y < 0, x > y; otherwise subtract.
      this.emit('@R13', 'D=M', `@${op === 'gt' ? yes : no}`, 'D;JLT', `@${both}`, '0;JMP');
      this.emit(`(${xneg})`, '@R13', 'D=M', `@${op === 'gt' ? no : yes}`, 'D;JGE');
      this.emit(`(${both})`, '@R14', 'D=M', '@R13', 'D=D-M', `@${yes}`, `D;${op === 'gt' ? 'JGT' : 'JLT'}`, `@${no}`, '0;JMP');
    }
    this.emit(`(${yes})`, '@SP', 'A=M-1', 'M=-1', `@${end}`, '0;JMP', `(${no})`, '@SP', 'A=M-1', 'M=0', `(${end})`);
  }

  arithmetic(op) {
    if (op === 'neg' || op === 'not') {
      this.emit('@SP', 'A=M-1', `M=${op === 'neg' ? '-M' : '!M'}`);
    } else if (op === 'eq' || op === 'gt' || op === 'lt') {
      this.compare(op);
    } else {
      this.popToD();
      const comp = { add: 'D+M', sub: 'M-D', and: 'D&M', or: 'D|M' }[op];
      this.emit('A=A-1', `M=${comp}`);
    }
  }

  memory(op, segment, index) {
    const push = op === 'push';
    if (segment === 'constant') {
      this.emit(`@${index}`, 'D=A');
      this.pushD();
    } else if (segment in BASES) {
      const base = BASES[segment];
      this.emit(`@${index}`, 'D=A', `@${base}`);
      if (push) {
        this.emit('A=D+M', 'D=M');
        this.pushD();
      } else {
        this.emit('D=D+M', '@R13', 'M=D');
        this.popToD();
        this.emit('@R13', 'A=M', 'M=D');
      }
    } else {
      const name = segment === 'static' ? `${this.filename}.${index}`
        : segment === 'pointer' ? (index === 0 ? 'THIS' : 'THAT')
        : String(5 + index); // temp R5..R12
      if (push) {
        this.emit(`@${name}`, 'D=M');
        this.pushD();
      } else {
        this.popToD();
        this.emit(`@${name}`, 'M=D');
      }
    }
  }

  writeCall(name, nArgs) {
    const returnLabel = this.unique('RET');
    this.emit(`@${returnLabel}`, 'D=A');
    this.pushD();
    for (const reg of ['LCL', 'ARG', 'THIS', 'THAT']) {
      this.emit(`@${reg}`, 'D=M');
      this.pushD();
    }
    this.emit('@SP', 'D=M', '@5', 'D=D-A', `@${nArgs}`, 'D=D-A', '@ARG', 'M=D');
    this.emit('@SP', 'D=M', '@LCL', 'M=D', `@${name}`, '0;JMP', `(${returnLabel})`);
  }

  writeReturn() {
    // FRAME=R13=LCL, RET=R14=*(FRAME-5).
    this.emit('@LCL', 'D=M', '@R13', 'M=D', '@5', 'A=D-A', 'D=M', '@R14', 'M=D');
    this.popToD();
    this.emit('@ARG', 'A=M', 'M=D'); // *ARG = return value
    this.emit('@ARG', 'D=M+1', '@SP', 'M=D'); // SP = ARG+1
    for (const reg of ['THAT', 'THIS', 'ARG', 'LCL']) {
      this.emit('@R13', 'AM=M-1', 'D=M', `@${reg}`, 'M=D');
    }
    this.emit('@R14', 'A=M', '0;JMP');
  }

  write(cmd) {
    const { op, a, b } = cmd;
    if (ARITHMETIC.has(op)) this.arithmetic(op);
    else if (op === 'push' || op === 'pop') this.memory(op, a, b);
    else if (op === 'label') this.emit(`(${this.scoped(a)})`);
    else if (op === 'goto') this.emit(`@${this.scoped(a)}`, '0;JMP');
    else if (op === 'if-goto') { this.popToD(); this.emit(`@${this.scoped(a)}`, 'D;JNE'); }
    else if (op === 'function') {
      this.currentFunction = a;
      this.emit(`(${a})`);
      for (let i = 0; i < b; i++) { this.emit('@0', 'D=A'); this.pushD(); }
    } else if (op === 'call') this.writeCall(a, b);
    else if (op === 'return') this.writeReturn();
  }

  bootstrap(withSysInit) {
    this.emit('@256', 'D=A', '@SP', 'M=D');
    if (withSysInit) this.writeCall('Sys.init', 0);
  }
}

function translate(inputPath, bootstrapMode = 'auto') {
  const input = path.resolve(inputPath);
  if (!fs.existsSync(input)) throw new Error(`Input does not exist: ${input}`);
  const isDir = fs.statSync(input).isDirectory();
  const files = isDir ? fs.readdirSync(input).filter(f => f.endsWith('.vm')).sort().map(f => path.join(input, f)) : [input];
  if (!files.length || files.some(f => path.extname(f).toLowerCase() !== '.vm')) throw new Error('Provide a .vm file or a folder containing .vm files');
  const sources = files.map(file => ({ file, commands: parseFile(file) }));
  const hasSysInit = sources.some(s => s.commands.some(c => c.op === 'function' && c.a === 'Sys.init'));
  if (bootstrapMode === 'yes' && !hasSysInit) throw new Error('Bootstrap requested, but Sys.init function was not found');
  const writer = new CodeWriter();
  if (bootstrapMode === 'yes' || (bootstrapMode === 'auto' && (isDir || hasSysInit))) {
    writer.bootstrap(hasSysInit);
  }
  for (const { file, commands } of sources) {
    writer.setFile(file);
    for (const command of commands) writer.write(command);
  }
  const output = isDir ? path.join(input, `${path.basename(input)}.asm`) : input.replace(/\.vm$/i, '.asm');
  fs.writeFileSync(output, writer.asm.join('\n') + '\n', 'utf8');
  return { output, files: files.length, instructions: sources.reduce((n,s) => n + s.commands.length, 0) };
}

if (require.main === module) {
  const args = process.argv.slice(2);
  const modeFlag = args.find(a => a.startsWith('--'));
  const input = args.find(a => !a.startsWith('--'));
  if (!input || args.length > 2 || (modeFlag && !['--bootstrap', '--no-bootstrap'].includes(modeFlag))) {
    console.error('Usage: node VMTranslator.js <file.vm|directory> [--bootstrap|--no-bootstrap]');
    process.exit(1);
  }
  try {
    const result = translate(input, modeFlag === '--bootstrap' ? 'yes' : modeFlag === '--no-bootstrap' ? 'no' : 'auto');
    console.log(`OK: ${result.files} VM file(s), ${result.instructions} commands -> ${result.output}`);
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

module.exports = { translate, parseFile, CodeWriter };
