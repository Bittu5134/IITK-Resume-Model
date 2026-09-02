"""Generate official CDW submission PDF from docs/ATR.md.

Produces: PoolName_CDW_PS_DiagnosticEngine.pdf
conforming to official Anweshan '26 guidelines.
"""
import argparse
import re
from pathlib import Path
import pymupdf

def markdown_to_html(md_text: str) -> str:
    """Basic Markdown to HTML converter for PyMuPDF HTML box rendering."""
    lines = md_text.splitlines()
    html_parts = []
    
    html_parts.append("""
    <style>
        body { font-family: Helvetica, Arial, sans-serif; font-size: 9.5pt; line-height: 1.45; color: #1e293b; }
        h1 { font-size: 18pt; color: #002147; border-bottom: 2px solid #FFC72C; padding-bottom: 4px; margin-top: 14px; margin-bottom: 8px; }
        h2 { font-size: 13pt; color: #002147; border-bottom: 1px solid #cbd5e1; padding-bottom: 3px; margin-top: 12px; margin-bottom: 6px; }
        h3 { font-size: 10.5pt; color: #1e40af; margin-top: 8px; margin-bottom: 4px; }
        p { margin-top: 3px; margin-bottom: 6px; }
        ul { margin-top: 2px; margin-bottom: 6px; padding-left: 18px; }
        li { margin-bottom: 2px; }
        code { font-family: Courier, monospace; background-color: #f1f5f9; color: #0f172a; font-size: 8.5pt; }
        pre { font-family: Courier, monospace; background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 6px; font-size: 7.5pt; margin: 6px 0; }
        table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 8pt; }
        th { background-color: #002147; color: #ffffff; border: 1px solid #cbd5e1; padding: 4px 6px; text-align: left; }
        td { border: 1px solid #cbd5e1; padding: 4px 6px; }
        tr:nth-child(even) { background-color: #f8fafc; }
        .badge { background-color: #e0f2fe; color: #0369a1; padding: 2px 5px; border-radius: 3px; font-weight: bold; }
    </style>
    """)

    in_list = False
    in_table = False
    table_rows = []
    in_code = False
    code_block = []

    for line in lines:
        stripped = line.strip()

        # Code block
        if stripped.startswith("```"):
            if in_code:
                in_code = False
                code_text = "\n".join(code_block).replace("<", "&lt;").replace(">", "&gt;")
                html_parts.append(f"<pre><code>{code_text}</code></pre>")
                code_block = []
            else:
                in_code = True
            continue

        if in_code:
            code_block.append(line)
            continue

        # Table rows
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                table_rows = []
            if "---" in stripped:
                continue  # Divider line
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            table_rows.append(cells)
            continue
        elif in_table:
            # End of table
            in_table = False
            html_parts.append("<table>")
            if table_rows:
                html_parts.append("<thead><tr>")
                for h in table_rows[0]:
                    html_parts.append(f"<th>{h}</th>")
                html_parts.append("</tr></thead><tbody>")
                for row in table_rows[1:]:
                    html_parts.append("<tr>")
                    for cell in row:
                        cell_fmt = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", cell)
                        html_parts.append(f"<td>{cell_fmt}</td>")
                    html_parts.append("</tr>")
                html_parts.append("</tbody>")
            html_parts.append("</table>")
            table_rows = []

        if not stripped:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue

        # Headers
        if stripped.startswith("# "):
            html_parts.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("## "):
            html_parts.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("### "):
            html_parts.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("- ") or stripped.startswith("• "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            item_text = stripped[2:]
            item_fmt = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", item_text)
            item_fmt = re.sub(r"`(.*?)`", r"<code>\1</code>", item_fmt)
            html_parts.append(f"<li>{item_fmt}</li>")
        elif stripped.startswith("---"):
            html_parts.append("<hr style='border: 0; border-top: 1px solid #cbd5e1; margin: 10px 0;'>")
        else:
            p_fmt = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", stripped)
            p_fmt = re.sub(r"`(.*?)`", r"<code>\1</code>", p_fmt)
            p_fmt = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', p_fmt)
            html_parts.append(f"<p>{p_fmt}</p>")

    if in_list:
        html_parts.append("</ul>")
    if in_table and table_rows:
        html_parts.append("<table><tbody>")
        for row in table_rows:
            html_parts.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
        html_parts.append("</tbody></table>")

    return "\n".join(html_parts)


def build_submission_pdf(atr_path: Path, output_pdf: Path, pool_name: str = "PoolName"):
    """Compile ATR Markdown into a multi-page PDF formatted for submission."""
    with open(atr_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Prepend Pool Title Cover
    content = content.replace("PoolName", pool_name)

    html = markdown_to_html(content)
    
    story = pymupdf.Story(html=html)
    writer = pymupdf.DocumentWriter(str(output_pdf))

    def rectfn(rect_num, filled):
        mediabox = pymupdf.Rect(0, 0, 595, 842)  # A4 size
        rect = pymupdf.Rect(45, 45, 550, 797)     # Margins
        return mediabox, rect, None

    story.write(writer, rectfn)
    writer.close()

    # Check page count
    doc = pymupdf.open(str(output_pdf))
    page_count = len(doc)
    doc.close()
    print(f"Generated official submission PDF ({page_count} pages): {output_pdf}")


def main():
    parser = argparse.ArgumentParser(description="Generate official CDW submission PDF")
    parser.add_argument("--pool", default="PoolSubmission", help="Pool Name (e.g. PoolA, Sharks, etc.)")
    parser.add_argument("--atr", default="docs/ATR.md", help="Path to ATR markdown")
    parser.add_argument("-o", "--output", help="Output PDF file path")
    args = parser.parse_args()

    out_name = args.output or f"{args.pool}_CDW_PS_DiagnosticEngine.pdf"
    atr_file = Path(args.atr)
    if not atr_file.exists():
        raise FileNotFoundError(f"ATR file not found: {atr_file}")

    build_submission_pdf(atr_file, Path(out_name), args.pool)

if __name__ == "__main__":
    main()
