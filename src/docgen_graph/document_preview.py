import re
from html import escape

from markdown_it import MarkdownIt


def render_document_preview(markdown: str, evidence_files: dict[str, str] | None = None) -> str:
    parser = MarkdownIt("commonmark", {"html": False}).enable("table")
    notes = {}

    def collect_note(match):
        notes[match[1]] = match[2]
        return ""

    body = re.sub(r"^\[\^(\d+)\]: (.+)$", collect_note, markdown, flags=re.M)
    tokens = parser.parse(body)
    outline = []
    title = "Documentation"
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            text = tokens[index + 1].content
            identifier = "document-title" if token.tag == "h1" else f"section-{len(outline) + 1}"
            token.attrSet("id", identifier)
            if token.tag == "h1":
                title = text
            else:
                outline.append((token.tag, identifier, text))

    default_fence = parser.renderer.rules["fence"]

    def render_fence(items, index, options, env):
        if items[index].info.strip() == "mermaid":
            return '<pre class="mermaid">' + escape(items[index].content) + "</pre>\n"
        return default_fence(items, index, options, env)

    parser.renderer.rules["fence"] = render_fence
    content = parser.renderer.render(tokens, parser.options, {})
    content = re.sub(
        r"\[\^(\d+)\]",
        lambda match: (
            f'<sup><a class="citation" href="#evidence-{match[1]}" '
            f'aria-label="Source {match[1]}">{match[1]}</a></sup>'
            if match[1] in notes
            else match[0]
        ),
        content,
    )
    content = re.sub(
        r"<p>(<strong>(?:Figure|Diagram|Illustration) \d+[.:])",
        r'<p class="figure-caption">\1',
        content,
    )
    navigation = "".join(
        f'<a class="level-{level}" href="#{identifier}">{escape(text)}</a>'
        for level, identifier, text in outline
    )
    sources = []
    for number, label in notes.items():
        target = re.search(r"\]\(([^)]+)\)", label)
        excerpt = (evidence_files or {}).get(target[1], "") if target else ""
        rendered_excerpt = parser.render(excerpt) if excerpt else parser.render(label)
        rendered_excerpt = re.sub(
            r'href="(?![a-z]+:|/|#|evidence/)([^"#]+\.md)"',
            r'href="evidence/\1"',
            rendered_excerpt,
        )
        sources.append(
            f'<details id="evidence-{number}" class="evidence"><summary>'
            f'Source {number}</summary>{rendered_excerpt}</details>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)}</title><style>{PREVIEW_CSS}</style></head><body>"
        '<div class="document-shell"><aside><a class="brand" href="#document">'
        'DOCUMENTATION</a><nav aria-label="Contents">'
        + navigation
        + '<a class="sources-link" href="#sources">Sources</a></nav></aside>'
        '<main id="document"><article>'
        + content
        + '</article><section id="sources" class="source-register"><h2>Sources</h2>'
        '<p class="source-intro">Open a reference to read its exact supporting passage.</p>'
        + "".join(sources)
        + f"</section></main></div><script type=\"module\">{PREVIEW_JS}</script></body></html>"
    )


PREVIEW_CSS = """
:root{color-scheme:light;--ink:#203247;--muted:#536779;--accent:#195b78;--line:#dce4e8}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:28px}
body{margin:0;background:#f3f5f6;color:var(--ink);font:16px/1.72 'Segoe UI',Arial,sans-serif}
.document-shell{display:grid;grid-template-columns:245px minmax(0,900px);gap:36px;
max-width:1250px;padding:40px 30px;margin:auto}aside{position:sticky;top:30px;
align-self:start;max-height:calc(100vh - 60px);overflow:auto;padding:10px 4px}
.brand{font-size:11px;font-weight:700;letter-spacing:.16em;color:var(--accent);text-decoration:none}
nav{margin-top:25px}nav a{display:block;font-size:13px;line-height:1.45;color:var(--muted);
text-decoration:none;padding:8px 12px;border-left:2px solid transparent}
nav a:hover,nav a:focus{color:var(--accent);border-color:var(--accent);background:#e9eff2}
nav .level-h3{padding-left:24px;font-size:12px}.sources-link{margin-top:16px}
main{background:white;border:1px solid var(--line);border-radius:10px;padding:48px 56px;
box-shadow:0 8px 30px #20324706;min-width:0}h1,h2,h3,h4{line-height:1.3;letter-spacing:-.02em}
h1{font-size:36px;margin:0 0 30px;font-weight:650;padding-bottom:26px;
border-bottom:3px solid var(--accent)}
h2{font-size:25px;margin:48px 0 18px;padding-top:12px;border-top:1px solid var(--line)}
h3{font-size:20px;margin:30px 0 12px;color:#244c64}h4{font-size:17px;margin-top:26px}
p{margin:0 0 18px}a{color:var(--accent);text-underline-offset:3px}li{padding:3px 0}
table{border-collapse:collapse;width:100%;font-size:14px;margin:24px 0;display:block;overflow:auto}
th,td{text-align:left;vertical-align:top;padding:12px 14px;border:1px solid var(--line)}
th{background:#eef4f6;font-weight:650}tr:nth-child(even) td{background:#fafcfc}
img{display:block;max-width:100%;max-height:620px;height:auto;object-fit:contain;
margin:26px auto 12px;border-radius:5px;border:1px solid var(--line)}
.figure-caption{text-align:center;font-size:14px;color:var(--muted);margin:10px 0 30px;
line-height:1.5}
.mermaid{background:#fafcfc;border:1px solid var(--line);border-radius:6px;padding:20px;
margin:24px 0 10px;overflow:auto;text-align:center}.mermaid svg{max-width:100%;height:auto}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7f8;padding:18px;border-radius:5px}
code{font-size:.88em}sup{line-height:0}.citation{font-size:11px;font-weight:650;margin:0 2px;
padding:1px 3px;text-decoration:none;border-radius:3px;background:#eaf2f5}
.citation:hover{background:#d3e5ed}.source-register{margin-top:54px}.source-intro{font-size:14px;color:var(--muted)}
.evidence{border:1px solid var(--line);border-radius:5px;margin:9px 0;padding:12px 16px;
font-size:14px}
.evidence:target{border-color:var(--accent)}summary{cursor:pointer;font-weight:600}
.evidence h1{font-size:18px;border:0;margin:15px 0;padding:0}.evidence blockquote{margin:12px 0;
border-left:3px solid #8aafbf;padding:10px 16px;background:#f5f9fa;white-space:normal}
.diagram-failure{font-size:14px;color:#805321}.source-register h2{font-size:22px}
@media(max-width:850px){.document-shell{display:block;padding:12px}aside{position:static;
max-height:none;padding:16px}nav{display:none}main{padding:28px 22px}
h1{font-size:29px}h2{font-size:23px}}
@media print{body{background:white}.document-shell{display:block;padding:0}aside{display:none}
main{border:0;padding:0;box-shadow:none}h2,h3,.figure-caption{break-after:avoid}
img,.mermaid{break-inside:avoid}a{color:inherit}.source-register{page-break-before:always}}
"""


PREVIEW_JS = """
function revealEvidence() {
  const id = decodeURIComponent(location.hash.slice(1));
  const target = document.getElementById(id);
  if (target?.matches('details.evidence')) target.open = true;
}
window.addEventListener('hashchange', revealEvidence);
revealEvidence();
const diagrams = [...document.querySelectorAll('pre.mermaid')];
window.documentDiagramResults = [];
if (diagrams.length) {
  try {
    const {default: mermaid} = await import(
      'https://cdn.jsdelivr.net/npm/mermaid@12.2.0/dist/mermaid.esm.min.mjs'
    );
    mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'neutral',
      fontFamily:'Segoe UI, Arial, sans-serif',flowchart:{htmlLabels:false}});
    for (let index = 0; index < diagrams.length; index++) {
      const target = diagrams[index];
      const source = target.textContent;
      try {
        await mermaid.parse(source);
        const {svg} = await mermaid.render('document-diagram-' + index, source);
        target.innerHTML = svg;
        window.documentDiagramResults.push({index,valid:true});
      } catch (error) {
        target.textContent = source;
        target.classList.add('diagram-failure');
        window.documentDiagramResults.push({index,valid:false,error:String(error)});
      }
    }
  } catch (error) {
    const notice = document.createElement('p');
    notice.className = 'diagram-failure';
    notice.textContent = 'Diagram preview is unavailable. The diagram definition is shown below.';
    diagrams[0].before(notice);
    window.documentDiagramResults.push({valid:false,error:String(error)});
  }
}
"""
