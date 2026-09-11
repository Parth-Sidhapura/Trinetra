"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Wordmark } from "@/components/Shell";

const STAGES = [
  ["Identity", "A Supabase-issued JWT, verified here against the published key set."],
  ["Case", "Membership on this case is checked before a single row is read."],
  ["Field", "Clearance rank gates classified fields inside a case."],
  ["Action", "Role rank gates the operation itself."],
];

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function signIn(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setBusy(false);
    if (error) return setErr(error.message);
    router.push("/dashboard");
  }

  return (
    <main className="min-h-screen grid lg:grid-cols-[1.05fr_1fr]">
      {/* ------------------------------------------------------------ brief */}
      <section className="hidden lg:flex flex-col justify-between p-10 border-r border-rule
                          relative overflow-hidden"
               style={{ background: "linear-gradient(160deg,#0E151E,#0B1017)" }}>
        <span className="pointer-events-none absolute -top-32 -left-24 w-[440px] h-[440px] rounded-full"
              style={{ background: "radial-gradient(circle,rgba(200,150,62,.1),transparent 68%)" }} />
        <div className="relative"><Wordmark size={28} /></div>

        <div className="relative">
          <p className="lbl mb-1">Zero-trust request pipeline</p>
          <h2 className="disp text-[26px] leading-tight mb-6 max-w-sm">
            Four checks, in this order, on every single request.
          </h2>
          <ol className="space-y-4 max-w-sm">
            {STAGES.map(([k, v], i) => (
              <li key={k} className="flex gap-3.5">
                <span className="font-mono text-[11px] text-brass pt-[3px]">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <p className="semi text-[13.5px]">{k}</p>
                  <p className="text-[12.5px] text-mute leading-relaxed">{v}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>

        <div className="relative max-w-sm">
          <p className="lbl mb-2.5">Ranks in this deployment</p>
          <dl className="space-y-1.5 mb-4">
            {[["Constable", "reads cases, cannot file or decide"],
              ["Inspector", "files evidence, decides identity matches, sees the audit log"],
              ["Admin", "the above, plus assigning ranks"]].map(([r, w]) => (
              <div key={r} className="flex gap-2.5 text-[12px]">
                <dt className="w-[76px] shrink-0 text-brass font-mono text-[11px]">{r}</dt>
                <dd className="text-mute leading-relaxed">{w}</dd>
              </div>
            ))}
          </dl>
          <p className="text-[11px] text-faint leading-relaxed">
            You do not choose a rank here. It is attached to your account on the
            server, and the server re-checks it on every request — so the screen
            you get is a consequence of your rank, never the cause of it.
          </p>
        </div>
      </section>

      {/* ------------------------------------------------------------- form */}
      <section className="flex items-center justify-center p-6">
        <form onSubmit={signIn} className="slab p-7 w-full max-w-sm space-y-4 animate-rise">
          <div className="lg:hidden mb-1"><Wordmark /></div>
          <div>
            <p className="lbl mb-1.5">Restricted system</p>
            <h1 className="disp text-[21px]">Investigator sign-in</h1>
          </div>

          <div>
            <label htmlFor="email" className="lbl block mb-1.5">Email</label>
            <input id="email" type="email" required autoComplete="username"
                   value={email} onChange={(e) => setEmail(e.target.value)} className="input" />
          </div>

          <div>
            <label htmlFor="password" className="lbl block mb-1.5">Password</label>
            <input id="password" type="password" required autoComplete="current-password"
                   value={password} onChange={(e) => setPassword(e.target.value)} className="input" />
          </div>

          {err && (
            <p className="mono text-alarmlit border-l-2 border-alarm/50 pl-2.5 animate-rise">
              {err}
            </p>
          )}

          <button disabled={busy} className="btn-pri w-full">
            {busy ? "authenticating…" : "Sign in"}
          </button>

          <p className="text-[11px] text-faint leading-relaxed border-t border-rule pt-3">
            Roles and clearance are assigned server-side. Failed attempts are rate-limited
            and written to the hash-chained audit log.
          </p>
        </form>
      </section>
    </main>
  );
}
