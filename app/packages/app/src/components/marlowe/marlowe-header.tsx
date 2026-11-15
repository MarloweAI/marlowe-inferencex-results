'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';

import { HEADER_ACTION_STYLE } from '@/components/ui/control-styles';
import { cn } from '@/lib/shared/utils';

/** Site header: the dashboard header's layout with Marlowe branding and a light/dark toggle. */
export function MarloweHeader() {
  const { resolvedTheme, setTheme } = useTheme();
  const dark = resolvedTheme === 'dark';
  return (
    <header className="vt-site-header sticky top-0 z-50 border-b border-border/30 mb-4 bg-background/95 backdrop-blur-md">
      <div className="container mx-auto px-4 lg:px-8">
        <div className="flex h-14 items-center gap-2 sm:gap-6">
          <a href="/" className="flex items-center min-h-11 gap-2 shrink-0">
            <span className="text-lg font-bold tracking-tight" style={{ color: "oklch(0.650 0.200 45.0)" }}>
              Marlowe
            </span>
            <span className="hidden sm:inline text-xs text-muted-foreground">inference results</span>
          </a>
          <div className="ml-auto flex items-center gap-1">
            <button
              type="button"
              aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
              className={cn(HEADER_ACTION_STYLE, 'min-h-11 min-w-11 justify-center')}
              onClick={() => setTheme(dark ? 'light' : 'dark')}
            >
              {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
