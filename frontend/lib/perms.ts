/**
 * The UI's view of what you may do.
 *
 * This is presentation only — it hides controls you cannot use so the screen
 * doesn't lie to you. It is NOT the access check. Every write endpoint is
 * guarded server-side with require_role(), so deleting this file, editing it
 * in devtools, or calling the API directly changes nothing about what the
 * backend will actually accept.
 */
export const ROLE_RANK: Record<string, number> = {
  CONSTABLE: 1, INSPECTOR: 2, ADMIN: 3,
};

export type Me = { role?: string; clearance?: string; email?: string } | null;

export const rank = (me: Me) => ROLE_RANK[me?.role || ""] ?? 0;

/** May open cases, upload evidence, confirm merges, run detectors. */
export const canWrite = (me: Me) => rank(me) >= ROLE_RANK.INSPECTOR;

/** May see the Security Operations Center and the audit log. */
export const canSeeSoc = (me: Me) => rank(me) >= ROLE_RANK.INSPECTOR;

/** May manage other users' roles. */
export const isAdmin = (me: Me) => rank(me) >= ROLE_RANK.ADMIN;

export const ROLE_LABEL: Record<string, string> = {
  CONSTABLE: "Read-only access",
  INSPECTOR: "Can file and decide",
  ADMIN: "Full administrative access",
};
