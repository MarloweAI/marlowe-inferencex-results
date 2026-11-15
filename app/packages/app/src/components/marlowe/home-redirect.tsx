'use client';

import { useEffect } from 'react';

export const HOME_PATH = '/infx/inference/deepseek-v41-flash/';

/** The site's only page is the inference chart; the root sends readers there. */
export function HomeRedirect() {
  useEffect(() => {
    window.location.replace(HOME_PATH + window.location.search + window.location.hash);
  }, []);
  return (
    <main className="container mx-auto px-4 py-16 text-center">
      <a className="underline" href={HOME_PATH}>
        Open the results
      </a>
    </main>
  );
}
