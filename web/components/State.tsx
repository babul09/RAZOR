/** Shared loading + empty-state components for the recovery terminal. */

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <p className="animate-pulse-soft py-8 font-mono text-sm text-fg-muted">
      {label}…
    </p>
  );
}

export function Empty({ label = "No data" }: { label?: string }) {
  return (
    <p className="py-10 text-center font-mono text-sm text-fg-muted">{label}</p>
  );
}
