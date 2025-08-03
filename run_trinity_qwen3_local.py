#!/usr/bin/env python3
"""
Trinity-SWE Qwen3-Coder Local Runner Script
Local inference version targeting Qwen3-Coder models (no API tokens required)
"""

import os
import asyncio
from trinity_swe_qwen3_local import LocalTrinitySWEQwen3, setup_qwen3_trinity

async def run_local_evaluation(trinity: LocalTrinitySWEQwen3, max_instances: int = 50):
    """Run Trinity-SWE on SWE-bench Verified with local Qwen3-Coder"""
    
    print("🚀 Initializing Trinity-SWE Qwen3-Coder Local...")
    
    print(f"📊 Evaluating {max_instances} instances from SWE-bench Verified...")
    predictions = await trinity.evaluate_dataset(
        dataset_name="princeton-nlp/SWE-bench_Verified",
        max_instances=max_instances
    )
    
    print("💾 Generating submission files...")
    submission_path = trinity.save_submission_files(
        predictions, 
        output_dir=f"trinity_swe_qwen3_local_{max_instances}"
    )
    
    print(f"\n🎯 Trinity-SWE Qwen3-Coder Evaluation Complete!")
    print(f"📂 Submission ready: {submission_path}")
    print(f"📈 Processed: {len(predictions)} instances")
    
    # Enhanced stats
    successful = sum(1 for p in predictions if p.get("confidence", 0) > 0.5)
    high_confidence = sum(1 for p in predictions if p.get("confidence", 0) > 0.7)
    consensus = sum(1 for p in predictions if p.get("consensus", False))
    
    print(f"✅ High confidence predictions: {successful}/{len(predictions)} ({successful/len(predictions)*100:.1f}%)")
    print(f"🎯 Very high confidence: {high_confidence}/{len(predictions)} ({high_confidence/len(predictions)*100:.1f}%)")
    print(f"🤝 Consensus reached: {consensus}/{len(predictions)} ({consensus/len(predictions)*100:.1f}%)")
    
    return submission_path

def print_submission_instructions(submission_path):
    """Print instructions for SWE-bench submission"""
    
    print(f"\n📋 SWE-bench Submission Instructions:")
    print(f"1. Fork: https://github.com/swe-bench/experiments")
    print(f"2. Create folder: experiments/evaluation/verified/trinity-swe-qwen3-local/")
    print(f"3. Copy files from: {submission_path}/")
    print(f"4. Create PR with your submission")
    print(f"5. 🚀 Watch Trinity-SWE Qwen3-Coder climb the leaderboard!")

def print_setup_diagnostics():
    """Print diagnostic information about local setup"""
    print("\n🔧 Local Setup Diagnostics:")
    print("=" * 40)
    
    # Check for common local inference setups
    import subprocess
    import socket
    
    # Check Ollama
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Ollama detected")
            models = [line.split()[0] for line in result.stdout.split('\n')[1:] if line.strip()]
            qwen_models = [m for m in models if 'qwen' in m.lower()]
            if qwen_models:
                print(f"   Qwen models: {', '.join(qwen_models)}")
            else:
                print("   ⚠️  No Qwen models found. Install with: ollama pull qwen2.5-coder:32b")
        else:
            print("❌ Ollama not responding")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ Ollama not installed")
    
    # Check for vLLM/OpenAI compatible servers
    def check_port(port, name):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        if result == 0:
            print(f"✅ {name} detected on port {port}")
        else:
            print(f"❌ {name} not running on port {port}")
    
    check_port(8000, "vLLM/OpenAI API server")
    check_port(3000, "Text Generation Inference")
    check_port(11434, "Ollama API")
    
    print("\n📖 Setup Instructions:")
    print("1. Ollama (easiest): curl -fsSL https://ollama.ai/install.sh | sh")
    print("   Then: ollama pull qwen2.5-coder:32b")
    print("2. vLLM: pip install vllm")
    print("   Then: python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-Coder-32B-Instruct")
    print("3. TGI (Docker): docker run --gpus all -p 3000:80 ghcr.io/huggingface/text-generation-inference:1.4 --model-id Qwen/Qwen2.5-Coder-32B-Instruct")

async def main():
    """Main execution"""
    
    print("🔱 Trinity-SWE Qwen3-Coder Local: No API Keys Required!")
    print("🎯 Targeting Qwen3-Coder-480B-A35B performance with local models")
    print("=" * 70)
    
    # Setup local Trinity-SWE
    trinity = await setup_qwen3_trinity()
    if not trinity:
        print_setup_diagnostics()
        return
    
    print("\nChoose evaluation mode:")
    print("1. Quick test (2 instances) - Fast validation")
    print("2. Small batch (5 instances) - Algorithm testing") 
    print("3. Medium batch (20 instances) - Performance evaluation")
    print("4. Large batch (50 instances) - Comprehensive test")
    print("5. Full Verified (500 instances) - Complete evaluation")
    print("6. Custom amount")
    
    choice = input("\nEnter choice (1-6): ").strip()
    
    if choice == "1":
        max_instances = 2
    elif choice == "2":
        max_instances = 5
    elif choice == "3":
        max_instances = 20
    elif choice == "4":
        max_instances = 50
    elif choice == "5":
        max_instances = 500
    elif choice == "6":
        try:
            max_instances = int(input("Enter number of instances: ").strip())
            max_instances = max(1, min(max_instances, 2294))  # Reasonable bounds
        except ValueError:
            print("Invalid input. Using default of 5 instances.")
            max_instances = 5
    else:
        print("Invalid choice. Using default of 2 instances.")
        max_instances = 2
    
    print(f"\n🚀 Starting evaluation with {max_instances} instances...")
    print("💡 This uses local inference - no API costs!")
    
    submission_path = await run_local_evaluation(trinity, max_instances=max_instances)
    print_submission_instructions(submission_path)
    
    print(f"\n🏆 Trinity-SWE Qwen3-Coder Local evaluation complete!")
    print("💪 No API limits, no costs, just pure local AI power!")

if __name__ == "__main__":
    asyncio.run(main())