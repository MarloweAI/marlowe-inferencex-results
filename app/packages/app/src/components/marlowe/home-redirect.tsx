'use client';

import { useEffect } from 'react';
import { HOME_PATH, withBasePath } from '@/components/marlowe/base-path';

/** The site's only page is the inference chart; the root sends readers there. */
export function HomeRedirect() {
  useEffect(() => {
    window.location.replace(withBasePath(HOME_PATH) + window.location.search + window.location.hash);
  }, []);
  return (
    <main className="container mx-auto px-4 py-16 text-center">
      <a className="underline" href={withBasePath(HOME_PATH)}>
        Open the results
      </a>
    </main>
  );
}
