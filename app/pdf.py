from fpdf import FPDF


def _text(value: object) -> str:
    return str(value or "").encode("latin-1", "replace").decode("latin-1")


def render(case: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    width = pdf.epw

    def heading(title: str) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 13)
        pdf.multi_cell(width, 8, _text(title))

    def body(text: str, size: int = 10) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", size=size)
        pdf.multi_cell(width, 5, _text(text))

    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(width, 10, _text(f"Fennec dossier: {case.get('name', '')}"))
    body(case.get("notes") or "Local OSINT case. Public sources only.", 11)
    heading("Findings")
    for row in case.get("findings") or []:
        body(f"{row.get('kind')}: {row.get('value')} [{row.get('source')} / {row.get('confidence')}]")
        if row.get("evidence"):
            body(str(row["evidence"]))
    heading("Links")
    links = case.get("links") or []
    if not links:
        body("No shared values.")
    for row in links:
        body(f"{row.get('kind')} · {row.get('value')} · {row.get('count')} findings")
    heading("Runs")
    for run in case.get("runs") or []:
        extra = f" · {run['error']}" if run.get("error") else ""
        body(f"{run.get('module_id')} · {run.get('input_value')} · {run.get('status')}{extra}")
    return bytes(pdf.output())
