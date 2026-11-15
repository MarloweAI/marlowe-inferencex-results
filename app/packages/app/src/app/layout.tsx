import '@/lib/runtime/polyfills';
import './globals.css';

import type { Metadata } from 'next';
import { DM_Sans } from 'next/font/google';

import { MarloweFooter } from '@/components/marlowe/marlowe-footer';
import { MarloweHeader } from '@/components/marlowe/marlowe-header';
import { ThemeProvider } from '@/components/ui/theme-provider';
import { APP_THEMES } from '@/lib/themes/themes';
import { QueryProvider } from '@/providers/query-provider';

const dm_sans = DM_Sans({
  subsets: ['latin'],
  display: 'optional',
  variable: '--font-dm-sans',
});

export const metadata: Metadata = {
  title: { default: 'Marlowe inference results', template: '%s | Marlowe' },
  description:
    "Marlowe's DeepSeek-V4.1-Flash AgentX results on AMD MI355X, charted beside InferenceX's published results.",
  robots: { index: false, follow: false },
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${dm_sans.variable} antialiased relative min-h-screen flex flex-col`}>
        <QueryProvider>
          <ThemeProvider
            attribute="class"
            defaultTheme="light"
            themes={APP_THEMES}
            enableSystem
            disableTransitionOnChange
          >
            <MarloweHeader />
            <div className="grow flex flex-col">{children}</div>
            <MarloweFooter />
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
