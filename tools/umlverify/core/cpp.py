"""Parsing a project's C++ headers with libclang; shared by every flow that reads C++.

translation_unit(include_dir) parses every header under include_dir as one unit and
returns (tu, ours): the translation unit, and a predicate telling whether a cursor
was declared in those headers rather than in the standard library.
"""
import pathlib
import subprocess
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


def translation_unit(include_dir):
    """Parse all headers under include_dir as one unit -> (tu, ours).

    Raises RuntimeError with the first compiler error, or when there are no headers.
    """
    include = Path(include_dir)
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
        pass
    tu = ci.Index.create().parse("all.cpp", args=args, unsaved_files=[("all.cpp", unit)])
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
