"""PDF generation: investigation brief + BSA Section 63 certificate DRAFT.

The certificate is explicitly a generator/draft: it assists the prescribed
certification process, it does NOT itself establish legal admissibility.
Falls back to HTML when WeasyPrint isn't installed (free-tier build weight).
"""
import logging
import platform
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Anomaly, Case, Entity, Evidence, Relationship
from app.services.ingestion import verify_chain

log = logging.getLogger("trinetra.reports")

CSS = """
@page { size: A4; margin: 18mm 16mm; @bottom-center { content: counter(page); font-size: 9pt; color: #666; } }
body { font-family: "DejaVu Sans", sans-serif; font-size: 10pt; color: #111; line-height: 1.45; }
h1 { font-size: 19pt; margin: 0 0 2mm; }
h2 { font-size: 12pt; margin: 7mm 0 2mm; border-bottom: 1px solid #ccc; padding-bottom: 1mm; }
.kicker { font-size: 8pt; letter-spacing: .08em; text-transform: uppercase; color: #666; }
table { width: 100%; border-collapse: collapse; margin: 3mm 0; font-size: 8.5pt; }
th { text-align: left; background: #f2f2f2; padding: 2mm; border: 1px solid #ddd; }
td { padding: 2mm; border: 1px solid #ddd; vertical-align: top; }
.mono { font-family: "DejaVu Sans Mono", monospace; font-size: 7.5pt; word-break: break-all; }
.notice { background: #fff8e1; border-left: 3px solid #f0a500; padding: 3mm 4mm; margin: 4mm 0; font-size: 8.5pt; }
.ok { color: #1a7f37; font-weight: bold; } .bad { color: #b3261e; font-weight: bold; }
"""


def _render(html: str) -> tuple[bytes, str]:
    try:
        from weasyprint import CSS as WCSS, HTML
        pdf = HTML(string=html).write_pdf(stylesheets=[WCSS(string=CSS)])
        return pdf, "application/pdf"
    except Exception as exc:  # noqa: BLE001
        log.warning("WeasyPrint unavailable (%s) - returning HTML", exc)
        return (f"<style>{CSS}</style>{html}").encode(), "text/html"


def _esc(v) -> str:
    return (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def investigation_brief(db: Session, case_id: str,
                        actor: str = "") -> tuple[bytes, str]:
    case = db.query(Case).filter(Case.id == case_id).first()
    entities = db.query(Entity).filter(Entity.case_id == case_id).all()
    rels = (db.query(Relationship)
              .filter(Relationship.case_id == case_id,
                      Relationship.status.in_(["source_observed", "human_confirmed"]))
              .all())
    anomalies = db.query(Anomaly).filter(Anomaly.case_id == case_id).all()
    evidence = (db.query(Evidence).filter(Evidence.case_id == case_id)
                  .order_by(Evidence.sequence_number).all())
    chain = verify_chain(db, case_id)
    name_of = {str(e.id): e.name for e in entities}

    ent_rows = "".join(
        f"<tr><td>{_esc(e.type)}</td><td>{_esc(e.name)}</td>"
        f"<td>{_esc(', '.join(e.aliases or []) or '—')}</td></tr>"
        for e in entities[:80])

    rel_rows = "".join(
        f"<tr><td>{_esc(name_of.get(str(r.source_id), '?'))}</td>"
        f"<td>{_esc(r.type)}</td>"
        f"<td>{_esc(name_of.get(str(r.target_id), '?'))}</td>"
        f"<td>{_esc(r.status)}</td>"
        f"<td>{r.relationship_confidence or 0:.2f}</td></tr>"
        for r in rels[:80])

    anom_rows = "".join(
        f"<tr><td>{_esc(a.kind)}</td><td>{_esc(a.title)}</td>"
        f"<td>{_esc(a.description)}</td>"
        f"<td>{a.anomaly_confidence or 0:.2f}</td></tr>"
        for a in anomalies)

    ev_rows = "".join(
        f"<tr><td>{e.sequence_number}</td><td>{_esc(e.filename)}</td>"
        f"<td class='mono'>{_esc(e.sha256)}</td></tr>" for e in evidence)

    html = f"""
    <p class="kicker">TRINETRA · Investigation Brief · Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}</p>
    <h1>{_esc(case.title if case else 'Case')}</h1>
    <p class="mono">Case ID {_esc(case_id)} · Stage: {_esc(case.bnss_stage if case else '—')}
       · Classification: {_esc(case.data_classification if case else '—')}
       · Prepared by: {_esc(actor or '—')}</p>

    <div class="notice"><b>Nature of this document.</b> This brief summarises
    machine-assisted analysis of the case material listed below. Every
    relationship and score in it is traceable to source evidence. Analytical
    prominence is <b>not</b> a determination of guilt; anomaly flags are
    investigative leads requiring verification.</div>

    <h2>Evidence integrity</h2>
    <p>Hash chain: <span class="{'ok' if chain['chain_valid'] else 'bad'}">
    {'VALID' if chain['chain_valid'] else 'BROKEN at #' + str(chain['broken_at'])}</span>
    · Records: {chain['evidence_count']}</p>
    <p class="mono">Merkle root: {_esc(chain.get('merkle_root') or '—')}</p>
    <table><tr><th>#</th><th>File</th><th>SHA-256</th></tr>{ev_rows}</table>

    <h2>Entities ({len(entities)})</h2>
    <table><tr><th>Type</th><th>Name</th><th>Aliases</th></tr>{ent_rows}</table>

    <h2>Confirmed relationships ({len(rels)})</h2>
    <table><tr><th>Source</th><th>Type</th><th>Target</th><th>Status</th><th>Conf.</th></tr>{rel_rows}</table>

    <h2>Investigative leads — anomalies ({len(anomalies)})</h2>
    <table><tr><th>Type</th><th>Pattern</th><th>Detail</th><th>Conf.</th></tr>{anom_rows}</table>
    """
    return _render(html)


def bsa_section63_certificate(db: Session, case_id: str,
                              actor: str = "") -> tuple[bytes, str]:
    """Bharatiya Sakshya Adhiniyam, 2023 - Section 63 electronic evidence
    certificate DRAFT."""
    case = db.query(Case).filter(Case.id == case_id).first()
    evidence = (db.query(Evidence).filter(Evidence.case_id == case_id)
                  .order_by(Evidence.sequence_number).all())
    chain = verify_chain(db, case_id)

    rows = "".join(
        f"<tr><td>{e.sequence_number}</td><td>{_esc(e.filename)}</td>"
        f"<td>{e.size_bytes or 0}</td>"
        f"<td class='mono'>{_esc(e.sha256)}</td>"
        f"<td class='mono'>{_esc(e.chain_hash)}</td>"
        f"<td>{e.uploaded_at:%Y-%m-%d %H:%M} UTC</td></tr>"
        for e in evidence)

    html = f"""
    <p class="kicker">Draft certificate under Section 63, Bharatiya Sakshya Adhiniyam, 2023</p>
    <h1>Electronic Evidence Certificate <span style="font-size:11pt;color:#888">(DRAFT)</span></h1>

    <div class="notice"><b>This document assists the prescribed certification
    process; it does not itself establish legal admissibility.</b> It is a
    structured aid produced by an automated system, and is not a substitute
    for the certificate required under the Act, nor for the signature of the
    person lawfully authorised to give it.</div>

    <h2>1. Case particulars</h2>
    <table>
      <tr><th>Case title</th><td>{_esc(case.title if case else '—')}</td></tr>
      <tr><th>Case identifier</th><td class="mono">{_esc(case_id)}</td></tr>
      <tr><th>Procedural stage (BNSS)</th><td>{_esc(case.bnss_stage if case else '—')}</td></tr>
      <tr><th>Generated</th><td>{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC</td></tr>
      <tr><th>Generated by</th><td>{_esc(actor or '—')}</td></tr>
    </table>

    <h2>2. System particulars</h2>
    <table>
      <tr><th>Software</th><td>TRINETRA v0.1.0</td></tr>
      <tr><th>Platform</th><td>{_esc(platform.platform())}</td></tr>
      <tr><th>Python runtime</th><td>{_esc(platform.python_version())}</td></tr>
      <tr><th>Integrity scheme</th><td>SHA-256 linear hash chain + Merkle tree</td></tr>
    </table>

    <h2>3. Evidence hash ledger</h2>
    <table>
      <tr><th>#</th><th>File</th><th>Bytes</th><th>SHA-256</th><th>Chain hash</th><th>Received</th></tr>
      {rows}
    </table>

    <h2>4. Integrity verification result</h2>
    <p>Chain verification: <span class="{'ok' if chain['chain_valid'] else 'bad'}">
      {'VALID — no unexpected modification detected' if chain['chain_valid']
        else 'BROKEN at record #' + str(chain['broken_at'])}</span></p>
    <p class="mono">Merkle root: {_esc(chain.get('merkle_root') or '—')}</p>
    <p>Records covered: {chain['evidence_count']}</p>

    <h2>5. Declaration to be completed by the authorised person</h2>
    <table>
      <tr><th style="width:35%">Name</th><td style="height:9mm"></td></tr>
      <tr><th>Designation</th><td style="height:9mm"></td></tr>
      <tr><th>Signature</th><td style="height:13mm"></td></tr>
      <tr><th>Date &amp; place</th><td style="height:9mm"></td></tr>
    </table>
    """
    return _render(html)
