"""One-time migration of legacy Streamlit HTML calls to escaped st.html output.

Only explicit st.markdown(..., unsafe_allow_html=True) calls are changed.
Static markup is preserved; each dynamic interpolation is HTML-escaped after
formatting. st.html additionally sanitizes the result using Streamlit's DOMPurify.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend"


class EscapeInterpolations(ast.NodeTransformer):
    def visit_JoinedStr(self, node):
        values = []
        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                # Preserve conversion and format specifiers before escaping.
                formatted = ast.JoinedStr(values=[value])
                call = ast.Call(func=ast.Name(id="escape_html", ctx=ast.Load()), args=[formatted], keywords=[])
                values.append(ast.FormattedValue(value=call, conversion=-1))
            else:
                values.append(value)
        return ast.copy_location(ast.JoinedStr(values=values), node)


def migrate(path):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    def offset(line, column):
        # AST columns are UTF-8 byte offsets, while source slicing uses characters.
        return offsets[line-1] + len(lines[line-1].encode("utf-8")[:column].decode("utf-8"))
    replacements = []
    escaped = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "st" or node.func.attr != "markdown":
            continue
        unsafe = next((kw for kw in node.keywords if kw.arg == "unsafe_allow_html"), None)
        if not unsafe or not isinstance(unsafe.value, ast.Constant) or unsafe.value.value is not True:
            continue
        node.func.attr = "html"
        node.keywords = [kw for kw in node.keywords if kw is not unsafe]
        if node.args and isinstance(node.args[0], ast.JoinedStr):
            node.args[0] = EscapeInterpolations().visit(node.args[0])
            escaped = True
        replacements.append((offset(node.lineno, node.col_offset), offset(node.end_lineno, node.end_col_offset), ast.unparse(ast.fix_missing_locations(node))))
    for start, end, value in sorted(replacements, reverse=True):
        source = source[:start] + value + source[end:]
    if escaped:
        source = "from html import escape as escape_html\n" + source
    if replacements:
        compile(source, str(path), "exec")
        path.write_text(source, encoding="utf-8")
    return len(replacements)


if __name__ == "__main__":
    changed = sum(migrate(path) for path in ROOT.rglob("*.py"))
    print(f"Migrated {changed} legacy HTML calls; dynamic interpolations are escaped.")
