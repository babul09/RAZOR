/** Shared loading + empty-state components for dashboard sections. */

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <p className="py-4 text-sm text-slate-400">{label}</p>;
}

export function Empty({ label = "No data" }: { label?: string }) {
  return <p className="py-6 text-center text-sm text-slate-400">{label}</p>;
}
