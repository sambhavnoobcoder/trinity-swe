# Trinity-SWE GPU Setup Guide

## Quick Start for GPU Execution

### 1. Install GPU Dependencies

```bash
# Install PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install vLLM for fast GPU inference
pip install vllm

# Or install Text Generation Inference (alternative)
# pip install text-generation
```

### 2. Model Options

**Option A: Ollama (Recommended)**
```bash
# Pull the actual Qwen3-Coder model
ollama pull qwen3-coder:30b
```

**Option B: GPU acceleration with vLLM**
Edit `trinity_swe_qwen3_local.py` and uncomment the GPU_CONFIG section:

```python
# Uncomment these lines:
GPU_CONFIG = {
    'backend': 'vllm',  # or 'tgi' for Text Generation Inference
    'model_name': 'Qwen/QwQ-32B-Preview',  # Qwen3-Coder equivalent
    'gpu_memory_utilization': 0.9,
    'tensor_parallel_size': 1,  # Increase for multi-GPU
    'max_model_len': 32768,
    'dtype': 'bfloat16'
}
```

### 3. Run Full Dataset Prediction

```bash
# Generate predictions for all 500 instances
python3 run_trinity_qwen3_local.py --instances 500

# This will create: trinity_swe_qwen3_local_500/all_preds.jsonl
```

### 4. Submit to Hugging Face

Upload the generated `all_preds.jsonl` to:
https://huggingface.co/spaces/swe-bench/leaderboard

## Performance Notes

- **32B model**: ~24GB VRAM required
- **Expected time**: 2-4 hours for 500 instances on RTX 4090
- **Throughput**: ~2-3 instances/minute with vLLM

## Troubleshooting

### Out of Memory
- Reduce `gpu_memory_utilization` to 0.8
- Use smaller model: `Qwen/Qwen2.5-Coder-14B-Instruct`

### Slow inference
- Ensure vLLM is installed: `pip install vllm`
- Check CUDA availability: `python -c "import torch; print(torch.cuda.is_available())"`

## Multi-GPU Setup

For multiple GPUs, increase `tensor_parallel_size`:
```python
'tensor_parallel_size': 2,  # For 2 GPUs
'tensor_parallel_size': 4,  # For 4 GPUs
```