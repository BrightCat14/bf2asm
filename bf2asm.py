import json
import os
import sys
import traceback
from pathlib import Path

import colorama
from colorama import Fore

import locale

colorama.init()

name = "bf2asm"
short_name = "b2a"

def error_print(s):
    print(f"{Fore.RED}{s}{Fore.RESET}")

def success_print(s):
    print(f"{Fore.GREEN}{s}{Fore.RESET}")

def warning_print(s):
    print(f"{Fore.YELLOW}{s}{Fore.RESET}")

def err_hook(exc_type, exc_value, exc_traceback):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    error_print(tb)
sys.excepthook = err_hook

class BFSyntaxError(Exception):
    pass

# multi-backends
BACKENDS = {
    ("x86_64", "linux"): {
        "ptr_init": "mov rsi, tape",
        "inc_ptr": "inc rsi",
        "dec_ptr": "dec rsi",
        "inc_val": "inc byte [rsi]",
        "dec_val": "dec byte [rsi]",
        "output": """mov rax, 1
mov rdi, 1
mov rdx, 1
mov rsi, rsi
syscall""",
        "input": """mov rax, 0
mov rdi, 0
mov rdx, 1
mov rsi, rsi
syscall""",
        "exit": "mov rax, 60\nxor rdi,rdi\nsyscall",
        "header": "section .bss\n    tape resb 30000\nsection .text\nglobal _start\n_start:",
        "cmp_byte_for_loop": "cmp byte [rsi], 0"
    },
    ("arm64", "linux"): {
        "ptr_init": "adr x19, tape",
        "inc_ptr": "add x19, x19, #1",
        "dec_ptr": "sub x19, x19, #1",
        "inc_val": "ldrb w0, [x19]\nadd w0, w0, #1\nstrb w0, [x19]",
        "dec_val": "ldrb w0, [x19]\nsub w0, w0, #1\nstrb w0, [x19]",
        "output": """mov x0, #1
mov x2, #1
mov x1, x19
mov x8, #64
svc 0""",
        "input": """mov x0, #0
mov x2, #1
mov x1, x19
mov x8, #63
svc 0""",
        "exit": "mov x8, #93\nmov x0, #0\nsvc 0",
        "header": ".bss\n    tape: .space 30000\n.text\nglobal _start\n_start:",
        "cmp_byte_for_loop": "cmp byte [rsi], 0"
    },
    ("x86_64", "windows"): {
        "ptr_init": "mov rsi, tape",
        "inc_ptr": "inc rsi",
        "dec_ptr": "dec rsi",
        "inc_val": "inc byte [rsi]",
        "dec_val": "dec byte [rsi]",
        "output": """movzx rdx, byte [rsi]
    lea rcx, [rel fmt]   
    xor rax, rax           
    call printf""",
        "input": """call getchar
    mov [rsi], al""",
        "exit": "ret",
        "header": """section .data
    fmt db "%c",0

    section .bss
    tape resb 30000

    section .text
    global main
    extern printf, getchar
    main:
        mov rsi, tape""",
        "cmp_byte_for_loop": "cmp byte [rsi], 0"
    }
}


def main():
    locale.init()

    # load extra backends from backends.json if exists
    json_path = os.path.join(Path.home(), name, "backends.json")
    if os.path.exists(json_path):
        with open(json_path) as f:
            extra = json.load(f)
        for k, v in extra.items():
            arch, os_name = k.split("_", 1)
            BACKENDS[(arch, os_name)] = v

    if len(sys.argv) < 2:
        warning_print(f"{locale.usage}: python bf2asm.py <arch> <os> <input.b> <output.asm> {locale.or_keyword} settings lang <locale>")
        sys.exit(1)

    if sys.argv[1] == "settings" and len(sys.argv) >= 4 and sys.argv[2] == "lang":
        lang_code = sys.argv[3]
        success_print(f"{locale.changing_lang_to} {lang_code}")
        locale.change_language(lang_code)
        sys.exit(0)

    if len(sys.argv) < 5:
        warning_print(f"{locale.usage}: python {sys.argv[0]} <arch> <os> <input.b> <output.asm>")
        sys.exit(1)

    arch, os_name, bf_file, output_file = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

    backend = BACKENDS.get((arch, os_name))
    if not backend:
        error_print(locale.backend_not_implemented.format(arch=arch, os_name=os_name))
        sys.exit(1)

    # determine cache path
    b2a_tmp = os.getenv(f"{short_name.upper()}_TMP")
    if b2a_tmp is None:
        if os.name == "nt":
            temp_dir = os.getenv("TEMP", ".")
        else:
            temp_dir = "/tmp"
    else:
        temp_dir = b2a_tmp

    if not temp_dir == b2a_tmp:
        named_tmp = os.path.join(temp_dir, name)
    else:
        named_tmp = temp_dir
    if not os.path.exists(named_tmp):
        os.mkdir(named_tmp)

    cache_file = os.path.join(named_tmp, os.path.basename(bf_file) + f"-{os_name}_{arch}.b_cache.json")
    cache = {}

    if os.path.exists(cache_file):
        with open(cache_file) as f:
            cache = json.load(f)

    # read bf code
    with open(bf_file) as f:
        bf_code = f.read()

    # validate bracket balance
    balance = 0
    for c in bf_code:
        if c == '[':
            balance += 1
        elif c == ']':
            balance -= 1
        if balance < 0:
            raise BFSyntaxError(locale.unmatched_brackets.format(bracket="']'"))
    if balance > 0:
        raise BFSyntaxError(locale.unmatched_brackets.format(bracket="'['"))


    # generate asm with cache, keeping loop_stack across chunks
    asm_code = backend["header"] + "\n    " + backend["ptr_init"] + "\n"
    chunk_size = 50

    loop_stack = []
    label_id = 0

    i = 0
    while i < len(bf_code):
        chunk = bf_code[i:i+chunk_size]
        if chunk in cache:
            # load cached asm
            asm_code += cache[chunk]
            i += chunk_size
            continue

        chunk_asm = ""
        j = 0
        while j < len(chunk):
            c = chunk[j]
            if c == '>':
                chunk_asm += f"    {backend['inc_ptr']}\n"
            elif c == '<':
                chunk_asm += f"    {backend['dec_ptr']}\n"
            elif c == '+':
                chunk_asm += f"    {backend['inc_val']}\n"
            elif c == '-':
                chunk_asm += f"    {backend['dec_val']}\n"
            elif c == '.':
                chunk_asm += f"    {backend['output']}\n"
            elif c == ',':
                chunk_asm += f"    {backend['input']}\n"
            elif c == '[':
                start_label = f"loop_start_{label_id}"
                end_label = f"loop_end_{label_id}"
                loop_stack.append((start_label, end_label))
                chunk_asm += f"{start_label}:\n    {backend.get("cmp_byte_for_loop", "cmp byte [rsi], 0")}\n    je {end_label}\n"
                label_id += 1
            elif c == ']':
                if not loop_stack:
                    raise BFSyntaxError(locale.unmatched_brackets.format(bracket="']'"))
                start_label, end_label = loop_stack.pop()
                chunk_asm += f"    {backend.get("cmp_byte_for_loop", "cmp byte [rsi], 0")}\n    jne {start_label}\n{end_label}:\n"
            elif c == '#':
                comment_text = ""
                while j < len(chunk) and chunk[j] != '\n':
                    comment_text += chunk[j]
                    j += 1
                chunk_asm += f"    ;{comment_text.lstrip("#")}\n"
                continue
            j += 1

        # store generated chunk in cache
        cache[chunk] = chunk_asm
        asm_code += chunk_asm
        i += chunk_size

    # add exit syscall
    asm_code += f"    {backend['exit']}\n"

    # write output.asm
    with open(output_file, "w") as f:
        f.write(asm_code)

    # update cache
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=2)

    success_print(locale.generated_asm.format(output_file=output_file, cache_file=cache_file))

if __name__ == "__main__":
    main()