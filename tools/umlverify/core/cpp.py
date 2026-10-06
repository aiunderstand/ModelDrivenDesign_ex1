"""Parsing a project's C++ headers with libclang; shared by every flow that reads C++.

translation_unit(include_dir) parses every header under include_dir as one unit and
returns (tu, ours): the translation unit, and a predicate telling whether a cursor
was declared in those headers rather than in the standard library.
"""
import pathlib
import subprocess
import sys
from pathlib import Path

import clang.cindex as ci

# Match libclang to the SDK whose headers we parse. The pip wheel ships its own
# LLVM, which chokes on Apple's libc++; the CommandLineTools dylib is the same
# version as the SDK. On Linux/devcontainer the system libclang is already right.
for _candidate in ("/Library/Developer/CommandLineTools/usr/lib/libclang.dylib",):
    if pathlib.Path(_candidate).exists():
        ci.Config.set_library_file(_candidate)
        break

HEADER_SUFFIXES = {".h", ".hh", ".hpp", ".hxx"}


def headers(include_dir):
    """Every header under include_dir, sorted."""
    include = Path(include_dir)
    return sorted(p for p in include.rglob("*") if p.suffix in HEADER_SUFFIXES)


_UNITS = {}   # resolved include dir -> (tu, ours): one parse per run, however many flows ask


def translation_unit(include_dir):
    """Parse all headers under include_dir as one unit -> (tu, ours).

    Raises RuntimeError with the first compiler error, or when there are no headers.
    """
    include = Path(include_dir)
    key = str(include.resolve())
    if key not in _UNITS:
        _UNITS[key] = _parse(include)
    return _UNITS[key]


def project_classes(include_dir):
    """The names of the classes, structs and class templates the headers define, in order."""
    tu, ours = translation_unit(include_dir)
    names = []

    def walk(cur):
        for c in cur.get_children():
            if c.kind == ci.CursorKind.NAMESPACE:
                walk(c)
            elif (c.kind in (ci.CursorKind.CLASS_DECL, ci.CursorKind.STRUCT_DECL,
                             ci.CursorKind.CLASS_TEMPLATE)
                  and ours(c) and c.is_definition() and c.spelling and c.spelling not in names):
                names.append(c.spelling)
    walk(tu.cursor)
    return names


def _resource_dir():
    """Elsewhere (Linux, CI), the wheel ships without clang's own headers (stddef.h, ...),
    so every standard header fails. Borrow them from an installed clang, if there is one."""
    try:
        found = subprocess.run(["clang", "-print-resource-dir"], capture_output=True,
                               text=True, check=True).stdout.strip()
    except Exception:
        return []
    return [f"-resource-dir={found}"] if (Path(found) / "include" / "stddef.h").exists() else []


def _windows_args():
    """On Windows the pip wheel finds no standard library at all. Point it at the MSVC and
    Windows SDK headers: from %INCLUDE% (a Developer Command Prompt sets it), else by
    looking for the newest Visual Studio and Windows 10/11 SDK installed."""
    import os
    dirs = [d for d in os.environ.get("INCLUDE", "").split(os.pathsep) if d]
    if not dirs:
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        try:
            vs = subprocess.run(
                [str(Path(pf86) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"),
                 "-latest", "-products", "*", "-property", "installationPath"],
                capture_output=True, text=True, check=True).stdout.strip()
            tools = sorted((Path(vs) / "VC" / "Tools" / "MSVC").glob("*"))
            if tools:
                dirs.append(str(tools[-1] / "include"))
        except Exception:
            pass
        sdks = sorted((Path(pf86) / "Windows Kits" / "10" / "Include").glob("10.*"))
        if sdks:
            dirs += [str(sdks[-1] / sub) for sub in ("ucrt", "um", "shared")]
    # The pip wheel is Clang 18; the newest MSVC STL insists on Clang 20 (error STL1000)
    # unless told the mismatch is deliberate.
    return (["-fms-compatibility", "-fms-extensions", "-D_ALLOW_COMPILER_AND_STL_VERSION_MISMATCH"]
            + [f"-isystem{d}" for d in dirs])


def _parse(include):
    found = headers(include)
    if not found:
        raise RuntimeError(f"no C++ headers found under {include}")
    unit = "\n".join(f'#include "{h.relative_to(include).as_posix()}"' for h in found)
    args = ["-std=c++20", f"-I{include}", "-xc++"]
    # The pip libclang wheel is not the platform driver, so on macOS it needs the
    # SDK spelled out. A C++ tool linking the system libclang inherits these.
    try:
        sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True,
                             text=True, check=True).stdout.strip()
        args += [f"-isysroot{sdk}", f"-I{sdk}/usr/include/c++/v1", f"-I{sdk}/usr/include"]
    except Exception:
        args += _resource_dir()
        if sys.platform == "win32":
            args += _windows_args()
    tu =ci.Index.create().parse("all.cpp", args=args, unsaved_files=[("all.cpp", unit)])
    for d in tu.diagnostics:
        if d.severity >= ci.Diagnostic.Error:
            loc = d.location
            where = f"{loc.file.name}:{loc.line}: " if loc.file else ""
            raise RuntimeError(f"{where}{d.spelling}")

    root = include.resolve()

    def ours(c):
        """Only declarations written in this project's headers -- not libc++."""
        f = c.location.file
        if f is None:
            return False
        try:
            return root in Path(f.name).resolve().parents
        except OSError:
            return False

    return tu, ours
