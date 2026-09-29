# AGENTS.md

Instructions for AI coding agents (GitHub Copilot, Claude, Codex, …) working in this repository.

Your job is to **implement a UML class diagram in C++**, in `project/impl/`. A person drew the
design; a verifier then compares your headers with it, element by element, and reports every
difference. Success is **100 % alignment**: the code is exactly the design, nothing more and
nothing less.

## Where things are

| Path | What it is | You may |
|---|---|---|
| `project/diagrams/input/class.drawio` | the design, drawn by a person | read — **never edit** |
| `project/diagrams/output/class-design.mmd` | the same design as mermaid text, generated | read — easiest to parse |
| `project/impl/` | the implementation | **write here, and only here** |
| `project/process/` | specs and plans for your work (see below) | write |
| `project/reports/class-report.md` | the verification report, generated | read |
| `examples/` | worked examples | read |
| `tools/` | the verifier | read |

`class-design.mmd` is created by the verifier. If it is missing, run the verifier once (see
[Check your work](#check-your-work)); it converts the drawing even before any code exists.

## Project structure

Use exactly this layout:

```
project/impl/
  CMakeLists.txt
  include/<name>/<class>.hpp    one header per class; <name> is a short lowercase project name
  src/<class>.cpp               one source per class that has code; plus src/demo.cpp
```

- **Headers in `include/` are what gets compared with the design.** Every class, attribute,
  method and relation must be declared there. Sources in `src/` are built but not compared.
- Use `snake_case` file names (`library_item.hpp` for `LibraryItem`) and put everything in one
  namespace, e.g. `namespace library { … }`.
- `CMakeLists.txt` follows [examples/1-class-simple/impl/CMakeLists.txt](examples/1-class-simple/impl/CMakeLists.txt):
  C++20, `CMAKE_EXPORT_COMPILE_COMMANDS ON`, a static library from `src/*.cpp` with `include`
  as its public include directory, `-Wall -Wextra`, and a small `demo` executable that uses the
  classes. The build must succeed without warnings.

## Rules for the implementation

**1. Follow the mapping exactly.** [tools/umlverify/docs/UML-CPP-MAPPING.md](tools/umlverify/docs/UML-CPP-MAPPING.md)
defines which C++ construct each UML element becomes. The verifier applies it mechanically, so
anything else is reported as a difference. The rules that matter most:

| In the design | In C++ |
|---|---|
| `Owner *-- Part` composition (filled diamond) | `std::unique_ptr<Part>` or a by-value `Part` member |
| `Owner o-- Part` aggregation (hollow diamond) | `std::shared_ptr<Part>` member |
| `A --> B` association (open arrow) | `B*`, `B&` or `std::weak_ptr<B>` member |
| `A ..> B` dependency (dashed) | `B` only in a parameter or return type, never a member |
| multiplicity `*` / `0..1` | `std::vector<…>` / `std::optional<…>` |
| `+` / `#` / `-` | `public:` / `protected:` / `private:` |
| `<<interface>>` | only pure virtual methods, no data members, virtual destructor |
| `<<abstract>>` / italic method | at least one pure virtual method (`= 0`) and data members |
| `<<enumeration>>` | `enum class` |
| underlined member (static) | `static` |

Ownership is the easy one to get wrong, because the wrong choice still compiles: do **not**
reach for `std::shared_ptr` unless the design shows a hollow diamond.

**2. Implement exactly what is drawn.**
- Every class, attribute, method and relation in the design — no fewer.
- Nothing that is not in the design: no helper or utility classes, no extra public or private
  methods, no extra data members. Put helper logic inside the method bodies in `src/`.
- Constructors, destructors and operators are fine; the diagram leaves them out by convention.
- A member that implements a relation is not also an attribute: `Playlist *-- "*" Song : songs`
  is one member, `std::vector<Song> songs_;`.

**3. Use the design's names and types.**
- Class, method and attribute names as drawn. Private data members may take a trailing
  underscore (`name_` for `name`); the verifier ignores it.
- A relation's role name is the member's name: `: borrower` → `borrower_`.
- `string` → `std::string`, `size_t` → `std::size_t`, `vector<T>` → `std::vector<T>`.
- Parameter and return types as drawn; `const T&` for class-typed parameters is fine.

## Check your work

Run the verifier after every change:

- **VS Code:** Ctrl+Shift+B (Cmd+Shift+B on macOS), choose `project`.
- **Terminal:** `.venv/bin/python tools/verify.py project` (the VS Code task *Set up Python
  environment* creates `.venv/` the first time).

Then read `project/reports/class-report.md`. Fix every **Changed**, **Missing** and **Extra**
entry and run it again until alignment is 100 %. If a build error is reported, the compiler's
messages are printed above the summary. Do not edit the report or the files in
`project/diagrams/output/`: they are regenerated on every run.

## Process files

Keep your working notes in `project/process/`:

- `specs/` — what to build. Before writing code, write down each class from the design with its
  members and relations, and the C++ construct each one maps to.
- `plans/` — how you will build it: a checklist of steps, one file per piece of work, named
  `YYYY-MM-DD-<topic>.md`.
- `plans/completed/` — move a plan here once all its steps are done and the verifier reports
  100 %.

## Examples

- [examples/1-class-simple](examples/1-class-simple/) — three classes, implemented exactly as
  designed, 100 %. **Copy its structure and style.**
- [examples/2-class-library](examples/2-class-library/) — eleven classes covering interfaces,
  abstract classes, enums, templates and every kind of relation. Its implementation contains
  **three deliberate mistakes** (listed in its README): learn from the rest, never copy those.

## If you change a draw.io file

This is only for work on the examples or the tools, never on `project/diagrams/input/`. Render it
and look at the result before calling it done:
`node tools/render-drawio/render.js <file.drawio>`. The checklist is the `drawio-visual-check`
skill ([.claude/skills/drawio-visual-check/SKILL.md](.claude/skills/drawio-visual-check/SKILL.md)),
which GitHub Copilot and Claude Code both load automatically; in Copilot Chat you can also type
`/drawio-visual-check`.
