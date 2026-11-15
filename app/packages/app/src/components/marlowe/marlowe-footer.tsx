const INFERENCEX_SITE = 'https://inferencex.semianalysis.com';
const INFERENCEX_APP_REPO = 'https://github.com/SemiAnalysisAI/InferenceX-app';

/** Site footer: data credit, licence and the no-endorsement statement. */
export function MarloweFooter() {
  return (
    <footer className="mt-12 border-t border-border/30">
      <div className="container mx-auto px-4 lg:px-8 py-8 flex flex-col gap-2 text-sm text-muted-foreground">
        <p>
          Published results: published by{' '}
          <a className="underline" href={INFERENCEX_SITE} rel="noopener noreferrer" target="_blank">
            InferenceX (SemiAnalysis)
          </a>
          , from its public API (snapshot date shown under the chart). Points labelled Marlowe are measured
          by Marlowe; each links to its recipe.
        </p>
        <p>
          SemiAnalysis and InferenceX have not reviewed or endorsed the Marlowe results on this page. This
          site is built from the{' '}
          <a className="underline" href={INFERENCEX_APP_REPO} rel="noopener noreferrer" target="_blank">
            InferenceX-app
          </a>{' '}
          dashboard code, modified by Marlowe, under the GNU GPL v3.0.
        </p>
      </div>
    </footer>
  );
}
