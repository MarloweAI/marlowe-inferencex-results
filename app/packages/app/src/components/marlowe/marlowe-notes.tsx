import { MARLOWE_SNAPSHOT_DATE } from './snapshot-date';

/** How the Marlowe points were measured, shown under the chart. */
export function MarloweNotes() {
  return (
    <section className="rounded-xl border border-border/60 bg-card p-6 text-sm text-muted-foreground">
      <h2 className="mb-3 text-base font-semibold text-foreground">How the Marlowe points were measured</h2>
      <ol className="list-decimal space-y-2 pl-5">
        <li>
          <strong className="text-foreground">Simulated speculative acceptance.</strong> Every Marlowe point runs
          with a simulated accept length of 3.51 (<code>SGLANG_SIMULATE_ACC_LEN=3.51</code>,{' '}
          <code>match-expected</code>, <code>real-draft-token</code>), as InferenceX&apos;s CI sets for
          DeepSeek-V4.1-Flash&apos;s DSpark speculative decoding. The measured mean accept length was 3.51 on every
          run.
        </li>
        <li>
          <strong className="text-foreground">Measured by Marlowe, not by InferenceX CI.</strong> We ran
          InferenceX&apos;s own client (agentx-harness 1.0.13, <code>agentx</code> preset, 3600 s, sequential trace
          replay) and scored the results with InferenceX&apos;s formulas (<code>agentx-audit-data</code>{' '}
          <code>windows.py</code>, full window), on our own MI355X nodes with a build that is not a published image.
          InferenceX has not reviewed or reproduced these numbers.
        </li>
        <li>
          <strong className="text-foreground">Shared nodes.</strong> Several servers shared each 8-GPU node on
          disjoint GPUs (four TP2 or two TP4 servers), each pinned to its own socket&apos;s CPU cores, with the client
          on the same node. InferenceX runs one server per node.
        </li>
        <li>
          <strong className="text-foreground">Request caps.</strong> Some points cap concurrent decoding requests
          (<code>--max-running-requests</code>, e.g. 1 at C1 and C2, 2 or 4 on the interactivity-leaning points).
          Requests over the cap wait in the queue, so the wait shows in TTFT, not in interactivity. Each point&apos;s
          cap is in its recipe.
        </li>
        <li>
          <strong className="text-foreground">Engram host table on at TP2.</strong> At TP2 the model only fits with
          the Engram tables in host memory (the InferenceX MI355X SGLang recipe&apos;s setting); at TP4 and TP8 they
          stay on the GPU.
        </li>
        <li>
          <strong className="text-foreground">Builds.</strong> Earlier series, TP2 and TP4 points: image{' '}
          <code>lb-sgl1a16c3def9-mono3c777011</code>, MarloweAI/sglang <code>1a16c3de</code> (marlowe-dev{' '}
          <code>08d1e520</code>) + sgl-amd-mono <code>3c777011</code> + marlowe-mix <code>edde9499</code>. TP8 C1:
          image <code>lb-sgl2ad94ff74d-mono5c4c0d20</code>, MarloweAI/sglang <code>2ad94ff7</code> (marlowe-dev{' '}
          <code>ab55bd11</code>) + sgl-amd-mono <code>5c4c0d20</code> + marlowe-mix <code>edde9499</code>; it changes
          only bookkeeping and TP8 start-up, not the TP2/TP4 kernels. The 2026-11-17 series (C1 to C8) runs on the
          newer release build: image <code>team-nov17-marlowe-optimized-v0</code>, MarloweAI/sglang marlowe-dev{' '}
          <code>0a0fcd33</code> + sgl-amd-mono <code>c85bc95c</code> + marlowe-mix <code>b79e6105</code>. The other
          series, C16 and up included, are on the earlier build above. All run InferenceX&apos;s MI355X SGLang agentic
          recipe with Marlowe&apos;s MoE runner and monokernel added; no point uses DP attention.
        </li>
        <li>
          <strong className="text-foreground">Series.</strong> &ldquo;Marlowe SGLang&rdquo; is the main series;
          &ldquo;interactivity-leaning&rdquo; trades TTFT for interactivity with tighter request caps. The two &ldquo;2026-11-17&rdquo; series re-measure the C1, C2 and C8 points on the
          release build with the same server and client commands; the earlier curves stay as published. The main TP2 C64
          point is still being chosen and is not shown. Power, cost-per-energy and cache-hit metrics were not measured
          for Marlowe points, so they do not appear on those charts.
        </li>
      </ol>
      <p className="mt-4">
        Published InferenceX results: snapshot of {MARLOWE_SNAPSHOT_DATE}. Click any Marlowe point, then
        &ldquo;Marlowe recipe&rdquo;, for its exact server and client commands.
      </p>
    </section>
  );
}
