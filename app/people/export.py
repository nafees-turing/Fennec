import html

from fpdf import FPDF

SECTIONS = (
    ("Names", "names"),
    ("Emails", "emails"),
    ("Phones", "phones"),
    ("Usernames", "usernames"),
    ("Accounts", "accounts"),
    ("Addresses", "addresses"),
    ("Companies", "companies"),
    ("URLs", "urls"),
    ("Wallets", "wallets"),
    ("Places", "places"),
    ("Wikidata", "wikidata"),
    ("Other", "other"),
)


def _text(value: object) -> str:
    return str(value or "").encode("latin-1", "replace").decode("latin-1")


def _is_http(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _looks_email(value: str) -> bool:
    if "://" in value or value.lower().startswith("mailto:"):
        return False
    if " " in value or value.count("@") != 1:
        return False
    local, _, domain = value.partition("@")
    return bool(local) and "." in domain


def _item_html(value: str, slot: str) -> str:
    text = str(value)
    escaped = html.escape(text)
    if slot == "emails" or _looks_email(text):
        href = text if text.lower().startswith("mailto:") else f"mailto:{text}"
        return f'<a href="{html.escape(href, quote=True)}">{escaped}</a>'
    if _is_http(text):
        return f'<a href="{html.escape(text, quote=True)}">{escaped}</a>'
    return escaped


def render_html(profile: dict, case_name: str) -> str:
    """Standalone HTML page for one person profile."""
    title = str(profile.get("title") or "Profile")
    page_title = f"Fennec profile — {title}"
    count = profile.get("finding_count")
    meta_bits = ["Fennec", html.escape(str(case_name or ""))]
    if profile.get("id") is not None:
        meta_bits.append(f"#{html.escape(str(profile['id']))}")
    if count is not None:
        meta_bits.append(f"{html.escape(str(count))} findings")
    avatar = profile.get("avatar_url")
    avatar_html = ""
    if avatar:
        avatar_html = (
            f'<img class="avatar" src="{html.escape(str(avatar), quote=True)}" alt="">'
        )
    sections = []
    for label, key in SECTIONS:
        items = [str(item) for item in (profile.get(key) or []) if str(item).strip()]
        if not items:
            continue
        rows = "".join(f"<li>{_item_html(item, key)}</li>" for item in items)
        sections.append(f"<h2>{html.escape(label)}</h2><ul>{rows}</ul>")
    body = "\n".join(sections) or "<p class=\"muted\">No profile fields.</p>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(page_title)}</title>
  <style>
    body {{ font-family: "Segoe UI", Helvetica, Arial, sans-serif; margin: 2rem auto; max-width: 48rem; color: #0f172a; }}
    h1, h2 {{ font-weight: 650; color: #1e3a8a; }}
    .muted {{ color: #64748b; }}
    .avatar {{ width: 96px; height: 96px; object-fit: cover; border-radius: 8px; border: 1px solid #cbd5e1; }}
    ul {{ padding-left: 1.2rem; }}
    li {{ margin: 0.2rem 0; }}
    a {{ color: #1d4ed8; }}
  </style>
</head>
<body>
  <p class="muted">{" · ".join(meta_bits)}</p>
  {avatar_html}
  <h1>{html.escape(title)}</h1>
  {body}
</body>
</html>
"""


def render_pdf(profile: dict, case_name: str) -> bytes:
    """PDF bytes for one person profile. Use fpdf2 like app/pdf.py."""
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

    title = profile.get("title") or "Profile"
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(width, 10, _text(f"Fennec profile: {title}"))
    body(f"Case: {case_name}", 11)
    count = profile.get("finding_count")
    if count is not None:
        body(f"Findings: {count}", 11)
    for label, key in SECTIONS:
        items = [str(item) for item in (profile.get(key) or []) if str(item).strip()]
        if not items:
            continue
        heading(label)
        for item in items:
            body(item)
    return bytes(pdf.output())
