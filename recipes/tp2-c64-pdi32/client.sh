#!/bin/bash
# InferenceX agentx-harness client for DeepSeek-V4.1-Flash, C64, 3600 s replay.
# The exact command of the charted run. Local paths are replaced by variables:
#   TOKENIZER_PATH: the Hugging Face snapshot directory of deepseek-ai/DeepSeek-V4.1-Flash (tokenizer files),
#   OUT: the run's output directory.
# The client ran on the server's node, pinned to 8 cores of the server's socket.

export HF_HUB_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export AIPERF_HTTP_TCP_USER_TIMEOUT=900000
export AIPERF_REQUIRED_SERVER_METRIC_PREFIX=sglang:

agentx profile \
  --url http://127.0.0.1:31080 \
  --model deepseek-ai/DeepSeek-V4.1-Flash \
  --tokenizer "$TOKENIZER_PATH" \
  --concurrency 64 \
  --benchmark-duration 3600 \
  --tokenizer-trust-remote-code \
  --server-metrics http://127.0.0.1:31080/metrics \
  --output-artifact-dir "$OUT/aiperf_artifacts" \
  --public-dataset semianalysis_cc_traces_weka_062126 \
  --warmup-grace-period 3600
