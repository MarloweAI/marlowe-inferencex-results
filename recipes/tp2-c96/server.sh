#!/bin/bash
# DeepSeek-V4.1-Flash AgentX server, MI355X TP2 C96.
# The exact command of the measured run. Only the model path and the listening port are replaced.
# MODEL_PATH: a local copy of deepseek-ai/DeepSeek-V4.1-Flash (weight bundle sha256 9f04cdab842e…).
# Image: Nov-17-2026-marlowe-optimized-v0 (sha256 83f8b7ddfab97aff…), commits:
#   MarloweAI/sglang 0a0fcd3356357adbfc201ac5fe4dd67f54446f3a
#   MarloweAI/sgl-amd-mono-upstream c85bc95ca041621f16ba925d35426d1896d0eec6
#   MarloweAI/marlowe-mix b79e610582f720ede1feb0b2380c8a5af7d89fd5
# The image's own environment applies too; the variables below are set on top of it.
# One server per node, started fresh for this concurrency.
# DP attention: one SGLang engine with --data-parallel-size 2 behind sglang_router (--dp-aware).

# Engine:
env -u ROCR_VISIBLE_DEVICES \
  GPU_ARCHS=gfx950 \
  SGLANG_ENABLE_AMD_MONO_RUNTIME_OPTIMIZATION=1 \
  SGLANG_OPT_DSV41_SAMPLING_ACCEPT_GRAPH=1 \
  SGLANG_OPT_DSV41_SAMPLED_VERIFY_VARIANT=1 \
  SGLANG_OPT_DSV41_BLOCKWISE_REJECTION=1 \
  SGLANG_OPT_DSV41_DSPARK_CYCLE_GRAPH=1 \
  SGLANG_OPT_DSV41_DSPARK_SLOT_WINDOW=1 \
  SGLANG_OPT_DSV41_DSPARK_CYCLE_RING=1 \
  SGLANG_DEFAULT_THINKING=1 \
  SGLANG_DSV41_REASONING_EFFORT=high \
  SGLANG_ENABLE_DSV41_ENGRAM_HOST_TABLE=1 \
  SGLANG_DSV41_ENGRAM_HOST_TABLE_LAYOUT=per_rank \
  SGLANG_USE_AITER=1 \
  SGLANG_USE_ROCM700A=0 \
  TORCH_BLAS_PREFER_HIPBLASLT=1 \
  AITER_BF16_FP8_MOE_BOUND=0 \
  TRITON_HIP_USE_ASYNC_COPY=0 \
  ROCM_QUICK_REDUCE_QUANTIZATION=INT8 \
  HSA_NO_SCRATCH_RECLAIM=0 \
  GPU_MAX_HW_QUEUES=2 \
  SGLANG_TIMEOUT_KEEP_ALIVE=900 \
  SGLANG_WARMUP_TIMEOUT=1800 \
  SGLANG_SET_CPU_AFFINITY=0 \
  SGLANG_OPT_FUSED_KDA_VERIFY=0 \
  SGLANG_DSA_FUSE_TOPK=1 \
  SGLANG_ENABLE_WAR_BARRIER=0 \
  SGLANG_FORCE_COARSE_WAR_BARRIER=0 \
  SGLANG_OPT_HIP_FLYDSL_MXFP8=1 \
  SGLANG_OPT_HIP_OPUS_SPARSE_PREFILL=true \
  SGLANG_HIP_DSV41_INDEX_K_PAGE8=0 \
  SGLANG_SHARED_EXPERT_TP1=1 \
  SGLANG_DP_USE_GATHERV=1 \
  SGLANG_DP_USE_REDUCE_SCATTER=1 \
  SGLANG_AITER_CAPTURE_COPY_IN=1 \
  SGLANG_SIMULATE_ACC_LEN=3.51 \
  SGLANG_SIMULATE_ACC_METHOD=match-expected \
  SGLANG_SIMULATE_ACC_TOKEN_MODE=real-draft-token \
  python3 -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --trust-remote-code \
  --language-model-only \
  --tp 2 \
  --ep-size 1 \
  --speculative-algorithm DSPARK \
  --speculative-dspark-block-size 5 \
  --enforce-shared-experts-fusion \
  --fp8-gemm-backend aiter \
  --enable-decoder-swa-bounded-replay \
  --cuda-graph-backend-prefill disabled \
  --mem-fraction-static 0.86 \
  --chunked-prefill-size 32768 \
  --prefill-decode-interval 8 \
  --swa-prefix-tails 4096 \
  --max-running-requests 128 \
  --cuda-graph-max-bs-decode 128 \
  --reasoning-parser auto \
  --tool-call-parser auto \
  --watchdog-timeout 3600 \
  --enable-metrics \
  --enable-cache-report \
  --port 54439 \
  --context-length 1048576 \
  --kv-cache-dtype fp8_e4m3 \
  --page-size 256 \
  --max-prefill-tokens 16384 \
  --schedule-policy fcfs \
  --enable-linear-replayssm-spec \
  --moe-runner-backend marlowe_mix \
  --speculative-moe-runner-backend marlowe_mix \
  --data-parallel-size 2 \
  --enable-dp-attention \
  --enable-dp-lm-head \
  --enable-prefill-delayer \
  --enable-dp-attention-local-control-broadcast \
  --tokenizer-worker-num 2 \
  --prefill-delayer-token-usage-low-watermark 0.7 \
  --load-balance-method total_requests \
  --served-model-name deepseek-ai/DeepSeek-V4.1-Flash \
  --host 127.0.0.1 &

# Router, which the client connects to:
python3 -m sglang_router.launch_router \
  --worker-urls http://127.0.0.1:54439 \
  --host 0.0.0.0 \
  --port 30000 \
  --prometheus-port 38583 \
  --policy cache_aware \
  --request-id-headers x-correlation-id \
  --dp-aware \
  --connect-timeout-secs 900 \
  --request-timeout-secs 14400 \
  --disable-health-check \
  --disable-retries \
  --max-tree-size 1073741824 \
  --balance-abs-threshold 1024
