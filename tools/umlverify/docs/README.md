# umlverify

A Python library that checks an implementation against a UML design drawn in draw.io, and
reports every difference. It is deterministic — no AI anywhere — so the same design and the same
code always give the same report. [`tools/verify.py`](../../verify.py) is its command line; the
VS Code task *Verify design* runs that.

## How a verification works

```
diagrams/input/<type>.drawio ──read──▶ design model ────────────┐
                                                                 ├─ compare ─▶ reports/<type>-report.md
impl/ ──build──▶ extract ──────────▶ implemented model ──────────┘             diagrams/output/<type>-comparison.drawio
```

1. **Read the design.** The draw.io file is turned into a model, which is also written out as
   mermaid (`diagrams/output/<type>-design.mmd`).
2. **Build and extract the implementation.** The code must build; the implemented design is then
   read from it mechanically (for class diagrams: from the C++ headers, by libclang).
3. **Compare.** Both models become *elements* — for a class diagram, one class, attribute, method
   or relation each — and every element of either diagram lands in exactly one bucket:

   | Bucket | Meaning |
   |---|---|
   | ✅ Identical | in both, every detail matches |
   | ✏️ Changed | in both, at least one detail differs |
   | ➖ Missing | in the design only — the AI left it out |
   | ➕ Extra | in the implementation only — the AI added it |

   **Alignment = Identical ÷ (Identical + Changed + Missing + Extra)**, per category and in total,
   with no weights. The counts must add up (Identical + Changed + Missing = In design) and the
   library asserts that they do.
4. **Report.** A markdown report (overview table, legend, every difference) and a two-page
   draw.io comparison with every difference coloured, both from the same comparison result, so
   they cannot disagree.

The **input file's name picks the diagram type**: `class.drawio` runs the class-diagram flow.
All outputs carry the type as a prefix, so several diagram types can share one folder.

## Package layout

```
umlverify/
  __init__.py          FLOWS: input file name -> flow
  core/                diagram-agnostic
    drawio.py            read pages and cells; write cells, legends, documents; status colours
    compare.py           Element, the four buckets, alignment
    report.py            the markdown report
    routing.py           orthogonal routing around boxes, for lines nobody drew
    project.py           Context (a project's paths), FlowFailed/NotReady, the CMake build gate
  class_diagram/       the class-diagram flow: class.drawio + C++
    __init__.py          run(): read → build → extract → compare → report
    drawio_read.py       class.drawio -> model
    drawio_write.py      model -> draw.io shapes; the colour-coded comparison
    mermaid.py           the mermaid classDiagram subset, read and written
    cpp_extract.py       C++ headers -> model, via libclang
    elements.py          model -> elements; C++-aware type normalization
  docs/
    README.md            this file
    CLASS-DIAGRAMS.md    how the class-diagram flow reads, extracts and compares
    UML-CPP-MAPPING.md   the rules that turn UML into C++ and back
```

## Running

```bash
python3 tools/verify.py                  # asks which project; Enter repeats the last choice
python3 tools/verify.py project          # one project, by name or path
python3 tools/verify.py --all            # every project
```

The projects are `project/` (the student's own) and every folder under `examples/`. Designs are
the files in a project's `diagrams/input/`. Each run empties that project's `diagrams/output/`
and removes its `reports/*-report.md` first, so nothing stale survives.

A project that is not far enough yet is skipped, not failed: with no design it says where to save
one; with a design but no implementation it still converts the design to mermaid (a flow raises
`NotReady`). The exit status is 1 only when a report could not be made — for example, the
implementation does not build; the compiler's errors are printed so VS Code can link them.

## Adding a diagram type

A flow is a subpackage of `umlverify` with three names:

| Name | What |
|---|---|
| `NAME` | the input file name it handles, without `.drawio` — e.g. `"sequence"` |
| `TITLE` | a human-readable name — e.g. `"Sequence diagram"` |
| `run(ctx)` | reads `ctx.input`, writes `ctx.output("…")` and `ctx.report`, returns a `core.compare.Result`; raises `core.project.FlowFailed` with a plain-language reason when it cannot |

Then add it to `FLOWS` in `__init__.py`. Everything shared is in `core/`: reading draw.io pages
(`core.drawio.Page`), the comparison (`core.compare.compare` — you supply the elements and their
categories), the report (`core.report.render` — you supply the wording in a `ReportText`), the
colour palette and legend for the comparison drawing, and the CMake build gate. `class_diagram/`
is the reference for how the pieces fit.

## Design decisions

| Decision | Why |
|---|---|
| The implemented design is extracted from the code, never by an AI | Exact and repeatable. An AI reading the code tends to report the design it has already seen instead of the code. |
| Deterministic comparison, no weights | Same inputs, same report, nothing to argue with; a missing class outweighs a missing attribute only because its members go missing with it. |
| The report never fails a build | It is for self-assessment and instructor visibility, not a grade gate. |
| No layout engine | The comparison reuses the positions from the person's own draw.io file; the AI's additional classes go in a column on the right. |
| Unreadable parts of a design are warnings, never silent drops | A silently dropped element would look exactly like an implementation mistake. |

## Requirements and platform notes

Python 3, CMake, a C++20 compiler, and the libclang Python bindings (`requirements.txt`; the
VS Code task *Set up Python environment* installs them into `.venv/`).

libclang must match the standard library headers it parses. On macOS the `libclang` wheel's
bundled LLVM fails on Apple's libc++ (`'_Tp' does not refer to a value`), so `cpp_extract.py` uses
the Command Line Tools' `libclang.dylib` and passes the SDK path with `-isysroot`. On Linux the
system libclang matches. Windows is untested.

## The examples are the test suite

`examples/1-class-simple` must score 100 %, and `examples/2-class-library` must give exactly the
differences its README describes. After changing the library, run `tools/verify.py --all` and
check `git diff examples/`: generated files should only change when you meant them to.

Also look at what the library draws. `node tools/render-drawio/render.js <file.drawio>` renders
every page to PNG with draw.io's own viewer (set up once with
`npm install --prefix tools/render-drawio`). The checklist, and draw.io quirks found this way,
are in `.claude/skills/drawio-visual-check/SKILL.md`.

The draw.io reader was checked against a design with known content (every one of its 70 facts
reproduced), and the libclang extractor once found a relation missing from a hand-written
"expected" diagram — which is why expected diagrams are never written by hand.
