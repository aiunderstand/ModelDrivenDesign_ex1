# UML design verification

Draw a UML design in draw.io, let an AI implement it in C++, and see exactly where the
implementation differs from the design: as a report, and as a colour-coded draw.io diagram.

## Try it

1. Open this folder in VS Code. Install the recommended extensions when it asks.
2. Press **Ctrl+Shift+B** (**Cmd+Shift+B** on macOS) and choose an example.
3. Open that example's `reports/class-report.md` and click
   **Open the colour-coded comparison in draw.io**. The legend on each page explains the colours.

You need Python 3, CMake and a C++20 compiler (on macOS, the Xcode Command Line Tools). The first
run sets up `.venv/` with libclang, which takes a minute.

## How it works

```
diagrams/input/class.drawio   ← a person draws the design
impl/                         ← an AI writes the C++

        Ctrl+Shift+B

reports/class-report.md                    what differs, with an alignment score
diagrams/output/class-comparison.drawio    design and implementation side by side,
                                           every difference coloured
```

The implemented design is read from the code by libclang, not by an AI. The same design and
the same code therefore always give the same report.

## Examples

| Example | What it shows | Alignment |
|---|---|:-:|
| [1-class-simple](examples/1-class-simple/) | 3 classes, implemented exactly as designed | 100 % |
| [2-class-library](examples/2-class-library/) | 11 classes, with three deliberate mistakes to find | 90.7 % |

## Your own design

Your work goes in [`project/`](project/), which is always first in the menu:

```
project/
  diagrams/input/class.drawio     1. draw your design here
  impl/CMakeLists.txt             2. the AI writes the implementation here
  impl/include/…                     (the headers are what gets compared)
  impl/src/…
```

Run the task after each step. With no drawing yet, it tells you where to save one. With a drawing
but no implementation, it converts the design to `diagrams/output/class-design.mmd`, the text
version to hand to the AI. Once both exist, you get the report.

In VS Code, create `class.drawio` and it opens in the draw.io editor. The class shapes are under
**More Shapes › UML**. The file's name says what kind of diagram it is; only class diagrams are
supported so far.

## In this repository

| Folder | Contains |
|---|---|
| [`project/`](project/) | your own design and implementation |
| [`examples/`](examples/) | worked examples |
| [`tools/`](tools/) | `verify.py`, which the task runs, the `umlverify` library, and `render-drawio` |
| [`.vscode/`](.vscode/) | the *Verify design* task and the recommended extensions |

AI agents implementing a design are guided by [`AGENTS.md`](AGENTS.md): where to write, which
structure to use, and how UML maps to C++.

How the verification works, and how to add a diagram type:
[tools/umlverify/docs/](tools/umlverify/docs/README.md). How UML maps to C++:
[UML-CPP-MAPPING.md](tools/umlverify/docs/UML-CPP-MAPPING.md).

**Not there yet:** a devcontainer, and diagram types other than class diagrams.
