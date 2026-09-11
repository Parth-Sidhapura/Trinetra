"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getHealth } from "@/lib/api";
import { Wordmark } from "@/components/Shell";
import { Dot } from "@/components/ui";

const PILLARS = [
  ["Confirmed knowledge",
   "Every node traces back to a specific page of a specific file. Nothing enters the graph without a source."],
  ["Investigative leads",
   "Structural predictions live in their own layer, and are never phrased as a probability of guilt."],
  ["Tamper-evident",
   "A SHA-256 hash chain and Merkle tree cover both the evidence and the audit log that records who looked at it."],
];

export default function Home() {
  const [health, setHealth] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { getHealth().then(setHealth).catch((e) => setErr(e.message)); }, []);

  const rows = health ? [
    { k: "api", v: health.api, ok: health.api === "ok" },
    { k: "postgres", v: health.postgres, ok: health.postgres === "ok" },
    { k: "neo4j", v: health.neo4j, ok: health.neo4j === "ok" || health.neo4j === "disabled" },
  ] : [];

  return (
    <main className="min-h-screen flex items-center justify-center px-4 md:px-6 py-12">
      <div className="w-full max-w-4xl animate-rise">
        <div className="mb-10"><Wordmark size={28} /></div>

        <p className="lbl mb-3">Smart India Hackathon 2026 · PS 26189 · Team 243</p>
        <h1 className="disp text-[clamp(30px,5.4vw,52px)] leading-[1.04] mb-4">
          Scattered case files,
          <br /><span className="text-brasslit">one defensible network.</span>
        </h1>
        <p className="text-mute text-[15px] leading-relaxed max-w-xl mb-9">
          FIRs, call records, bank statements and seizure memos become a single
          investigative graph — where every inference can be walked back to the page
          it came from, and no two identities are ever merged without an officer
          saying so.
        </p>

        <div className="grid md:grid-cols-3 gap-3 mb-9">
          {PILLARS.map(([k, v]) => (
            <div key={k} className="slab p-4 border-t-2 border-t-brass/50">
              <p className="semi text-[13.5px] text-brasslit mb-1.5">{k}</p>
              <p className="text-[12.5px] text-mute leading-relaxed">{v}</p>
            </div>
          ))}
        </div>

        <div className="slab p-5 flex flex-wrap items-center gap-x-8 gap-y-4">
          <div>
            <p className="lbl mb-2.5">System check</p>
            {err && <p className="mono text-alarmlit">backend unreachable — {err}</p>}
            {!health && !err && <p className="mono text-faint">probing…</p>}
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              {rows.map((r) => (
                <span key={r.k} className="flex items-center gap-2 mono text-txt/80">
                  <Dot tone={r.ok ? "verd" : "alarm"} /> {r.k}{" "}
                  <span className="text-faint">{r.v}</span>
                </span>
              ))}
            </div>
          </div>
          <Link href="/login" className="btn-pri ml-auto">Sign in to the console →</Link>
        </div>
      </div>
    </main>
  );
}
