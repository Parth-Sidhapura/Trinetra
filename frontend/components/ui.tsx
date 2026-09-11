"use client";
import React from "react";

/* ================================================================ surfaces */
export function Panel({ children, className = "" }: any) {
  return <div className={`slab ${className}`}>{children}</div>;
}

export function Label({ children, className = "" }: any) {
  return <p className={`lbl ${className}`}>{children}</p>;
}

/* ------------------------------------------------------------------ chips */
const TONES: Record<string, string> = {
  slate:  "",
  brass:  "!border-brass/45 !text-brasslit bg-brass/[.09]",
  verd:   "!border-verd/45 !text-verd bg-verd/[.09]",
  alarm:  "!border-alarm/50 !text-alarmlit bg-alarm/10",
  violet: "!border-violet/45 !text-violet bg-violet/[.09]",
  steel:  "!border-steel/45 !text-steel bg-steel/[.09]",
};

export function Badge({ children, tone = "slate", className = "" }: any) {
  return <span className={`chip ${TONES[tone] || ""} ${className}`}>{children}</span>;
}

/* -------------------------------------------------------------- live dot */
export function Dot({ tone = "verd", className = "" }: any) {
  const c = tone === "alarm" ? "bg-alarm" : tone === "brass" ? "bg-brass" : "bg-verd";
  return <span className={`inline-block w-1.5 h-1.5 rounded-full animate-pulse2 ${c} ${className}`} />;
}

/* ------------------------------------------------------------ stat tiles */
export function Metric({ value, label, sub, tone }: any) {
  const c =
    tone === "brass" ? "text-brasslit" :
    tone === "verd"  ? "text-verd"     :
    tone === "alarm" ? "text-alarmlit" : "text-txt";
  return (
    <div className="px-5 py-[18px] border-r border-rule last:border-r-0">
      <p className={`semi text-[30px] leading-none num mb-2 ${c}`}>{value}</p>
      <p className="lbl">{label}</p>
      {sub && <p className="text-[11.5px] text-faint mt-1.5">{sub}</p>}
    </div>
  );
}

export function MetricRow({ children }: any) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 border border-rule rounded-md
                    overflow-hidden bg-slab">
      {children}
    </div>
  );
}

/* ------------------------------------------------------------- feedback */
export function Spinner({ label = "loading" }: any) {
  return (
    <div className="flex items-center gap-2.5 text-mute">
      <Dot tone="brass" />
      <span className="mono">{label}…</span>
    </div>
  );
}

export function ErrorBox({ error }: { error: string }) {
  return (
    <div className="rounded-md border border-alarm/40 bg-alarm/[.07] px-4 py-3 animate-rise">
      <p className="lbl !text-alarmlit mb-1">Something went wrong</p>
      <p className="mono text-alarmlit/90 break-all">{error}</p>
    </div>
  );
}

export function Empty({ title, hint }: any) {
  return (
    <div className="slab px-6 py-12 text-center">
      <p className="disp text-[16px] text-txt/70">{title}</p>
      {hint && <p className="text-[12.5px] text-mute mt-2">{hint}</p>}
    </div>
  );
}

/* ----------------------------------------------------------- note strip */
export function Note({ tone = "brass", children }: any) {
  const c = tone === "verd" ? "border-verd/30 bg-verd/[.06] text-verd"
                            : "border-brass/30 bg-brass/[.06] text-brasslit";
  return (
    <div className={`rounded-md border px-4 py-3 ${c}`}>
      <p className="text-[12.5px] leading-relaxed">{children}</p>
    </div>
  );
}

/* -------------------------------------------------- priority + breakdown */
export function ScoreBreakdown({ total, components, disclaimer }: any) {
  return (
    <div>
      <div className="flex items-end gap-3 mb-4">
        <span className="disp text-[46px] leading-[.82] text-brasslit num">{total}</span>
        <div className="pb-[3px]">
          <p className="lbl">investigative</p>
          <p className="lbl">priority</p>
        </div>
      </div>

      <div className="space-y-[9px]">
        {Object.entries(components || {}).map(([k, v]: any, i: number) => (
          <div key={`cmp-${k}-${i}`}>
            <div className="flex justify-between text-[11px] text-mute mb-1">
              <span>{k.replace(/_/g, " ")}</span>
              <span className="mono num">{v}</span>
            </div>
            <div className="h-[3px] rounded-sm bg-white/10 overflow-hidden">
              <div className="h-full transition-all duration-700"
                   style={{ width: `${Math.min(Math.max(v, 0), 100)}%`,
                            background: "linear-gradient(90deg,rgba(200,150,62,.45),#E8B65E)" }} />
            </div>
          </div>
        ))}
      </div>

      {disclaimer && (
        <p className="text-[10.5px] text-faint leading-relaxed mt-4 pl-[9px]
                      border-l-2 border-rule">{disclaimer}</p>
      )}
    </div>
  );
}

/* ------------------------------------------------- floating tab control */
export function Tabs({ tabs, active, onChange, floating = false }: any) {
  return (
    <div className={`flex gap-[2px] p-1 rounded-lg border border-rule2 overflow-x-auto
      ${floating ? "float" : "bg-slab"}`}>
      {tabs.map((t: any, ti: number) => {
        const on = active === t.id;
        return (
          <button key={`tab-${t.id}-${ti}`} onClick={() => onChange(t.id)}
            className={`px-3 py-1.5 rounded text-[12.5px] whitespace-nowrap transition-colors
              ${on ? "bg-brass/[.16] text-brasslit" : "text-mute hover:text-txt"}`}>
            {t.label}
            {t.count !== undefined && t.count !== null && (
              <span className={`ml-1.5 font-mono text-[10px] ${on ? "opacity-80" : "opacity-60"}`}>
                {t.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* --------------------------------------------------- severity-spined card */
export function SpineCard({ tone = "brass", children, className = "" }: any) {
  const c =
    tone === "alarm" ? "border-l-alarm" :
    tone === "verd"  ? "border-l-verd"  :
    tone === "faint" ? "border-l-faint" : "border-l-brass";
  return (
    <div className={`slab border-l-[3px] ${c} ${className}`}>{children}</div>
  );
}

/* ------------------------------------------------------ integrity seal */
export function Seal({ verify, onClose }: any) {
  const ok = verify.overall === "VALID";
  return (
    <div className={`flex items-center gap-4 flex-wrap rounded-md border px-5 py-[18px]
      ${ok ? "border-verd/35" : "border-alarm/45"}`}
      style={{ background: ok
        ? "linear-gradient(180deg,rgba(63,191,168,.09),rgba(63,191,168,.02))"
        : "linear-gradient(180deg,rgba(229,72,77,.1),rgba(229,72,77,.02))" }}>

      <div className={`w-14 h-14 rounded-full grid place-items-center text-[24px] shrink-0
        animate-stamp border-[1.5px]
        ${ok ? "border-verd/50 text-verd" : "border-alarm/55 text-alarmlit"}`}
        style={{ background: ok
          ? "radial-gradient(circle,rgba(63,191,168,.16),transparent 70%)"
          : "radial-gradient(circle,rgba(229,72,77,.16),transparent 70%)" }}>
        {ok ? "✓" : "✕"}
      </div>

      <div>
        <p className="lbl">Cryptographic integrity</p>
        <p className={`disp text-[23px] leading-none my-[3px] ${ok ? "text-verd" : "text-alarmlit"}`}>
          {verify.overall}
        </p>
        <p className="mono text-mute">
          evidence chain {verify.evidence_chain.chain_valid ? "unbroken" : "BROKEN"} ·
          {" "}audit chain {verify.audit_chain.valid ? "unbroken" : "BROKEN"} ·
          {" "}{verify.evidence_chain.evidence_count} records
        </p>
      </div>

      <div className="ml-auto text-right max-w-[330px]">
        <p className="lbl">Merkle root</p>
        <p className="mono text-[10.5px] text-brasslit break-all">
          {verify.evidence_chain.merkle_root}
        </p>
      </div>

      {onClose && (
        <button onClick={onClose} className="text-faint hover:text-txt text-[18px] leading-none">
          ×
        </button>
      )}
    </div>
  );
}
