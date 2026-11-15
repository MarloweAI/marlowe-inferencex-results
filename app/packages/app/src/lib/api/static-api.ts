/**
 * The site is a static export: API requests are served from JSON snapshots under /data/api/.
 * Returns the snapshot URL for an API URL, or null when the snapshot does not hold that view.
 */
const BASE = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}/data/api`;

export function staticApiUrl(url: string): string | null {
  const u = new URL(url, 'http://static.invalid');
  const q = u.searchParams;
  switch (u.pathname) {
    case '/api/v1/benchmarks': {
      const model = q.get('model');
      // Only the latest results per configuration are in the snapshot.
      if (!model || q.has('runId') || q.has('date')) return null;
      return `${BASE}/benchmarks/${encodeURIComponent(model)}.json`;
    }
    case '/api/v1/availability/compact':
      return `${BASE}/availability-compact.json`;
    case '/api/v1/benchmark-presence':
      return `${BASE}/benchmark-presence.json`;
    case '/api/v1/workflow-info': {
      const date = q.get('date');
      return date ? `${BASE}/workflow-info/${date}.json` : null;
    }
    default:
      return null;
  }
}
