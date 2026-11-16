/** URL prefix the site is served under (empty at a domain root); Next adds it to its own links, not to raw URLs. */
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

export function withBasePath(path: string): string {
  return `${BASE_PATH}${path}`;
}

/** The site's only page; the root sends readers here. */
export const HOME_PATH = '/infx/inference/deepseek-v41-flash/';
