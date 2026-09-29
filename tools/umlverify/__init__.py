"""umlverify — check an implementation against a UML design drawn in draw.io.

Each kind of UML diagram has its own *flow*: a subpackage with

    NAME    the input file name it handles, without .drawio ("class" -> class.drawio)
    TITLE   a human-readable name
    run(ctx: core.project.Context) -> core.compare.Result
            reads ctx.input, writes ctx.output(...) and ctx.report; raises
            core.project.FlowFailed when it cannot produce a report, or its
            subclass NotReady when the project has not got that far yet

The input file's name picks the flow. To add a diagram type, write the subpackage
and register it in FLOWS below; see docs/README.md.
"""
from pathlib import Path

from . import class_diagram

FLOWS = {flow.NAME: flow for flow in (class_diagram,)}


def flow_for(input_path):
    """The flow for diagrams/input/<name>.drawio, or None if the type is not supported."""
    return FLOWS.get(Path(input_path).stem)


def supported():
    return [f"{name}.drawio" for name in sorted(FLOWS)]
