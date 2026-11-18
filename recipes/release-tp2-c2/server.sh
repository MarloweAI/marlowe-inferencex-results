#!/bin/bash
# DeepSeek-V4.1-Flash AgentX server, MI355X TP2 C2 (release-main series).
# The exact command of the charted run. Only the model path is replaced by a variable.
# MODEL_PATH: a local copy of deepseek-ai/DeepSeek-V4.1-Flash at revision 314113f8a7dadb388215396ba5fbee2c610a04d6.
# Image: team-nov17-marlowe-optimized-v0 (built on the InferenceX MI355X SGLang image), commits:
#   MarloweAI/sglang 0a0fcd3356357adbfc201ac5fe4dd67f54446f3a
#   MarloweAI/sgl-amd-mono-upstream c85bc95ca041621f16ba925d35426d1896d0eec6
#   MarloweAI/marlowe-mix b79e610582f720ede1feb0b2380c8a5af7d89fd5
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
  ROCR_VISIBLE_DEVICES=0,1 \
  SGLANG_SET_CPU_AFFINITY=0 \
  taskset -c 96,128-159,177-183 \
  python3 -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --served-model-name deepseek-ai/DeepSeek-V4.1-Flash \
  --host 127.0.0.1 \
  --port 31100 \
  --nccl-port 31101 \
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
  --mem-fraction-static 0.70 \
  --chunked-prefill-size 16384 \
  --prefill-decode-interval 192 \
  --schedule-policy lpm \
  --swa-prefix-tails 128 \
  --max-running-requests 1 \
  --moe-runner-backend marlowe_mix \
  --speculative-moe-runner-backend marlowe_mix \
  --enable-amd-monokernel
