#!/usr/bin/env python3
"""
Setup Script for Local Inference Backends
Helps install and configure local inference options
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

def run_command(cmd, check=True):
    """Run shell command"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout)
    return True

async def setup_ollama():
    """Setup Ollama with Qwen models"""
    print("🦙 Setting up Ollama...")
    
    # Install Ollama (macOS/Linux)
    if sys.platform == "darwin":
        print("Installing Ollama on macOS...")
        run_command("curl -fsSL https://ollama.ai/install.sh | sh")
    elif sys.platform.startswith("linux"):
        print("Installing Ollama on Linux...")
        run_command("curl -fsSL https://ollama.ai/install.sh | sh")
    else:
        print("Please install Ollama manually from https://ollama.ai/")
        return False
    
    # Start Ollama service
    print("Starting Ollama service...")
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait a bit for service to start
    await asyncio.sleep(3)
    
    # Pull recommended models (in order of preference)
    models = [
        "qwen2.5-coder:32b",  # Best for coding
        "qwen2.5-coder:14b",  # Good balance
        "qwen2.5-coder:7b",   # Faster option
        "codellama:34b",      # Alternative
        "codellama:13b"       # Fallback
    ]
    
    print("📥 Pulling coding models (this may take a while)...")
    for model in models:
        print(f"Pulling {model}...")
        success = run_command(f"ollama pull {model}", check=False)
        if success:
            print(f"✅ Successfully pulled {model}")
            break
        else:
            print(f"❌ Failed to pull {model}, trying next...")
    
    return True

def setup_vllm():
    """Setup vLLM for high-performance inference"""
    print("🚀 Setting up vLLM...")
    
    # Install vLLM
    print("Installing vLLM...")
    if not run_command("pip install vllm", check=False):
        print("Trying with --user flag...")
        run_command("pip install --user vllm")
    
    # Create startup script
    startup_script = """#!/bin/bash
# vLLM Startup Script for Trinity-SWE

MODEL="Qwen/Qwen2.5-Coder-32B-Instruct"
PORT=8000

echo "🚀 Starting vLLM server with $MODEL..."
echo "Server will be available at http://localhost:$PORT"

python -m vllm.entrypoints.openai.api_server \\
    --model $MODEL \\
    --port $PORT \\
    --host 0.0.0.0 \\
    --served-model-name qwen-coder \\
    --max-model-len 32768 \\
    --gpu-memory-utilization 0.9
"""
    
    with open("start_vllm.sh", "w") as f:
        f.write(startup_script)
    
    os.chmod("start_vllm.sh", 0o755)
    print("✅ Created start_vllm.sh script")
    print("Run ./start_vllm.sh to start vLLM server")
    
    return True

def setup_tgi():
    """Setup Text Generation Inference"""
    print("🤗 Setting up Text Generation Inference...")
    
    # Create Docker compose file
    docker_compose = """version: '3.8'
services:
  tgi:
    image: ghcr.io/huggingface/text-generation-inference:1.4
    ports:
      - "3000:80"
    volumes:
      - ./data:/data
    environment:
      - MODEL_ID=Qwen/Qwen2.5-Coder-32B-Instruct
      - MAX_INPUT_LENGTH=32768
      - MAX_TOTAL_TOKENS=32768
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
"""
    
    with open("docker-compose.tgi.yml", "w") as f:
        f.write(docker_compose)
    
    print("✅ Created docker-compose.tgi.yml")
    print("Run 'docker-compose -f docker-compose.tgi.yml up' to start TGI")
    
    return True

async def test_all_backends():
    """Test which backends are currently running"""
    print("🧪 Testing available backends...")
    
    from local_inference import test_local_setup
    await test_local_setup()

def print_usage_instructions():
    """Print usage instructions for all backends"""
    print("\n📋 Usage Instructions:")
    print("=" * 50)
    
    print("\n1. Ollama (Easiest setup):")
    print("   - Automatically installs and configures")
    print("   - Run: python setup_local_inference.py --ollama")
    print("   - Models: qwen2.5-coder, codellama")
    
    print("\n2. vLLM (Best performance):")
    print("   - Requires CUDA GPU")
    print("   - Run: python setup_local_inference.py --vllm")
    print("   - Start: ./start_vllm.sh")
    
    print("\n3. TGI (HuggingFace):")
    print("   - Requires Docker + GPU")
    print("   - Run: python setup_local_inference.py --tgi")
    print("   - Start: docker-compose -f docker-compose.tgi.yml up")
    
    print("\n4. Test all:")
    print("   - Run: python setup_local_inference.py --test")
    
    print("\n🎯 After setup, run Trinity-SWE with:")
    print("   python trinity_swe_local.py")

async def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup local inference for Trinity-SWE")
    parser.add_argument("--ollama", action="store_true", help="Setup Ollama")
    parser.add_argument("--vllm", action="store_true", help="Setup vLLM")
    parser.add_argument("--tgi", action="store_true", help="Setup TGI")
    parser.add_argument("--all", action="store_true", help="Setup all backends")
    parser.add_argument("--test", action="store_true", help="Test available backends")
    
    args = parser.parse_args()
    
    if not any([args.ollama, args.vllm, args.tgi, args.all, args.test]):
        print_usage_instructions()
        return
    
    if args.test:
        await test_all_backends()
        return
    
    if args.ollama or args.all:
        await setup_ollama()
    
    if args.vllm or args.all:
        setup_vllm()
    
    if args.tgi or args.all:
        setup_tgi()
    
    print("\n✅ Setup complete!")
    print("Run 'python setup_local_inference.py --test' to verify installation")

if __name__ == "__main__":
    asyncio.run(main())