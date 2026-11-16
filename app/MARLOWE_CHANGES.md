# Changes from InferenceX-app

This directory is a modified copy of [SemiAnalysisAI/InferenceX-app](https://github.com/SemiAnalysisAI/InferenceX-app)
at the commit in `UPSTREAM_COMMIT`, licensed under the GNU GPL v3.0 (`LICENSE`). Marlowe modified it on 2026-11-15
to publish a static copy of the inference chart with Marlowe's measured points added. The changes:

- **Static export.** `packages/app/next.config.ts` exports a static site (no redirects, rewrites, analytics or
  PostHog). Every route except `/infx/inference/[model]` was removed, `src/proxy.ts` with it, and
  `src/app/page.tsx` sends the root to the DeepSeek-V4.1-Flash chart. Only models listed in
  `src/components/marlowe/models.ts` are exported.
- **Data from snapshots.** `src/lib/api/static-api.ts` maps the chart's API requests to JSON snapshots under
  `/data/api/`; `src/lib/api/api.ts` and `src/hooks/api/use-benchmark-presence.ts` use it. Date-specific and
  run-specific requests are not in the snapshot. `src/hooks/api/use-resident-sequence-lengths.ts` returns nothing,
  because its percentiles depend on the selected points.
- **Marlowe points.** `packages/constants/src/framework-aliases.ts` registers the `marlowe` and `marlowe-intvty`
  frameworks; `src/lib/charts/dynamic-colors.ts` gives them fixed orange shades; `src/components/inference/
  InferenceContext.tsx` keeps them in the default selection; `src/components/inference/utils/tooltipUtils.ts`
  links a Marlowe point to its recipe, and a published point's detail pages to the official site.
- **Branding.** `src/app/layout.tsx` uses Marlowe's header and footer (`src/components/marlowe/`) in place of the
  InferenceX header, footer, notices, analytics and seasonal effects. The dashboard tab bar is hidden
  (`src/components/dashboard/dashboard-shell.tsx`); page titles say Marlowe (`[model]/page.tsx`,
  `inference-page-intro.tsx`); the model-architecture link opens the official site
  (`ModelArchitectureInfoLink.tsx`). `src/components/marlowe/marlowe-notes.tsx` adds the measurement notes.
- **Assets.** Images, whitepapers, sounds and favicons not used by the chart were removed from
  `packages/app/public/`, as were the upstream `.github`, `.claude` and editor settings.
- **Error page.** `src/app/error.tsx` reloads the page once when a lazily loaded part fails to load, which on
  the private GitHub Pages site happens after its sign-in cookie expires.
- **Tooling.** The root `prepare` script no longer installs git hooks.

The upstream tests were not updated for these changes and are not run.
