"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { api, getHealth } from "@/lib/api";
import Shell from "@/components/Shell";
import { Badge, Metric, MetricRow, Spinner, ErrorBox, Empty } from "@/components/ui";
import { canWrite } from "@/lib/perms";
import type { Case } from "@/lib/types";

/** Proportion of a case's record types — real counts, drawn to scale. */
function Composition({ c }: { c: Case }) {
  const ev = c.counts?.evidence ?? 0;
  const en = c.counts?.entities ?? 0;
  const li = c.counts?.relationships ?? 0;
  const total = ev + en + li;
  if (!total) return <div className="h-[6px] rounded-sm bg-white/[.06]" />;
  const seg = [
    { w: (ev / total) * 100, c: "#3FBFA8" },
    { w: (en / total) * 100, c: "#E8B65E" },
    { w: (li / total) * 100, c: "#9C8CF0" },
  ];
  return (
    <div>
      <div className="flex h-[6px] rounded-sm overflow-hidden gap-px">
        {seg.map((s, i) => (
          <span key={`seg-${i}`} style={{ width: `${s.w}%`, background: s.c }} />
        ))}
      </div>
      <p className="lbl mt-2">evidence · entities · links</p>
    </div>
  );
}

export default function Dashboard() {
  const router = useRouter();
  const [me, setMe] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [cases, setCases] = useState<Case[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  async function load() {
    try {
      const [profile, list] = await Promise.all([api("/admin/me"), api<Case[]>("/cases")]);
      setMe(profile);
      setCases(list);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) router.push("/login");
      else { load(); getHealth().then(setHealth).catch(() => {}); }
    });
  }, [router]);

  async function createCase(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || creating) return;
    setCreating(true);
    try {
      const c = await api<Case>("/cases", {
        method: "POST", body: JSON.stringify({ title: title.trim() }),
      });
      setTitle("");
      if (c?.id) router.push(`/cases/${c.id}`); else load();
    } catch (e: any) { setErr(e.message); }
    finally { setCreating(false); }
  }

  const totals = cases.reduce(
    (a, c) => ({
      evidence: a.evidence + (c.counts?.evidence || 0),
      entities: a.entities + (c.counts?.entities || 0),
      links: a.links + (c.counts?.relationships || 0),
    }), { evidence: 0, entities: 0, links: 0 });

  const maxEv = Math.max(1, ...cases.map((c) => c.counts?.evidence || 0));

  return (
    <Shell me={me} health={health}>
      {/* ---------------------------------------------------------- header */}
      <div className="flex items-end justify-between gap-5 flex-wrap mb-5">
        <div>
          <p className="lbl">Case register</p>
          <h1 className="disp text-[30px] leading-[1.05] mt-1.5">Active investigations</h1>
        </div>
        {canWrite(me) ? (
          <form onSubmit={createCase} className="flex gap-2 flex-wrap grow sm:grow-0
                                                 sm:w-[420px] max-w-full">
            <input value={title} onChange={(e) => setTitle(e.target.value)}
                   placeholder="Name a new case — e.g. Operation Nexus"
                   className="input flex-1 min-w-[200px]" />
            <button disabled={creating || !title.trim()} className="btn-pri shrink-0">
              {creating ? "opening…" : "+ Open"}
            </button>
          </form>
        ) : (
          <p className="text-[12px] text-faint max-w-xs leading-relaxed
                        border-l-2 border-rule pl-3">
            Your account can read cases but not open them. Opening a case
            requires Inspector rank or above.
          </p>
        )}
      </div>

      {err && <div className="mb-4"><ErrorBox error={err} /></div>}

      {/* ------------------------------------------------------- situation */}
      <div className="grid lg:grid-cols-[minmax(0,1.15fr)_minmax(0,2fr)] gap-3.5 mb-5">
        <div className="slab relative overflow-hidden px-[22px] py-5">
          <span className="pointer-events-none absolute -bottom-24 -right-16 w-56 h-56 rounded-full"
                style={{ background: "radial-gradient(circle,rgba(200,150,62,.16),transparent 68%)" }} />
          <p className="lbl">Open cases</p>
          <p className="disp text-[58px] leading-[.9] text-brasslit num relative">
            {loading ? "—" : cases.length}
          </p>

          {cases.length > 0 && (
            <>
              <div className="flex items-end gap-[5px] h-11 mt-4 relative">
                {cases.map((c, bi) => (
                  <span key={`bar-${c.id}-${bi}`} className="flex-1 rounded-t-[1px]"
                        style={{
                          height: `${Math.max(6, ((c.counts?.evidence || 0) / maxEv) * 100)}%`,
                          background: "linear-gradient(180deg,rgba(200,150,62,.75),rgba(200,150,62,.18))",
                        }}
                        title={`${c.title} — ${c.counts?.evidence ?? 0} evidence records`} />
                ))}
              </div>
              <p className="lbl mt-2.5">Evidence records per case</p>
            </>
          )}
        </div>

        <MetricRow>
          <Metric value={totals.evidence} label="Evidence records" tone="verd"
                  sub="every one hash-chained" />
          <Metric value={totals.entities} label="Canonical entities"
                  sub="resolved from raw observations" />
          <Metric value={totals.links} label="Confirmed relationships" tone="brass"
                  sub="nothing merges without a human" />
        </MetricRow>
      </div>

      {/* ---------------------------------------------------------- register */}
      {loading ? (
        <Spinner label="reading the register" />
      ) : cases.length === 0 ? (
        <Empty title="The register is empty"
               hint="Name a case above to start ingesting evidence." />
      ) : (
        <div className="border border-rule rounded-md overflow-hidden bg-slab">
          <div className="hidden md:grid gap-3.5 px-4 py-2.5 bg-[#0E1620] border-b border-rule"
               style={{ gridTemplateColumns: "34px minmax(0,1fr) 170px 200px 24px" }}>
            <span className="lbl">#</span>
            <span className="lbl">Case</span>
            <span className="lbl">Composition</span>
            <span className="lbl text-right">Evidence / entities / links</span>
            <span />
          </div>

          {cases.map((c, i) => (
            <Link key={`case-${c.id}-${i}`} href={`/cases/${c.id}`}
                  className="group relative grid gap-3.5 items-center px-4 py-3.5
                             border-b border-rule last:border-b-0
                             hover:bg-white/[.045] transition-colors animate-rise
                             grid-cols-1 md:[grid-template-columns:34px_minmax(0,1fr)_170px_200px_24px]"
                  style={{ animationDelay: `${i * 45}ms` }}>
              <span className="absolute left-0 inset-y-0 w-[2px] bg-brass opacity-0
                               group-hover:opacity-100 transition-opacity" />
              <span className="mono text-[11px] text-faint num hidden md:block">
                {String(i + 1).padStart(2, "0")}
              </span>

              <div className="min-w-0">
                <p className="semi text-[15px] truncate group-hover:text-brasslit transition-colors">
                  {c.title}
                </p>
                <div className="flex gap-1.5 flex-wrap mt-1.5">
                  <Badge>{c.bnss_stage}</Badge>
                  <Badge tone="brass">{c.data_classification}</Badge>
                  <Badge tone={c.status === "open" ? "verd" : "slate"}>{c.status}</Badge>
                </div>
              </div>

              <Composition c={c} />

              <div className="flex md:justify-end gap-4">
                {[["ev", c.counts?.evidence ?? 0],
                  ["ent", c.counts?.entities ?? 0],
                  ["links", c.counts?.relationships ?? 0]].map(([k, v]: any, ci: number) => (
                  <div key={`ct-${k}-${ci}`} className="md:text-right">
                    <p className="mono text-[15px] text-txt num">{v}</p>
                    <p className="lbl">{k}</p>
                  </div>
                ))}
              </div>

              <span className="text-faint text-right hidden md:block
                               group-hover:text-brasslit transition-colors">→</span>
            </Link>
          ))}
        </div>
      )}

      <p className="lbl mt-3.5 leading-relaxed max-w-2xl">
        A case is the isolation boundary — evidence, entities and audit records never
        cross between cases, even for an administrator.
      </p>
    </Shell>
  );
}
