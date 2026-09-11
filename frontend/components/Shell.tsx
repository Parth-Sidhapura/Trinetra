"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Badge, Dot } from "./ui";
import { canSeeSoc, canWrite, ROLE_LABEL } from "@/lib/perms";

/* The triple-eye mark. Brass, because this system's job is attestation. */
export function Mark({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden>
      <path d="M2.5 16C6.4 10 11 7 16 7s9.6 3 13.5 9c-3.9 6-8.5 9-13.5 9S6.4 22 2.5 16Z"
            stroke="#C8963E" strokeWidth="1.4" />
      <circle cx="16" cy="16" r="4.6" stroke="#C8963E" strokeWidth="1.4" />
      <circle cx="16" cy="16" r="1.9" fill="#E8B65E" />
    </svg>
  );
}

export function Wordmark({ size = 24 }: { size?: number }) {
  return (
    <span className="flex items-center gap-2.5">
      <Mark size={size} />
      <b className="disp-wide text-[15px] tracking-[.2em]">TRINETRA</b>
    </span>
  );
}

const NAV = [
  {
    href: "/dashboard", label: "Cases",
    icon: (<><rect x="1.5" y="2.5" width="13" height="11" rx="1.5" stroke="currentColor" />
             <path d="M1.5 6h13" stroke="currentColor" /></>),
  },
  {
    href: "/security", label: "Security Ops",
    icon: (<path d="M8 1.8 13.5 4v4.2c0 3.1-2.2 5.2-5.5 6-3.3-.8-5.5-2.9-5.5-6V4L8 1.8Z"
                 stroke="currentColor" />),
  },
];

/**
 * The console frame: a fixed rail on the left, a status ribbon on top.
 * `bare` hands the whole content area to the page (the graph canvas uses it).
 */
export default function Shell({
  me, health, children, bare = false,
}: {
  me?: any; health?: any; children: React.ReactNode; bare?: boolean;
}) {
  const router = useRouter();
  const path = usePathname();

  const pgOk = !health || health.postgres === "ok";
  const neo4j: string = health?.neo4j ?? "";

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[214px_minmax(0,1fr)]">
      {/* ------------------------------------------------------------ rail */}
      <aside className="sticky top-0 h-screen flex flex-col py-[18px] border-r border-rule
                        max-lg:hidden"
             style={{ background: "linear-gradient(180deg,#0E151E,#0B1017)" }}>
        <Link href="/dashboard" className="px-[18px] pb-5"><Wordmark /></Link>

        <p className="lbl px-[18px] pt-3.5 pb-1.5">Workspace</p>
        <nav>
          {NAV.filter((n) => n.href !== "/security" || canSeeSoc(me)).map((n) => {
            const on = path?.startsWith(n.href);
            return (
              <Link key={n.href} href={n.href}
                className={`flex items-center gap-2.5 px-[18px] py-[7px] text-[13.5px]
                  border-l-2 transition-colors
                  ${on ? "text-brasslit border-brass"
                       : "text-mute border-transparent hover:text-txt hover:bg-white/[.04]"}`}
                style={on ? { background: "linear-gradient(90deg,rgba(200,150,62,.13),transparent)" } : undefined}>
                <svg width="15" height="15" viewBox="0 0 16 16" fill="none" className="shrink-0 opacity-85">
                  {n.icon}
                </svg>
                {n.label}
              </Link>
            );
          })}
        </nav>

        <p className="lbl px-[18px] pt-5 pb-1.5">System</p>
        <div className="px-[18px] space-y-[7px]">
          <p className="flex items-center gap-2 mono" style={{ color: pgOk ? "#3FBFA8" : "#FF8086" }}>
            <Dot tone={pgOk ? "verd" : "alarm"} /> postgres · {health?.postgres ?? "ok"}
          </p>
          <p className="flex items-center gap-2 mono text-verd">
            <Dot tone="verd" /> api · {health?.api ?? "ok"}
          </p>

          {/* Neo4j is an optional projection, not the system of record.
              When it is switched off it is not part of this deployment, so it
              is not reported; when it is switched ON but failing, that IS worth
              saying, because the projection is then stale. */}
          {neo4j === "ok" && (
            <p className="flex items-center gap-2 mono text-verd">
              <Dot tone="verd" /> neo4j · synced
            </p>
          )}
          {neo4j.startsWith("error") && (
            <p className="flex items-center gap-2 mono text-brasslit"
               title="The confirmed graph is derived from Postgres and is unaffected.">
              <Dot tone="brass" /> projection · stale
            </p>
          )}
        </div>

        <div className="mt-auto px-[18px] pt-3.5 border-t border-rule">
          <p className="mono text-[11.5px] text-txt truncate">{me?.email || "…"}</p>
          {me && (
            <>
              <div className="flex gap-1.5 mt-1.5 flex-wrap">
                <Badge tone={canWrite(me) ? "brass" : "steel"}>{me.role}</Badge>
                <Badge>{me.clearance}</Badge>
              </div>
              <p className="text-[10.5px] text-faint mt-1.5 leading-snug">
                {ROLE_LABEL[me.role] || "Access level assigned server-side"}
              </p>
            </>
          )}
          <button onClick={() => supabase.auth.signOut().then(() => router.push("/login"))}
                  className="lbl mt-2.5 hover:text-alarmlit transition-colors">
            Sign out
          </button>
        </div>
      </aside>

      {/* ------------------------------------------------------------ main */}
      <div className="min-w-0 flex flex-col">
        <div className="h-[46px] flex items-center gap-3.5 px-4 md:px-6
                        border-b border-rule bg-[#0C121A] shrink-0">
          <Link href="/dashboard" className="lg:hidden"><Mark size={20} /></Link>
          <Dot tone={pgOk ? "verd" : "alarm"} />
          <span className="mono text-mute">{pgOk ? "SYSTEM NOMINAL" : "DEGRADED"}</span>
          {me && !canWrite(me) && (
            <span className="chip !border-steel/45 !text-steel bg-steel/[.09]">
              READ-ONLY
            </span>
          )}
          <span className="lbl ml-auto hidden sm:block">PS 26189 · MHA / NCRB · TEAM 243</span>
          {canSeeSoc(me) && (
            <Link href="/security" className="lbl lg:hidden hover:text-brasslit">Sec Ops</Link>
          )}
        </div>

        {bare ? children : <div className="px-4 md:px-6 py-6 pb-12">{children}</div>}
      </div>
    </div>
  );
}
