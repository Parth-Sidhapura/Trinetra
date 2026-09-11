"use client";
import { useEffect, useState } from "react";
import { api, getHealth } from "@/lib/api";
import Shell from "@/components/Shell";
import { Badge, Label, Metric, MetricRow, Spinner, ErrorBox, SpineCard, Empty } from "@/components/ui";
import { canSeeSoc } from "@/lib/perms";

export default function SecurityCenter() {
  const [me, setMe] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [soc, setSoc] = useState<any>(null);
  const [backup, setBackup] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const [s, b] = await Promise.all([
        api("/security/soc"), api("/security/backup/status"),
      ]);
      setSoc(s); setBackup(b);
    } catch (e: any) { setErr(e.message); }
  }

  useEffect(() => {
    load();
    api("/admin/me").then(setMe).catch(() => {});
    getHealth().then(setHealth).catch(() => {});
  }, []);

  const lvl = soc?.api_threat_level;
  const tone = lvl === "LOW" ? "verd" : lvl === "ELEVATED" ? "brass" : "alarm";
  const color = lvl === "LOW" ? "text-verd" : lvl === "ELEVATED" ? "text-brasslit" : "text-alarmlit";

  return (
    <Shell me={me} health={health}>
      <div className="mb-5">
        <p className="lbl">Live aggregation over the audit and security-event tables</p>
        <h1 className="disp text-[30px] leading-[1.05] mt-1.5">Security operations</h1>
      </div>

      {err && /40[13]/.test(err) ? (
        <Empty title="Inspector rank required"
               hint="The audit log and security telemetry are restricted. Your account can read cases, but not the record of who looked at them." />
      ) : err ? (
        <div className="mb-4"><ErrorBox error={err} /></div>
      ) : null}
      {!soc && !err && <Spinner label="reading security telemetry" />}

      {soc && (
        <div className="space-y-3.5">
          {/* -------------------------------------------------- threat band */}
          <SpineCard tone={tone} className="p-5">
            <div className="flex items-center gap-5 flex-wrap">
              <div>
                <p className="lbl">API threat level</p>
                <p className={`disp text-[26px] leading-none mt-1 ${color}`}>{lvl}</p>
              </div>
              <span className="h-10 w-px bg-rule hidden md:block" />
              <div className="flex gap-6 flex-wrap">
                <div>
                  <p className="lbl">audit chain</p>
                  <div className="mt-1">
                    <Badge tone={soc.audit_chain === "VALID" ? "verd" : "alarm"}>
                      {soc.audit_chain}
                    </Badge>
                  </div>
                </div>
                <div>
                  <p className="lbl">honeytoken hits</p>
                  <div className="mt-1">
                    <Badge tone={soc.honeytoken_hits > 0 ? "alarm" : "slate"}>
                      {soc.honeytoken_hits}
                    </Badge>
                  </div>
                </div>
                <div>
                  <p className="lbl">active sessions</p>
                  <p className="mono text-[15px] text-txt num mt-1.5">{soc.active_sessions}</p>
                </div>
              </div>
              <p className="text-[11px] text-faint ml-auto max-w-xs leading-relaxed">
                Honeytokens are decoy records no legitimate query ever touches. A single
                hit is treated as an active intrusion signal.
              </p>
            </div>
          </SpineCard>

          <MetricRow>
            <Metric value={soc.failed_logins_24h} label="Failed logins · 24h"
                    tone={soc.failed_logins_24h > 5 ? "brass" : undefined}
                    sub="repeated failures lock the account" />
            <Metric value={soc.blocked_requests_24h} label="Blocked requests · 24h"
                    tone={soc.blocked_requests_24h > 0 ? "brass" : undefined}
                    sub="refused at the authorization stage" />
            <Metric value={soc.audit_events} label="Audit events" sub="each chained to the last" />
          </MetricRow>

          {/* ------------------------------------------------------ backup */}
          {backup && (
            <div className="slab p-4">
              <div className="flex items-center gap-3 flex-wrap mb-2">
                <Label>Immutable backup manifest</Label>
                <Badge tone={backup.comparison.status === "match" ? "verd" : "brass"}>
                  {backup.comparison.status}
                </Badge>
                <span className="mono text-mute">
                  {backup.manifest_count} manifest(s) exported
                </span>
                <button className="btn text-[12px] ml-auto"
                  onClick={() => { setBusy(true);
                    api("/security/backup/export", { method: "POST" })
                      .then(load).catch((e) => setErr(e.message))
                      .finally(() => setBusy(false)); }}>
                  {busy ? "exporting…" : "Export manifest now"}
                </button>
              </div>
              {backup.last_manifest && (
                <p className="font-mono text-[10.5px] text-brasslit break-all">
                  merkle root {backup.last_manifest.merkle_root}
                </p>
              )}
              <p className="text-[11px] text-faint mt-2 leading-relaxed max-w-3xl">
                Append-only. Manifests are named by sequence plus their own hash and are
                never overwritten, so a compromised database is detectable by divergence
                from the manifest history.
              </p>
            </div>
          )}

          {/* ------------------------------------------------------- audit */}
          <div className="slab p-4">
            <div className="flex items-center gap-3 mb-3 flex-wrap">
              <Label>Recent activity — hash-chained audit log</Label>
              <span className="mono text-faint ml-auto">
                {soc.evidence_records} evidence records under chain
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-[12.5px]">
                <thead>
                  <tr className="border-b border-rule text-left">
                    {["seq", "actor", "action", "result", "at"].map((h) => (
                      <th key={h} className="lbl py-2 pr-3">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {soc.recent_activity.map((a: any, ri: number) => (
                    <tr key={`ev-${a.seq}-${ri}`} className="border-b border-white/[.05] hover:bg-white/[.04]">
                      <td className="py-2 pr-3 mono text-faint num">{a.seq}</td>
                      <td className="py-2 pr-3 text-txt/85">{a.actor}</td>
                      <td className="py-2 pr-3 font-mono text-[11.5px] text-violet">{a.action}</td>
                      <td className="py-2 pr-3">
                        <span className={`mono ${a.result === "deny" ? "text-alarmlit" : "text-verd"}`}>
                          {a.result}
                        </span>
                      </td>
                      <td className="py-2 mono text-faint">{new Date(a.at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-faint mt-3 leading-relaxed max-w-3xl">
              Every row&apos;s hash includes the previous row&apos;s. Deleting or editing an
              audit entry breaks the chain from that point onward, and the break is visible
              on the case integrity check.
            </p>
          </div>
        </div>
      )}
    </Shell>
  );
}
