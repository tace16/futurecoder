import json
import traceback
from collections import Counter
from typing import Union, Iterable, List

from cheap_repr import cheap_repr
from executing import Source
from pygments.formatters.html import HtmlFormatter
from stack_data import (
    style_with_executing_node,
    Options,
    Line,
    FrameInfo,
    Variable,
    RepeatedFrames,
)

from main.utils import internal_dir

pygments_style = style_with_executing_node("monokai", "bg:#005080")
pygments_formatter = HtmlFormatter(
    style=pygments_style,
    nowrap=True,
)


class TracebackSerializer:
    def format_exception(self, e) -> List[dict]:
        if e.__cause__ is not None:
            result = self.format_exception(e.__cause__)
            result[-1]["tail"] = traceback._cause_message
        elif e.__context__ is not None and not e.__suppress_context__:
            result = self.format_exception(e.__context__)
            result[-1]["tail"] = traceback._context_message
        else:
            result = []

        result.append(
            dict(
                frames=self.format_stack(e.__traceback__),
                exception=dict(
                    type=type(e).__name__,
                    message=traceback._some_str(e),
                ),
                tail="",
            )
        )
        return result

    def format_stack(self, frame_or_tb) -> List[dict]:
        return list(
            self.format_stack_data(
                FrameInfo.stack_data(
                    frame_or_tb,
                    Options(before=0, after=0, pygments_formatter=pygments_formatter),
                    collapse_repeated_frames=True,
                )
            )
        )

    def format_stack_data(
        self, stack: Iterable[Union[FrameInfo, RepeatedFrames]]
    ) -> Iterable[dict]:
        for item in stack:
            if isinstance(item, FrameInfo):
                if item.filename != "my_program.py":
                    continue
                yield self.format_frame(item)
            else:
                yield self.format_repeated_frames(item)

    def format_repeated_frames(self, repeated_frames: RepeatedFrames) -> List[dict]:
        counts = sorted(
            Counter(repeated_frames.frame_keys).items(),
            key=lambda item: (-item[1], item[0][0].co_name),
        )
        return [
            dict(
                name=code.co_name,
                lineno=lineno,
                count=count,
            )
            for (code, lineno), count in counts
        ]

    def format_frame(self, frame: FrameInfo) -> dict:
        return dict(
            type="frame",
            name=frame.executing.code_qualname(),
            variables=list(self.format_variables(frame)),
            lines=list(self.format_lines(frame.lines)),
        )

    def format_lines(self, lines):
        for line in lines:
            if isinstance(line, Line):
                yield self.format_line(line)
            else:
                yield dict(type="line_gap")

    def format_line(self, line: Line) -> dict:
        return dict(
            type="line",
            is_current=line.is_current,
            lineno=line.lineno,
            content=line.render(
                pygmented=True,
                escape_html=True,
                strip_leading_indent=True,
            ),
        )

    def format_variables(self, frame_info: FrameInfo) -> Iterable[str]:
        for var in sorted(frame_info.variables, key=lambda v: v.name):
            yield self.format_variable(var)

    def format_variable(self, var: Variable) -> dict:
        return dict(
            name=var.name,
            value=cheap_repr(var.value),
        )


def test():
    def foo():
        print(1 / 0)

    try:
        foo()
    except Exception as e:
        print(json.dumps(TracebackSerializer().format_exception(e), indent=4))


if __name__ == "__main__":
    test()