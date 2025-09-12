# bf2asm

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

Lightweight Brainfuck -> Assembly converter named "bf2asm" implemented entirely in Python.
Supports multiple CPU architectures and OSes, with caching for faster repeated compilation.

---

## Features

* Convert Brainfuck (`.b`) code to **x86\_64** or **ARM64** assembly.
* Supports **Linux** out of the box.
* Multi-backend support, easy to add new CPU/OS targets via `backends.json`.
* Automatic **cache** for repeated code chunks - faster recompilation.
* Basic **syntax checking** for unmatched `[` or `]`.

---

## Requirements

* Python 3.7+
* Linux (tested) or Windows

---

## Usage

```bash
python bf2asm.py <arch> <os> <input.b> <output.asm>
```

* `<arch>` – target architecture (`x86_64` or `arm64`)
* `<os>` – target operating system (`linux`)
* `<input.b>` – path to your Brainfuck source file
* `<output.asm>` – path where generated ASM will be written

### Example

```bash
python bf2asm.py x86_64 linux examples/helloworld.b helloworld.asm
```

Output:

```
asm generated in helloworld.asm (cache stored in /tmp/helloworld.b_cache.json)
```

---

## Adding new backends

You can add custom CPU/OS backends in a JSON file at:

```
~/bf2asm/backends.json
```

Format example:

```json
{
  "riscv_linux": {
    "ptr_init": "...",
    "inc_ptr": "...",
    "dec_ptr": "...",
    "inc_val": "...",
    "dec_val": "...",
    "output": "...",
    "input": "...",
    "exit": "...",
    "header": "..."
  }
}
```

---

## How it works

1. Reads Brainfuck code from the input file.
2. Validates `[` and `]` balance.
3. Splits code into chunks (default 50 commands).
4. Checks cache for pre-generated ASM for chunks.
5. Generates ASM for each chunk using backend instructions.
6. Writes final ASM.
7. Updates cache for faster future compilations.

---

## License

MIT License - feel free to use or modify.