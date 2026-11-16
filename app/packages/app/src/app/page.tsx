import { HOME_PATH, withBasePath } from '@/components/marlowe/base-path';
import { HomeRedirect } from '@/components/marlowe/home-redirect';

export const metadata = { other: { refresh: `0; url=${withBasePath(HOME_PATH)}` } };

export default function Home() {
  return <HomeRedirect />;
}
