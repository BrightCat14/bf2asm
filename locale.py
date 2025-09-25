import ctypes
import os
from ctypes.util import find_library
from pathlib import Path

import bf2asm

locales_library = find_library("anLocales")

# just empty strings
unmatched_brackets = ""
usage = ""
generated_asm = ""
backend_not_implemented = ""

class AnLocales(ctypes.Structure):
    pass

class Locale(ctypes.Structure):
    pass

locales_folder = os.path.join(Path.home(), bf2asm.name, "locales")
locales_temp_folder = os.path.join(locales_folder, "temp")
locales_settings = os.path.join(locales_folder, "settings.json")

def init():
    global unmatched_brackets, usage, generated_asm, backend_not_implemented

    if locales_library is not None:
        lib = ctypes.CDLL(locales_library)
        AnLocales_p = ctypes.POINTER(AnLocales)
        Locale_p = ctypes.POINTER(Locale)
        # === AnLocales ===
        lib.anlocales_new_with_paths.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        lib.anlocales_new_with_paths.restype = AnLocales_p

        lib.anlocales_new.argtypes = []
        lib.anlocales_new.restype = AnLocales_p

        lib.anlocales_free.argtypes = [AnLocales_p]
        lib.anlocales_free.restype = None

        lib.anlocales_default_locale.argtypes = [AnLocales_p]
        lib.anlocales_default_locale.restype = Locale_p

        lib.anlocales_fallback_locale.argtypes = [AnLocales_p]
        lib.anlocales_fallback_locale.restype = Locale_p

        # === Locale ===
        lib.locale_load.argtypes = [AnLocales_p, ctypes.c_char_p]
        lib.locale_load.restype = Locale_p

        lib.locale_free.argtypes = [Locale_p]
        lib.locale_free.restype = None

        lib.locale_t.argtypes = [Locale_p, ctypes.c_char_p]
        lib.locale_t.restype = ctypes.c_char_p

        lib.locale_format_date.argtypes = [Locale_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
        lib.locale_format_date.restype = ctypes.c_char_p

        lib.locale_format_money.argtypes = [Locale_p, ctypes.c_double]
        lib.locale_format_money.restype = ctypes.c_char_p

        lib.locale_compare.argtypes = [Locale_p, ctypes.c_char_p, ctypes.c_char_p]
        lib.locale_compare.restype = ctypes.c_int

        lib.locale_plural_word.argtypes = [Locale_p, ctypes.c_char_p, ctypes.c_uint32]
        lib.locale_plural_word.restype = ctypes.c_char_p

        lib.locale_free_str.argtypes = [ctypes.c_char_p]
        lib.locale_free_str.restype = None

        al = lib.anlocales_new_with_paths(locales_folder.encode("utf-8"), locales_temp_folder.encode("utf-8"), locales_settings.encode("utf-8"))
        loc = lib.anlocales_default_locale(al)

        unmatched_brackets = lib.locale_t(loc, b"unmatched_brackets").decode()
        usage = lib.locale_t(loc, b"usage").decode()
        generated_asm = lib.locale_t(loc, b"generated_asm").decode()
        backend_not_implemented = lib.locale_t(loc, b"backend_not_implemented").decode()
    else:
        unmatched_brackets = "Unmatched {bracket} in bf code"
        usage = "Usage"
        generated_asm = "asm generated in {output_file} (cache stored in {cache_file})"
        backend_not_implemented = "Backend for {arch}/{os_name} not implemented yet"