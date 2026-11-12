"""nand2tetris Project 6: Hack assembler (Python 3).

Usage: python assembler.py path/to/Prog.asm
Output: path/to/Prog.hack
"""

from pathlib import Path
import re
import sys

# C-instruction comp bits: a c1 c2 c3 c4 c5 c6
COMP = {
    "0": "0101010", "1": "0111111", "-1": "0111010",
    "D": "0001100", "A": "0110000", "M": "1110000",
    "!D": "0001101", "!A": "0110001", "!M": "1110001",
    "-D": "0001111", "-A": "0110011", "-M": "1110011",
    "D+1": "0011111", "A+1": "0110111", "M+1": "1110111",
    "D-1": "0001110", "A-1": "0110010", "M-1": "1110010",
    "D+A": "0000010", "D+M": "1000010",
    "D-A": "0010011", "D-M": "1010011",
    "A-D": "0000111", "M-D": "1000111",
    "D&A": "0000000", "D&M": "1000000",
    "D|A": "0010101", "D|M": "1010101",
}

JUMP = {
    "": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111",
}

SYMBOL_PATTERN = re.compile(r"[A-Za-z_.$:][A-Za-z0-9_.$:]*\Z")


def predefined_symbols():
    table = {
        "SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
        "SCREEN": 16384, "KBD": 24576,
    }
    table.update({f"R{i}": i for i in range(16)})
    return table


def clean_lines(text):
    """Remove comments, whitespace and blank lines."""
    lines = []
    for line_no, original in enumerate(text.splitlines(), start=1):
        code = original.split("//", 1)[0]
        code = "".join(code.split())  # allow spaces in e.g. D = M + 1
        if code:
            lines.append((line_no, code))
    return lines


def first_pass(lines, symbols):
    """Record label (ROM) addresses, ignoring labels in instruction count."""
    instructions = []
    rom_address = 0
    for line_no, line in lines:
        if line.startswith("("):
            if not line.endswith(")"):
                raise ValueError(f"Line {line_no}: invalid label: {line}")
            label = line[1:-1]
            if not SYMBOL_PATTERN.fullmatch(label):
                raise ValueError(f"Line {line_no}: invalid label: {label}")
            if label in symbols:
                raise ValueError(f"Line {line_no}: duplicate or reserved label: {label}")
            symbols[label] = rom_address
        else:
            instructions.append((line_no, line))
            rom_address += 1
    return instructions


def encode_dest(dest, line_no):
    """Bits d1 d2 d3 correspond to registers A, D, M."""
    if len(dest) > 3 or len(set(dest)) != len(dest) or any(c not in "ADM" for c in dest):
        raise ValueError(f"Line {line_no}: invalid dest: {dest}")
    return "".join("1" if c in dest else "0" for c in "ADM")


def encode_c_instruction(line, line_no):
    if line.count("=") > 1 or line.count(";") > 1:
        raise ValueError(f"Line {line_no}: invalid C-instruction: {line}")
    if "=" in line:
        dest, rest = line.split("=", 1)
        if not dest:
            raise ValueError(f"Line {line_no}: missing destination")
    else:
        dest, rest = "", line
    if ";" in rest:
        comp, jump = rest.split(";", 1)
        if not jump:
            raise ValueError(f"Line {line_no}: missing jump")
    else:
        comp, jump = rest, ""
    if comp not in COMP:
        raise ValueError(f"Line {line_no}: invalid comp: {comp}")
    if jump not in JUMP:
        raise ValueError(f"Line {line_no}: invalid jump: {jump}")
    return "111" + COMP[comp] + encode_dest(dest, line_no) + JUMP[jump]


def assemble(source):
    symbols = predefined_symbols()
    instructions = first_pass(clean_lines(source), symbols)
    next_ram_address = 16
    output = []

    for line_no, line in instructions:
        if line.startswith("@"):
            value = line[1:]
            if not value:
                raise ValueError(f"Line {line_no}: missing A-instruction value")
            if value.isdecimal():
                address = int(value)
            else:
                if not SYMBOL_PATTERN.fullmatch(value):
                    raise ValueError(f"Line {line_no}: invalid symbol: {value}")
                if value not in symbols:
                    symbols[value] = next_ram_address
                    next_ram_address += 1
                address = symbols[value]
            if not 0 <= address <= 32767:
                raise ValueError(f"Line {line_no}: A-instruction address out of range: {address}")
            output.append(f"{address:016b}")
        else:
            output.append(encode_c_instruction(line, line_no))

    return "\n".join(output) + ("\n" if output else "")


def main():
    if len(sys.argv) != 2:
        print("Usage: python assembler.py <file.asm>")
        return 1

    source_path = Path(sys.argv[1])
    if source_path.suffix.lower() != ".asm":
        print("Error: input must be a .asm file", file=sys.stderr)
        return 1
    try:
        result = assemble(source_path.read_text(encoding="utf-8-sig"))
        destination = source_path.with_suffix(".hack")
        destination.write_text(result, encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Successfully assembled: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
