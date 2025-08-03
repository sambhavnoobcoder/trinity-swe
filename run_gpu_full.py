#!/usr/bin/env python3
"""
Quick script to run Trinity-SWE on full dataset with GPU acceleration
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("🚀 Trinity-SWE GPU Full Dataset Runner")
    print("=====================================")
    
    # Check if GPU config is enabled
    config_file = Path("trinity_swe_qwen3_local.py")
    if not config_file.exists():
        print("❌ trinity_swe_qwen3_local.py not found!")
        sys.exit(1)
    
    with open(config_file, 'r') as f:
        content = f.read()
    
    if "# GPU_CONFIG = {" in content:
        print("⚠️  GPU configuration is commented out!")
        print("📝 Please edit trinity_swe_qwen3_local.py and uncomment GPU_CONFIG section")
        print("📖 See GPU_SETUP.md for detailed instructions")
        
        response = input("Continue anyway with CPU? (y/N): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    print("🏃 Starting full dataset prediction...")
    print("📊 Target: 500 instances from SWE-bench Verified")
    print("⏱️  Estimated time: 2-4 hours on GPU, much longer on CPU")
    
    try:
        # Run the main script
        subprocess.run([
            sys.executable, 
            "run_trinity_qwen3_local.py", 
            "--instances", "500"
        ], check=True)
        
        print("✅ Predictions completed!")
        print("📁 Results saved in: trinity_swe_qwen3_local_500/")
        print("📋 Next steps:")
        print("   1. Upload trinity_swe_qwen3_local_500/all_preds.jsonl to Hugging Face")
        print("   2. Visit: https://huggingface.co/spaces/swe-bench/leaderboard")
        print("   3. 🏆 Dominate the leaderboard!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Execution failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Execution interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()