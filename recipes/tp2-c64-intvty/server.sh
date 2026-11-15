#!/bin/bash
# DeepSeek-V4.1-Flash AgentX server, MI355X TP2 C64 (interactivity-leaning series).
# The exact command of the charted run. Only the model path is replaced by a variable.
# MODEL_PATH: a local copy of deepseek-ai/DeepSeek-V4.1-Flash at revision 314113f8a7dadb388215396ba5fbee2c610a04d6.
# Image: lb-sgl1a16c3def9-mono3c777011 (built on the InferenceX MI355X SGLang image), commits:
#   MarloweAI/sglang 1a16c3def99bce67235d6639aae9eacca7a6b860 (merged to marlowe-dev as 08d1e520)
#   MarloweAI/sgl-amd-mono-upstream 3c777011a885754659bb60c5b80be0d70cf4b2fc
#   MarloweAI/marlowe-mix edde94993c964e6fa6d4d2851ec2a69f9fd165b5
# The image's own environment applies too; the variables below are set on top of it.
# Several servers shared each node on disjoint GPUs, each pinned with taskset to its socket's cores.

env -u HIP_VISIBLE_DEVICES -u CUDA_VISIBLE_DEVICES \
  PYTHONNOUSERSITE=1 \
  PYTHONUNBUFFERED=1 \
  SGLANG_TIMEOUT_KEEP_ALIVE=900 \
  SGLANG_DEFAULT_THINKING=1 \
  SGLANG_DSV41_REASONING_EFFORT=high \
  SGLANG_USE_AITER=1 \
  SGLANG_USE_ROCM700A=0 \
  TRITON_HIP_USE_ASYNC_COPY=0 \
  ROCM_QUICK_REDUCE_QUANTIZATION=INT8 \
  SGLANG_OPT_HIP_OPUS_SPARSE_PREFILL=true \
  SGLANG_OPT_HIP_FLYDSL_MXFP8=1 \
  SGLANG_HIP_FP4_INDEXER_ROWGROUP=1 \
  TORCH_BLAS_PREFER_HIPBLASLT=1 \
  HSA_NO_SCRATCH_RECLAIM=0 \
  GPU_MAX_HW_QUEUES=2 \
  SGLANG_ENABLE_DSV41_ENGRAM_HOST_TABLE=1 \
  SGLANG_DSV41_ENGRAM_HOST_TABLE_LAYOUT=per_rank \
  SGLANG_ENABLE_AMD_MONO_RUNTIME_OPTIMIZATION=1 \
  SGLANG_OPT_DSV41_SAMPLING_ACCEPT_GRAPH=1 \
  SGLANG_OPT_DSV41_SAMPLED_VERIFY_VARIANT=1 \
  SGLANG_OPT_DSV41_BLOCKWISE_REJECTION=1 \
  SGLANG_OPT_DSV41_DSPARK_CYCLE_GRAPH=1 \
  SGLANG_OPT_DSV41_DSPARK_SLOT_WINDOW=1 \
  SGLANG_OPT_DSV41_DSPARK_CYCLE_RING=1 \
  SGLANG_SIMULATE_ACC_LEN=3.51 \
  SGLANG_SIMULATE_ACC_METHOD=match-expected \
  SGLANG_SIMULATE_ACC_TOKEN_MODE=real-draft-token \
  ROCR_VISIBLE_DEVICES=2,3 \
  SGLANG_SET_CPU_AFFINITY=0 \
  taskset -c 48-87 \
  python3 -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --served-model-name deepseek-ai/DeepSeek-V4.1-Flash \
  --host 127.0.0.1 \
  --port 31040 \
  --nccl-port 31041 \
  --trust-remote-code \
  --tensor-parallel-size 2 \
  --speculative-algorithm DSPARK \
  --speculative-dspark-block-size 5 \
  --enforce-shared-experts-fusion \
  --fp8-gemm-backend aiter \
  --cuda-graph-max-bs-decode 64 \
  --enable-decoder-swa-bounded-replay \
  --cuda-graph-backend-prefill disabled \
  --reasoning-parser auto \
  --tool-call-parser auto \
  --image-processor-backend pil \
  --watchdog-timeout 3600 \
  --enable-metrics \
  --mem-fraction-static 0.85 \
  --chunked-prefill-size 16384 \
  --prefill-decode-interval 48 \
  --schedule-policy shortest-prefill-first \
  --swa-prefix-tails 4096 \
  --max-running-requests 128 \
  --cuda-graph-max-bs-decode 128 \
  --moe-runner-backend marlowe_mix \
  --speculative-moe-runner-backend marlowe_mix \
  --enable-amd-monokernel
