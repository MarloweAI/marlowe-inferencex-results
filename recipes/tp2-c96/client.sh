#!/bin/bash
# InferenceX agentx-harness client for DeepSeek-V4.1-Flash, C96, 3600 s replay.
# The exact command of the measured run. Local paths are replaced by variables:
#   TOKENIZER_PATH: a local copy of deepseek-ai/DeepSeek-V4.1-Flash (tokenizer files),
#   OUT: the run's output directory.

export AIPERF_REQUIRED_SERVER_METRIC_PREFIX=sglang:
export AIPERF_HTTP_TCP_USER_TIMEOUT=900000

agentx profile \
  --scenario agentx \
  --url http://127.0.0.1:30000 \
  --model deepseek-ai/DeepSeek-V4.1-Flash \
  --tokenizer "$TOKENIZER_PATH" \
  --tokenizer-trust-remote-code \
  --concurrency 96 \
  --benchmark-duration 3600 \
  --public-dataset semianalysis_cc_traces_weka_062126 \
  --random-seed 42 \
  --dataset-sampling-strategy sequential \
  --num-dataset-entries 393 \
  --trajectory-start-min-ratio 0.25 \
  --trajectory-start-max-ratio 0.75 \
  --warmup-requests-per-lane 10 \
  --warmup-grace-period 3600 \
  --trace-idle-gap-cap-seconds 300 \
  --request-timeout-seconds 21600 \
  --failed-request-threshold 0.1 \
  --output-artifact-dir "$OUT/aiperf_artifacts" \
  --server-metrics http://127.0.0.1:30000/metrics
