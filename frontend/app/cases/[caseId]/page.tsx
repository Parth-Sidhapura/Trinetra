"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, getHealth } from "@/lib/api";
import Shell from "@/components/Shell";
import {
  Badge, Label, Note, Spinner, ErrorBox, Empty, Tabs,
  ScoreBreakdown, SpineCard, Seal, Dot,
} from "@/components/ui";
import GraphExplorer, { TYPE_COLOR, TYPE_TAG } from "@/components/GraphExplorer";
import MapView from "@/components/MapView";
import { canWrite } from "@/lib/perms";
import type { Anomaly, Candidate, EvidenceRow, GraphData, Lead } from "@/lib/types";

const pct = (n: number) => `${Math.round((n ?? 0) * 100)}%`;
const sev = (c: number) => (c >= 0.8 ? "alarm" : c >= 0.6 ? "brass" : "faint");
const sevWord = (c: number) => (c >= 0.8 ? "high" : c >= 0.6 ? "medium" : "low");

/* ==================================================== the paper moment */
function PaperTrace({ lineage }: { lineage: any }) {
  const stages: any[] = lineage?.chain || [];
  const obs = stages.flatMap((s) => s.items || [])
                    .find((it: any) => it?.raw_text);
  const src = stages.flatMap((s) => s.items || [])
                    .find((it: any) => it?.filename);

  return (
    <div className="animate-rise">
      {obs && (
        <div className="paper">
          <div className="paper-h">
            <span>{src?.filename || "source document"}</span>
            <span>{obs.page ? `page ${obs.page}` : "extracted span"}</span>
          </div>
          …<mark>{obs.raw_text}</mark>{" "}
          {obs.entity_type ? `— recorded as ${obs.entity_type.toLowerCase()}` : ""}
          {obs.extraction_method ? `, extracted by ${obs.extraction_method}` : ""}…
        </div>
      )}

      <div className="mt-3 space-y-2.5">
        {stages.map((stage: any, i: number) => (
          <div key={`st-${i}`} className="border-l-2 border-brass/40 pl-2.5">
            <p className="lbl !text-brass/80">{stage.stage}</p>
            {(stage.items || []).slice(0, 4).map((it: any, j: number) => (
              <p key={`it-${i}-${j}`} className="text-[11px] text-txt/70 truncate">
                {it.filename || it.raw_text || it.name ||
                  (it.investigative_priority !== undefined
                    ? `priority ${it.investigative_priority}`
                    : JSON.stringify(it).slice(0, 60))}
                {it.page ? ` (p.${it.page})` : ""}
              </p>
            ))}
          </div>
        ))}
      </div>

      <p className="text-[10.5px] text-faint leading-relaxed mt-3">
        Every score walks backward through the exact chain it was built forward
        through — observation, resolution, entity, priority.
      </p>
    </div>
  );
}

/* ============================================================ main page */
export default function CasePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [me, setMe] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [tab, setTab] = useState("graph");
  const [detail, setDetail] = useState<any>(null);
  const [evidence, setEvidence] = useState<EvidenceRow[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [lineage, setLineage] = useState<any>(null);
  const [verify, setVerify] = useState<any>(null);
  const [verifying, setVerifying] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState("");
  const [until, setUntil] = useState("");
  const [mapData, setMapData] = useState<any>(null);
  const [cy, setCy] = useState<any>(null);
  const [rewind, setRewind] = useState(false);
  const [edgeLabels, setEdgeLabels] = useState(false);

  const load = useCallback(async () => {
    try {
      const [d, ev, cand, an] = await Promise.all([
        api(`/cases/${caseId}`),
        api<EvidenceRow[]>(`/cases/${caseId}/evidence`),
        api<Candidate[]>(`/cases/${caseId}/resolution/candidates`),
        api<Anomaly[]>(`/cases/${caseId}/anomalies`),
      ]);
      setDetail(d); setEvidence(ev); setCandidates(cand); setAnomalies(an);
    } catch (e: any) { setErr(e.message); }
  }, [caseId]);

  useEffect(() => {
    load();
    api("/admin/me").then(setMe).catch(() => {});
    getHealth().then(setHealth).catch(() => {});
  }, [load]);

  const loadGraph = useCallback(async (ts?: string) => {
    const qs = ts ? `?until=${encodeURIComponent(ts)}` : "";
    try { setGraph(await api<GraphData>(`/cases/${caseId}/graph${qs}`)); }
    catch (e: any) { setErr(e.message); }
  }, [caseId]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  useEffect(() => {
    if (tab === "map" && !mapData)
      api(`/cases/${caseId}/graph/map`).then(setMapData).catch(() => {});
  }, [tab, caseId, mapData]);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setBusy(`uploading ${files.length} file(s)`);
    try {
      for (const file of Array.from(files)) {
        const fd = new FormData();
        fd.append("file", file);
        await api(`/cases/${caseId}/evidence`, { method: "POST", body: fd });
      }
      setBusy("quarantine → scan → hash-chain → parse → extract");
      setTimeout(() => { load(); setBusy(""); }, 3000);
    } catch (e: any) { setErr(e.message); setBusy(""); }
  }

  async function decide(id: string, decision: "confirm" | "reject") {
    try {
      await api(`/cases/${caseId}/resolution/candidates/${id}`, {
        method: "POST", body: JSON.stringify({ decision }),
      });
      load(); loadGraph(until || undefined);
    } catch (e: any) { setErr(e.message); }
  }

  const pickNode = useCallback(async (id: string) => {
    setLineage(null);
    try { setSelected(await api(`/cases/${caseId}/entities/${id}`)); }
    catch (e: any) { setErr(e.message); }
  }, [caseId]);

  async function runVerify() {
    setVerifying(true); setTab("evidence");
    try { setVerify(await api(`/cases/${caseId}/evidence/verify`)); }
    catch (e: any) { setErr(e.message); }
    finally { setVerifying(false); }
  }

  const critical = anomalies.filter((a) => a.anomaly_confidence >= 0.8).length;
  const present = Array.from(new Set((graph?.nodes || [])
    .map((n: any) => n.data.type))).filter(Boolean) as string[];

  const tabs = [
    { id: "graph", label: "Network" },
    { id: "evidence", label: "Evidence", count: evidence.length },
    { id: "resolution", label: "Review", count: candidates.length },
    { id: "anomalies", label: "Anomalies", count: anomalies.length },
    { id: "map", label: "Geospatial" },
    { id: "leads", label: "Leads" },
    { id: "copilot", label: "Copilot" },
  ];

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const paneCls = "absolute inset-0 z-20 overflow-y-auto bg-ink/[.94] " +
                  "backdrop-blur-sm pt-[78px] px-4 md:px-6 pb-10";

  return (
    <Shell me={me} health={health} bare>
      <div className="relative flex-1 min-h-0 overflow-hidden">
        {/* ------------------------------------------------------- canvas */}
        <div className="absolute inset-0 gridfield" style={{
          background:
            "radial-gradient(1100px 620px at 62% 34%,rgba(63,191,168,.07),transparent 62%)," +
            "radial-gradient(800px 500px at 20% 78%,rgba(200,150,62,.06),transparent 60%)," +
            "#090E15",
        }} />
        {graph
          ? <GraphExplorer data={graph} onSelect={pickNode} onReady={setCy}
                           edgeLabels={edgeLabels}
                           className="absolute left-0 right-0 top-[56px] bottom-0 xl:right-[330px]" />
          : <div className="absolute inset-0 grid place-items-center">
              <Spinner label="building the network" />
            </div>}

        {/* --------------------------------------------------------- tabs */}
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 max-w-[94vw]">
          <Tabs tabs={tabs} active={tab} onChange={setTab} floating />
        </div>

        {/* ------------------------------------------------- case identity */}
        <div className="float absolute top-4 left-4 z-10 px-4 py-3 max-w-[min(46%,420px)]
                        max-lg:hidden">
          <Link href="/dashboard" className="lbl hover:text-brasslit transition-colors">
            ← Register
          </Link>
          <h1 className="disp text-[19px] leading-tight my-1.5 truncate">
            {detail?.title || "Case"}
          </h1>
          <div className="flex gap-1.5 flex-wrap">
            {detail && (<>
              <Badge>{detail.bnss_stage}</Badge>
              <Badge tone="brass">{detail.data_classification}</Badge>
              {detail.firs?.map((f: any, fi: number) => (
                <Badge key={`fir-${f.id}-${fi}`} tone="violet">{f.fir_number}</Badge>
              ))}
            </>)}
          </div>
        </div>

        {/* ----------------------------------------------------- actions */}
        <div className="float absolute top-4 right-4 z-10 p-2 flex gap-1.5 flex-wrap
                        max-w-[46vw] max-lg:top-auto max-lg:bottom-4">
          <button onClick={runVerify} disabled={verifying}
                  className="btn !border-verd/45 !text-verd hover:!bg-verd/10 text-[12.5px]">
            {verifying ? "verifying…" : "◈ Verify integrity"}
          </button>
          <button onClick={() => setEdgeLabels((v) => !v)}
                  className={`btn text-[12.5px] ${edgeLabels
                    ? "!border-brass/60 !text-brasslit !bg-brass/10" : ""}`}>
            Link names
          </button>
          <button onClick={() => setRewind((v) => !v)} className="btn text-[12.5px]">
            Rewind
          </button>
          <a className="btn text-[12.5px]" target="_blank" rel="noreferrer"
             href={`${API}/cases/${caseId}/reports/brief`}>Brief</a>
          {canWrite(me) && (
            <a className="btn text-[12.5px]" target="_blank" rel="noreferrer"
               href={`${API}/cases/${caseId}/reports/bsa-certificate`}>BSA §63</a>
          )}
        </div>

        {rewind && (
          <div className="float absolute top-[92px] right-4 z-30 p-3.5 w-[280px] animate-rise">
            <Label className="mb-2">Rebuild the network as it stood at</Label>
            <input type="datetime-local" value={until}
                   onChange={(e) => { setUntil(e.target.value); loadGraph(e.target.value); }}
                   className="input mono !text-[11px] mb-2" />
            <div className="flex gap-1.5">
              <button onClick={() => { setUntil(""); loadGraph(); }}
                      className="btn text-[11.5px]">Now</button>
              {canWrite(me) && (
                <button onClick={() => api(`/cases/${caseId}/graph/sync`, { method: "POST" })
                          .then(() => loadGraph(until || undefined)).catch((e) => setErr(e.message))}
                        className="btn text-[11.5px]">Sync → Neo4j</button>
              )}
              <button onClick={() => cy?.fit(undefined, 50)} className="btn text-[11.5px]">Fit</button>
            </div>
            <p className="text-[10.5px] text-faint leading-relaxed mt-2.5">
              Nothing is deleted to produce this — the graph is re-derived from the
              observations that existed at that moment.
            </p>
          </div>
        )}

        {/* ------------------------------------------------------- legend */}
        {tab === "graph" && graph && (
          <div className="float absolute bottom-4 left-4 z-10 px-3.5 py-2.5
                          max-w-[min(52%,520px)] max-lg:hidden">
            <Label className="mb-1.5">Entity types present</Label>
            <div className="flex gap-3 flex-wrap">
              {present.map((t) => (
                <span key={t} className="flex items-center gap-1.5 mono text-mute">
                  <i className="w-1.5 h-1.5 rounded-full"
                     style={{ background: TYPE_COLOR[t] || "#6C819A" }} />
                  <b className="text-txt/80">{TYPE_TAG[t] || "ENT"}</b>
                  {t.toLowerCase()}
                </span>
              ))}
            </div>
            <p className="lbl mt-2 leading-relaxed">
              node size = degree centrality · dashed = proposed, not confirmed ·
              hover a node for its full value · tap one to name its links
            </p>
          </div>
        )}

        {/* -------------------------------------------------------- counts */}
        {tab === "graph" && graph && (
          <div className="float absolute bottom-4 right-4 z-10 px-4 py-2.5 flex gap-5
                          max-lg:hidden">
            {[["nodes", graph.counts.nodes], ["edges", graph.counts.edges],
              ["version", graph.graph_version],
              ["alerts", anomalies.length]].map(([k, v]: any) => (
              <div key={k}>
                <p className="lbl">{k}</p>
                <p className={`mono text-[15px] num ${k === "alerts" && critical
                  ? "text-alarmlit" : "text-txt"}`}>{v}</p>
              </div>
            ))}
          </div>
        )}

        {/* --------------------------------------------------- inspector */}
        {tab === "graph" && (
          <aside className="absolute top-0 right-0 bottom-0 w-[330px] z-[15] p-[18px]
                            overflow-y-auto border-l border-rule
                            bg-[rgba(12,18,26,.9)] backdrop-blur-lg
                            max-xl:hidden">
            {selected ? (
              <div className="animate-rise">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <Label>{selected.type}</Label>
                    <h3 className="disp text-[20px] leading-tight mt-1">{selected.name}</h3>
                    {selected.aliases?.length > 0 && (
                      <p className="text-[12px] text-mute mt-1">
                        also seen as {selected.aliases.join(" · ")}
                      </p>
                    )}
                  </div>
                  <button onClick={() => { setSelected(null); setLineage(null); }}
                          className="text-faint hover:text-txt text-[18px] leading-none">×</button>
                </div>

                <div className="border-t border-rule mt-4 pt-4">
                  <ScoreBreakdown total={selected.priority.investigative_priority}
                                  components={selected.priority.components}
                                  disclaimer={selected.priority.disclaimer} />
                </div>

                {selected.criminal_history?.length > 0 && (
                  <div className="border-t border-rule mt-4 pt-3.5">
                    <Label className="mb-1.5">Prior records</Label>
                    {selected.criminal_history.map((h: any, i: number) => (
                      <p key={`ch-${i}`} className="mono text-txt/80">
                        {h.case_ref} — <span className="text-brasslit">{h.offense_type}</span>
                      </p>
                    ))}
                  </div>
                )}

                <div className="border-t border-rule mt-4 pt-3.5">
                  {!lineage ? (
                    <button className="btn w-full text-[12.5px]"
                      onClick={async () => {
                        try {
                          setLineage(await api(
                            `/cases/${caseId}/entities/${selected.id}/lineage`));
                        } catch (e: any) { setErr(e.message); }
                      }}>
                      ⟲ Trace this back to the page it came from
                    </button>
                  ) : (
                    <>
                      <div className="flex items-center justify-between mb-2.5">
                        <Label>Traced to source</Label>
                        <button onClick={() => setLineage(null)}
                                className="lbl hover:text-txt">close</button>
                      </div>
                      <PaperTrace lineage={lineage} />
                    </>
                  )}
                </div>

                <div className="border-t border-rule mt-4 pt-3.5">
                  <Label className="mb-2">Connections · {selected.relationships.length}</Label>
                  <div className="space-y-px">
                    {selected.relationships.slice(0, 40).map((r: any, ri: number) => (
                      <button key={`rel-${r.id}-${ri}`} onClick={() => pickNode(r.other_id)}
                              className="flex items-center gap-2 w-full text-left px-1.5 py-1
                                         rounded hover:bg-white/[.06] transition-colors group">
                        <span className="text-faint mono text-[11px]">
                          {r.direction === "out" ? "→" : "←"}
                        </span>
                        <span className="font-mono text-[9.5px] text-violet">{r.type}</span>
                        <span className="text-[12px] text-txt/80 truncate
                                         group-hover:text-brasslit transition-colors">{r.other}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full grid place-items-center text-center px-2">
                <div>
                  <p className="disp text-[15px] text-txt/60">Nothing selected</p>
                  <p className="text-[12px] text-mute mt-2 leading-relaxed">
                    Tap any node to isolate its neighbourhood and open its scored
                    profile — then trace the score back to the page it came from.
                  </p>
                </div>
              </div>
            )}
          </aside>
        )}

        {/* -------------------------------------------------------- alerts */}
        {(err || busy) && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-40 w-[min(560px,90vw)]">
            {err && <ErrorBox error={err} />}
            {busy && (
              <div className="float scanline px-4 py-2.5 mt-2">
                <p className="mono text-brasslit">{busy}…</p>
              </div>
            )}
          </div>
        )}

        {/* ==================================================== EVIDENCE */}
        {tab === "evidence" && (
          <div className={paneCls}>
            <div className="max-w-5xl mx-auto space-y-3.5">
              {verify && <Seal verify={verify} onClose={() => setVerify(null)} />}

              <div className="slab p-4">
                <Label className="mb-2">Ingest case files</Label>
                {canWrite(me) ? (
                  <>
                    <input type="file" multiple onChange={(e) => upload(e.target.files)}
                           className="text-[13px] text-txt/80 file:btn-pri file:mr-3 file:cursor-pointer" />
                    <p className="text-[11.5px] text-faint mt-2.5 leading-relaxed max-w-2xl">
                      PDF · CSV · XLSX · TXT · audio. Every file is quarantined, type-validated,
                      malware-scanned locally, SHA-256 hash-chained into the ledger, then parsed
                      and extracted. Nothing leaves the deployment boundary.
                    </p>
                  </>
                ) : (
                  <p className="text-[12.5px] text-faint leading-relaxed max-w-2xl">
                    Your account can read this ledger but not add to it. Filing
                    evidence requires Inspector rank or above — and the file
                    would be hash-chained under that officer&apos;s name.
                  </p>
                )}
              </div>

              <div className="slab p-4">
                <Label className="mb-3">Evidence ledger</Label>
                {evidence.length === 0 ? (
                  <Empty title="No files ingested" hint="Upload above to start the chain." />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-[12.5px]">
                      <thead>
                        <tr className="border-b border-rule text-left">
                          {["seq", "file", "status", "scan", "size", "sha-256"].map((h) => (
                            <th key={h} className="lbl py-2 pr-3">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {evidence.map((e, ei) => (
                          <tr key={`ev-${e.id}-${ei}`} className="border-b border-white/[.05] hover:bg-white/[.04]">
                            <td className="py-2.5 pr-3 mono text-faint num">{e.sequence_number}</td>
                            <td className="py-2.5 pr-3 text-txt/90">{e.filename}</td>
                            <td className="py-2.5 pr-3">
                              <Badge tone={e.processing_status === "done" ? "verd"
                                : e.processing_status === "failed" ? "alarm" : "brass"}>
                                {e.processing_status}
                              </Badge>
                            </td>
                            <td className="py-2.5 pr-3 mono text-verd">{e.scan_result}</td>
                            <td className="py-2.5 pr-3 mono text-mute num">
                              {(e.size_bytes / 1024).toFixed(0)} KB
                            </td>
                            <td className="py-2.5 font-mono text-[10px] text-faint">
                              {e.sha256.slice(0, 18)}…
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <p className="text-[11.5px] text-faint mt-3.5 leading-relaxed max-w-2xl">
                  Each record&apos;s hash includes the previous record&apos;s hash. Altering any
                  file — or any row in the audit log — changes every hash after it, so
                  tampering cannot be silent.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ================================================== RESOLUTION */}
        {tab === "resolution" && (
          <div className={paneCls}>
            <div className="max-w-4xl mx-auto space-y-3">
              <Note>
                <b>The system proposes. A human decides.</b> Nothing is ever auto-merged —
                an investigator confirms every identity match, and that decision is written
                to the hash-chained audit log with their name against it.
                {!canWrite(me) && " You are signed in with read-only access, so you can " +
                  "see what is pending but not decide it."}
              </Note>

              {candidates.length === 0 ? (
                <Empty title="The review queue is clear"
                       hint="New candidates appear as evidence is ingested and resolved." />
              ) : candidates.map((c, ci) => (
                <SpineCard key={`cand-${c.id}-${ci}`} tone={c.resolution_confidence >= 0.93 ? "verd" : "brass"}
                           className="p-4 animate-rise">
                  <div className="flex gap-5 flex-wrap items-start">
                    <div className="flex-1 min-w-[260px]">
                      <div className="flex items-center gap-3.5 flex-wrap mb-2.5">
                        <span className="disp text-[17px] text-brasslit">{c.a?.raw_text}</span>
                        <span className="mono text-faint">— same {(c.a?.entity_type || "entity").toLowerCase()}? —</span>
                        <span className="disp text-[17px] text-brasslit">{c.b?.raw_text}</span>
                      </div>
                      <p className="text-[12.5px] text-mute leading-relaxed mb-2.5">{c.reasoning}</p>
                      <div className="flex gap-1.5 flex-wrap">
                        <Badge tone="violet">{c.method}</Badge>
                        <Badge tone={c.resolution_confidence >= 0.93 ? "verd" : "brass"}>
                          {pct(c.resolution_confidence)} resolution confidence
                        </Badge>
                        <Badge>{c.a?.entity_type}</Badge>
                        {c.a?.page && <Badge>p.{c.a.page}</Badge>}
                      </div>
                    </div>
                    {canWrite(me) ? (
                      <div className="flex gap-2">
                        <button onClick={() => decide(c.id, "confirm")} className="btn-pri">
                          Confirm merge
                        </button>
                        <button onClick={() => decide(c.id, "reject")} className="btn">
                          Not the same
                        </button>
                      </div>
                    ) : (
                      <p className="text-[11.5px] text-faint max-w-[180px] leading-relaxed">
                        Only an Inspector can decide this match. The decision is
                        recorded under their name.
                      </p>
                    )}
                  </div>
                </SpineCard>
              ))}
            </div>
          </div>
        )}

        {/* =================================================== ANOMALIES */}
        {tab === "anomalies" && (
          <div className={paneCls}>
            <div className="max-w-4xl mx-auto space-y-3">
              <div className="flex gap-3 items-center flex-wrap">
                <div className="flex-1 min-w-[260px]">
                  <Note>
                    Patterns that <b>warrant verification</b> — never proof. Each carries the
                    detector that produced it and the precision of the source it read.
                  </Note>
                </div>
                {canWrite(me) && (
                  <button className="btn text-[12.5px]"
                    onClick={() => api(`/cases/${caseId}/anomalies/run`, { method: "POST" })
                      .then(load).catch((e) => setErr(e.message))}>Re-run detectors</button>
                )}
              </div>

              {anomalies.length === 0 ? (
                <Empty title="No anomalies detected"
                       hint="Run the detectors after ingesting evidence." />
              ) : anomalies.slice()
                  .sort((a, b) => b.anomaly_confidence - a.anomaly_confidence)
                  .map((a, ai) => (
                <SpineCard key={`an-${a.id}-${ai}`} tone={sev(a.anomaly_confidence)} className="p-4 animate-rise">
                  <div className="flex items-center gap-2.5 flex-wrap mb-2.5">
                    <span className={`font-mono text-[10px] uppercase tracking-[.14em]
                      ${a.anomaly_confidence >= 0.8 ? "text-alarmlit"
                        : a.anomaly_confidence >= 0.6 ? "text-brasslit" : "text-faint"}`}>
                      {sevWord(a.anomaly_confidence)} confidence
                    </span>
                    <Badge tone={a.kind === "financial" ? "brass"
                      : a.kind === "temporal" ? "violet" : "verd"}>{a.kind}</Badge>
                    <Badge>{pct(a.anomaly_confidence)}</Badge>
                    {a.source_precision && a.source_precision !== "n/a" && (
                      <Badge tone="brass">source: {a.source_precision}</Badge>
                    )}
                  </div>
                  <h3 className="disp text-[16px] mb-1.5">{a.title}</h3>
                  <p className="text-[12.5px] text-mute leading-relaxed mb-2.5">{a.description}</p>
                  <p className="font-mono text-[10.5px] text-faint">
                    {a.entities.map((e) => e.name).join(" · ")} — detector{" "}
                    {a.detector.name} v{a.detector.version}
                  </p>
                  {a.disclaimer && (
                    <p className="text-[11px] text-faint leading-relaxed mt-2.5 pl-[9px]
                                  border-l-2 border-rule">{a.disclaimer}</p>
                  )}
                </SpineCard>
              ))}
            </div>
          </div>
        )}

        {/* ========================================================= MAP */}
        {tab === "map" && (
          <div className={paneCls}>
            <div className="max-w-5xl mx-auto space-y-3.5">
              <Note>
                <b>Source precision is rendered, not hidden.</b> GPS fixes appear as precise
                points. Cell-tower associations appear as coverage areas — tower data cannot
                support a point-level location claim, so the map never draws one.
              </Note>
              {mapData ? <MapView data={mapData} /> : <Spinner label="loading geospatial layer" />}
              {mapData?.colocations?.length > 0 && (
                <div className="slab p-4">
                  <Label className="mb-2">Co-location findings</Label>
                  {mapData.colocations.map((c: any, li: number) => (
                    <div key={`colo-${c.id}-${li}`} className="border-t border-rule py-2.5 first:border-0 first:pt-0">
                      <Badge tone={c.precision === "gps" ? "steel" : "brass"}>{c.precision}</Badge>
                      <p className="text-[12.5px] text-txt/85 mt-1.5">{c.title}</p>
                      <p className="font-mono text-[10.5px] text-faint">{c.entities.join(" · ")}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {tab === "leads" && (
          <div className={paneCls}>
            <LeadsPanel caseId={caseId} leads={leads} setLeads={setLeads} />
          </div>
        )}

        {tab === "copilot" && (
          <div className={paneCls}><CopilotPanel caseId={caseId} /></div>
        )}
      </div>
    </Shell>
  );
}

/* ================================================== investigative leads */
function LeadsPanel({ caseId, leads, setLeads }: any) {
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    api<Lead[]>(`/cases/${caseId}/graph/leads`).then(setLeads).catch(() => {});
  }, [caseId, setLeads]);

  return (
    <div className="max-w-4xl mx-auto space-y-3">
      <Note>
        <b>A separate layer from confirmed knowledge.</b> An Adamic-Adar score is a
        structural similarity measure, <b>not</b> a calibrated probability — it is never
        phrased as a percentage likelihood, and never written into the confirmed graph
        or an evidence-linked report.
      </Note>

      <button className="btn text-[12.5px]"
        onClick={() => { setLoading(true);
          api<Lead[]>(`/cases/${caseId}/graph/leads?refresh=true`)
            .then(setLeads).finally(() => setLoading(false)); }}>
        {loading ? "computing…" : "Recompute predictions"}
      </button>

      {leads.length === 0 ? (
        <Empty title="No leads yet" hint="Link prediction needs a denser confirmed graph." />
      ) : (
        <div className="grid md:grid-cols-2 gap-3">
          {leads.map((l: Lead, li: number) => (
            <SpineCard key={`lead-${l.id}-${li}`} tone="brass" className="p-4">
              <div className="flex items-center gap-3 flex-wrap mb-3">
                <span className="disp text-[15px]">{l.source.name}</span>
                <span className="font-mono text-[10px] text-brasslit">⇠ unobserved ⇢</span>
                <span className="disp text-[15px]">{l.target.name}</span>
              </div>
              <dl className="font-mono text-[11.5px] space-y-1 text-mute">
                {[["link prediction", l.link_prediction_score], ["method", l.method],
                  ["status", l.status], ["evidence", l.evidence]].map(([k, v]: any, di: number) => (
                  <div key={`ld-${k}-${di}`} className="flex gap-2">
                    <dt className="w-[124px] text-faint">{k}</dt>
                    <dd className={k === "link prediction" ? "text-brasslit num" : "text-txt/75"}>{v}</dd>
                  </div>
                ))}
              </dl>
            </SpineCard>
          ))}
        </div>
      )}
    </div>
  );
}

/* ============================================================= copilot */
function CopilotPanel({ caseId }: { caseId: string }) {
  const [q, setQ] = useState("");
  const [history, setHistory] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);

  const SUGGESTED = [
    "Summarise how the entities in this case connect.",
    "What evidence links the highest-priority person to a bank account?",
    "Which findings rest on cell-tower data rather than GPS?",
  ];

  async function ask(question: string) {
    if (!question.trim() || busy) return;
    setQ(""); setBusy(true);
    try {
      const r = await api(`/cases/${caseId}/copilot`, {
        method: "POST", body: JSON.stringify({ question }),
      });
      setHistory((h) => [...h, { question, ...r }]);
    } catch (e: any) {
      setHistory((h) => [...h, { question, answer: `Error: ${e.message}`, citations: [] }]);
    } finally { setBusy(false); }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-3">
      <Note tone="verd">
        Grounded Q&amp;A. Authorization runs <b>before</b> retrieval — the model never
        decides access. Every citation is validated against the retrieved evidence set;
        an answer citing something that doesn&apos;t exist is <b>blocked</b>.
      </Note>

      {history.length === 0 && (
        <div className="flex gap-2 flex-wrap">
          {SUGGESTED.map((s) => (
            <button key={s} onClick={() => ask(s)}
                    className="btn text-[12px] text-left max-w-full">{s}</button>
          ))}
        </div>
      )}

      {history.map((h, i) => (
        <div key={i} className="slab p-4 animate-rise">
          <p className="disp text-[15px] text-brasslit mb-2.5">▸ {h.question}</p>
          <p className="text-[13.5px] leading-[1.68] whitespace-pre-wrap">{h.answer}</p>
          {h.blocked && (
            <div className="mt-2.5"><Badge tone="alarm">BLOCKED — invalid citation</Badge></div>
          )}
          {h.citations?.length > 0 && (
            <div className="border-t border-rule mt-3.5 pt-2.5">
              <Label className="mb-1.5">Cited evidence</Label>
              {h.citations.map((c: any, ki: number) => (
                <p key={`cite-${c.ref}-${ki}`} className="mono text-mute">
                  <span className="text-brasslit">[{c.ref}]</span> {c.kind} —{" "}
                  {c.name || c.filename || c.id?.slice(0, 8)}
                </p>
              ))}
            </div>
          )}
        </div>
      ))}

      {busy && <Spinner label="retrieving under your clearance" />}

      <form onSubmit={(e) => { e.preventDefault(); ask(q); }} className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)}
               placeholder="Ask about this case — grounded in its evidence only"
               className="input flex-1" />
        <button disabled={busy} className="btn-pri">{busy ? "…" : "Ask"}</button>
      </form>
    </div>
  );
}
