import re
import sys
from argparse import ArgumentParser
 
VERSION = "1.0"
MAX_DEPTH = 19  # batas nesting, sama seperti test suite json.org (fail18)
 
 
class JSONError(Exception):
    """Error JSON, membawa posisi karakter supaya pesan bisa menunjuk lokasi."""
 
    def __init__(self, message, pos):
        super().__init__(message)
        self.message = message
        self.pos = pos
 
 
# ---------------------------------------------------------------- LEXER
PUNCTUATION = {
    "{": "LBRACE", "}": "RBRACE",
    "[": "LBRACKET", "]": "RBRACKET",
    ":": "COLON", ",": "COMMA",
}
LITERALS = {"true": True, "false": False, "null": None}
ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b",
           "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
HEX_DIGITS = set("0123456789abcdefABCDEF")
DIGITS = "0123456789"
NUMBER_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
 
 
def read_string(text, start):
    """Baca string yang diawali '"' di posisi start. Return (isi, posisi_akhir)."""
    i = start + 1
    chars = []
    while i < len(text):
        ch = text[i]
        if ch == '"':
            return "".join(chars), i + 1
        if ch == "\\":
            i += 1
            if i >= len(text):
                break
            esc = text[i]
            if esc in ESCAPES:
                chars.append(ESCAPES[esc])
                i += 1
            elif esc == "u":
                digits = text[i + 1:i + 5]
                if len(digits) != 4 or any(c not in HEX_DIGITS for c in digits):
                    raise JSONError("Escape \\u harus diikuti 4 digit hex", i - 1)
                chars.append(chr(int(digits, 16)))
                i += 5
            else:
                raise JSONError(f"Escape tidak valid '\\{esc}'", i - 1)
        elif ord(ch) < 0x20:
            raise JSONError("Karakter kontrol (tab/newline) tidak boleh "
                            "ada langsung di dalam string", i)
        else:
            chars.append(ch)
            i += 1
    raise JSONError("String tidak ditutup dengan tanda kutip ganda", start)
 
 
def tokenize(text):
    """Pecah teks menjadi token: (jenis, nilai, posisi)."""
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in " \t\n\r":
            i += 1
        elif ch in PUNCTUATION:
            tokens.append((PUNCTUATION[ch], ch, i))
            i += 1
        elif ch == '"':
            value, end = read_string(text, i)
            tokens.append(("STRING", value, i))
            i = end
        elif ch == "-" or ch in DIGITS:
            match = NUMBER_RE.match(text, i)
            if not match:
                raise JSONError("Angka tidak valid", i)
            raw = match.group()
            is_float = any(c in raw for c in ".eE")
            tokens.append(("NUMBER", float(raw) if is_float else int(raw), i))
            i = match.end()
        else:
            for word, value in LITERALS.items():
                if text.startswith(word, i):
                    tokens.append(("LITERAL", value, i))
                    i += len(word)
                    break
            else:
                raise JSONError(f"Karakter tidak dikenal '{ch}'", i)
    return tokens
 
 
# --------------------------------------------------------------- PARSER
class Parser:
    """Recursive descent parser: satu fungsi untuk tiap bentuk JSON."""
 
    def __init__(self, tokens, text_length):
        self.tokens = tokens
        self.i = 0
        self.end = text_length
 
    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None
 
    def next(self):
        token = self.peek()
        if token is None:
            raise JSONError("Data berakhir terlalu cepat (ada yang belum ditutup)",
                            self.end)
        self.i += 1
        return token
 
    def parse(self):
        first = self.peek()
        if first is None:
            raise JSONError("Input kosong", 0)
        if first[0] not in ("LBRACE", "LBRACKET"):
            raise JSONError("JSON harus diawali '{' atau '['", first[2])
        value = self.parse_value(1)
        extra = self.peek()
        if extra is not None:
            raise JSONError("Ada sisa data setelah JSON selesai", extra[2])
        return value
 
    def parse_value(self, depth):
        kind, value, pos = self.next()
        if kind == "LBRACE":
            return self.parse_object(depth, pos)
        if kind == "LBRACKET":
            return self.parse_array(depth, pos)
        if kind in ("STRING", "NUMBER", "LITERAL"):
            return value
        raise JSONError(f"Token tidak terduga '{value}'", pos)
 
    def parse_object(self, depth, pos):
        if depth > MAX_DEPTH:
            raise JSONError(f"Nesting terlalu dalam (maksimal {MAX_DEPTH})", pos)
        result = {}
        nxt = self.peek()
        if nxt is not None and nxt[0] == "RBRACE":
            self.i += 1
            return result
        while True:
            kind, key, kpos = self.next()
            if kind == "RBRACE":
                raise JSONError("Koma berlebih sebelum '}'", kpos)
            if kind != "STRING":
                raise JSONError("Key object harus string dengan tanda kutip ganda",
                                kpos)
            kind, value, cpos = self.next()
            if kind != "COLON":
                raise JSONError("Setelah key harus ada ':'", cpos)
            result[key] = self.parse_value(depth + 1)
            kind, value, spos = self.next()
            if kind == "RBRACE":
                return result
            if kind != "COMMA":
                raise JSONError("Diharapkan ',' atau '}'", spos)
 
    def parse_array(self, depth, pos):
        if depth > MAX_DEPTH:
            raise JSONError(f"Nesting terlalu dalam (maksimal {MAX_DEPTH})", pos)
        result = []
        nxt = self.peek()
        if nxt is not None and nxt[0] == "RBRACKET":
            self.i += 1
            return result
        while True:
            nxt = self.peek()
            if nxt is not None and nxt[0] == "RBRACKET":
                raise JSONError("Koma berlebih sebelum ']'", nxt[2])
            result.append(self.parse_value(depth + 1))
            kind, value, spos = self.next()
            if kind == "RBRACKET":
                return result
            if kind != "COMMA":
                raise JSONError("Diharapkan ',' atau ']'", spos)
 
 
# ------------------------------------------------------------ PEMBUNGKUS
def line_and_column(text, pos):
    line = text.count("\n", 0, pos) + 1
    column = pos - (text.rfind("\n", 0, pos) + 1) + 1
    return line, column
 
 
def check(text):
    """Periksa teks JSON. Return (kode_keluar, pesan)."""
    try:
        Parser(tokenize(text), len(text)).parse()
    except JSONError as err:
        line, col = line_and_column(text, err.pos)
        return 1, f"JSON tidak valid: {err.message} (baris {line}, kolom {col})"
    return 0, "JSON valid"
 
 
def read_input(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
 
 
def main():
    cli = ArgumentParser(description="Validasi format JSON.")
    cli.add_argument("file", nargs="?", default="-",
                     help="File yang diperiksa (kosong atau '-' = baca dari STDIN).")
    cli.add_argument("-v", "--version", action="store_true",
                     help="Tampilkan versi program.")
    args = cli.parse_args()
 
    if args.version:
        print(f"json_parser versi {VERSION}")
        sys.exit(0)
 
    try:
        text = read_input(args.file)
    except OSError as err:
        print(f"Tidak bisa membaca file: {err}")
        sys.exit(1)
    except UnicodeDecodeError:
        print("JSON tidak valid: file bukan teks UTF-8")
        sys.exit(1)
 
    code, message = check(text)
    print(message)
    sys.exit(code)
 
 
if __name__ == "__main__":
    main()