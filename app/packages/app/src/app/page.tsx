import { HOME_PATH, HomeRedirect } from '@/components/marlowe/home-redirect';

export const metadata = { other: { refresh: `0; url=${HOME_PATH}` } };

export default function Home() {
  return <HomeRedirect />;
}
