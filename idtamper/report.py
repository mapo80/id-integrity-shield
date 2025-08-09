
import base64, json
from pathlib import Path
from PIL import Image
import io

HTML_TMPL = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8" />
<title>Report Forense — {title}</title>
<style>
 body {{ font-family: Arial, sans-serif; margin: 24px; }}
 h1 {{ margin-top: 0; }}
 .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
 .card {{ border: 1px solid #e0e0e0; border-radius: 10px; padding: 12px; }}
 .kpi {{ font-size: 18px; }}
 .ok {{ color: #2e7d32; }} .bad {{ color: #c62828; }}
 table {{ border-collapse: collapse; width: 100%; }}
 th, td {{ border: 1px solid #ddd; padding: 6px 8px; font-size: 14px; }}
 th {{ background: #f5f5f5; text-align: left; }}
 img {{ max-width: 100%; border-radius: 8px; }}
 .caption {{ font-size: 12px; color: #555; }}
</style>
</head>
<body>
<h1>Report Forense — {title}</h1>
<div class="kpi">Esito: <b class="{label_cls}">{label_txt}</b> — Score totale: <b>{score:.3f}</b> — Soglia: {thr:.3f} — Confidence: <b>{conf:.3f}</b></div>
<div class="grid">
  <div class="card">
    <h3>Originale</h3>
    <img src="data:image/png;base64,{img_b64}" alt="original"/>
  </div>
  <div class="card">
    <h3>Overlay</h3>
    <img src="data:image/png;base64,{ov_b64}" alt="overlay"/>
    <div class="caption">Fused heatmap sovrapposta</div>
  </div>
  <div class="card">
    <h3>Fused heatmap</h3>
    <img src="data:image/png;base64,{fused_b64}" alt="fused"/>
  </div>
</div>
<h2>Dettaglio per Controllo</h2>
<table>
<tr><th>Check</th><th>Score</th><th>Soglia</th><th>Flag</th><th>Note</th></tr>
{rows}
</table>
<h2>Heatmap per controllo</h2>
<div class="grid">
{hm_cards}
</div>
<hr/>
<small>Generato da IDTamper SDK — CPU. Timestamp: {ts}</small>
</body></html>
"""

def _img_to_b64(path):
    p = Path(path)
    if not p.exists():
        return ""
    with p.open("rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def _png_from_image(path, max_side=None):
    im = Image.open(path).convert("RGB")
    if max_side and max(im.size) > max_side:
        scale = max_side / float(max(im.size))
        im = im.resize((int(im.size[0]*scale), int(im.size[1]*scale)))
    bio = io.BytesIO()
    im.save(bio, format="PNG")
    return base64.b64encode(bio.getvalue()).decode("ascii")

def make_html(item_dir):
    item = Path(item_dir)
    rep = json.loads((item/"report.json").read_text())
    img_path = item / rep["image"]
    fused = item / rep["artifacts"].get("fused_heatmap","")
    overlay = item / rep["artifacts"].get("overlay","")
    # Build table rows & heatmap cards
    rows = []
    cards = []
    for name, v in rep["per_check"].items():
        score = v["score"]
        thr = v["threshold"]
        flag = v["flag"]
        note = ", ".join([f"{k}={v['details'][k]}" for k in sorted(v["details"].keys())]) if v.get("details") else ""
        rows.append(f"<tr><td>{name}</td><td>{score if score is not None else ''}</td><td>{thr:.3f}</td><td>{flag}</td><td>{note}</td></tr>")
        hm_name = f"heatmap_{name}"
        hm_file = item / f"{hm_name}.png"
        if hm_file.exists():
            cards.append(f'<div class="card"><h4>{name}</h4><img src="data:image/png;base64,{_img_to_b64(hm_file)}"/><div class="caption">{name} heatmap</div></div>')
    html = HTML_TMPL.format(
        title=rep["image"],
        label_cls="bad" if rep["is_tampered"] else "ok",
        label_txt="TAMPERED" if rep["is_tampered"] else "GENUINE",
        score=rep["tamper_score"],
        thr=rep["threshold"],
        img_b64=_png_from_image(img_path, max_side=1200),
        ov_b64=_img_to_b64(overlay) if overlay.exists() else "",
        fused_b64=_img_to_b64(fused) if fused.exists() else "",
        rows="\n".join(rows),
        hm_cards="\n".join(cards),
        ts=str(Path('.').resolve()), conf=rep.get("confidence", 0.0)
    )
    (item/"report.html").write_text(html)
    return str(item/"report.html")

def make_pdf(item_dir):
    # Optional: requires reportlab
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.units import cm
    except Exception as e:
        return None, f"reportlab not available: {e}"
    from PIL import Image
    from pathlib import Path
    item = Path(item_dir)
    rep = json.loads((item/"report.json").read_text())
    pdf_path = item/"report.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=landscape(A4))
    width, height = landscape(A4)
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2*cm, height-1.5*cm, f"Report Forense — {rep['image']}  (score {rep['tamper_score']:.3f} vs thr {rep['threshold']:.3f})")
    # Original image left
    orig = Image.open(item/rep["image"]).convert("RGB")
    ow, oh = orig.size
    maxw, maxh = 12*cm, 8*cm
    scale = min(maxw/ow, maxh/oh, 1.0)
    orig = orig.resize((int(ow*scale), int(oh*scale)))
    tmp_orig = item/"_orig_tmp.png"
    orig.save(str(tmp_orig))
    c.drawInlineImage(str(tmp_orig), 2*cm, height-10*cm)
    # Fused heatmap and overlay
    fused = item / rep["artifacts"].get("fused_heatmap","")
    overlay = item / rep["artifacts"].get("overlay","")
    y0 = height-10*cm
    x0 = 2*cm + maxw + 1*cm
    if fused.exists():
        c.drawString(x0, y0+8.2*cm, "Fused heatmap")
        c.drawInlineImage(str(fused), x0, y0, width=8*cm, height=6*cm)
    if overlay.exists():
        c.drawString(x0, y0-0.5*cm, "Overlay")
        c.drawInlineImage(str(overlay), x0, y0-6.5*cm, width=8*cm, height=6*cm)
    # New page for per-check scores
    c.showPage()
    c.setFont("Helvetica-Bold", 14); c.drawString(2*cm, height-1.5*cm, "Dettaglio per controllo")
    c.setFont("Helvetica", 10)
    y = height-2.5*cm
    for name, v in rep["per_check"].items():
        line = f"{name:<18} score={v['score'] if v['score'] is not None else ''}  thr={v['threshold']:.3f}  flag={v['flag']}"
        c.drawString(2*cm, y, line); y -= 0.6*cm
        if y < 2*cm:
            c.showPage(); y = height-2.5*cm; c.setFont("Helvetica", 10)
    c.save()
    return str(pdf_path), None
