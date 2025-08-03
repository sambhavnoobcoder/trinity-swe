#!/usr/bin/env python3
"""
Trinity-SWE Runner Script
Quick setup and execution script for SWE-bench evaluation
"""

import os
import asyncio
from trinity_swe import TrinitySWE

def setup_environment():
    """Setup environment and API keys"""
    api_key = os.getenv("TOGETHER_API_KEY")
    
    if not api_key:
        print("⚠️  Please set TOGETHER_API_KEY environment variable")
        print("   export TOGETHER_API_KEY='your-key-here'")
        print("   Get your key from: https://api.together.ai/settings/api-keys")
        return None
    
    return api_key

async def run_verified_subset(api_key: str, max_instances: int = 50):
    """Run Trinity-SWE on SWE-bench Verified subset"""
    
    print("🚀 Initializing Trinity-SWE...")
    trinity = TrinitySWE(api_key)
    
    print(f"📊 Evaluating {max_instances} instances from SWE-bench Verified...")
    predictions = await trinity.evaluate_dataset(
        dataset_name="princeton-nlp/SWE-bench_Verified",
        max_instances=max_instances
    )
    
    print("💾 Generating submission files...")
    submission_path = trinity.save_submission_files(
        predictions, 
        output_dir=f"trinity_swe_verified_{max_instances}"
    )
    
    print(f"\n🎯 Trinity-SWE Evaluation Complete!")
    print(f"📂 Submission ready: {submission_path}")
    print(f"📈 Processed: {len(predictions)} instances")
    
    # Quick stats
    successful = sum(1 for p in predictions if p.get("confidence", 0) > 0.5)
    print(f"✅ High confidence predictions: {successful}/{len(predictions)} ({successful/len(predictions)*100:.1f}%)")
    
    return submission_path

async def run_full_benchmark(api_key: str):
    """Run Trinity-SWE on full SWE-bench (expensive!)"""
    
    print("🔥 WARNING: Running on FULL SWE-bench (2,294 instances)")
    print("💰 This will be expensive (~6,000+ API calls using Qwen3-Coder)")
    
    confirm = input("Continue? (y/N): ")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return
    
    trinity = TrinitySWE(api_key)
    
    predictions = await trinity.evaluate_dataset(
        dataset_name="princeton-nlp/SWE-bench"
    )
    
    submission_path = trinity.save_submission_files(
        predictions,
        output_dir="trinity_swe_full_benchmark"
    )
    
    print(f"🏆 FULL SWE-bench evaluation complete!")
    print(f"📂 Submission: {submission_path}")
    
    return submission_path

def print_submission_instructions(submission_path):
    """Print instructions for SWE-bench submission"""
    
    print(f"\n📋 SWE-bench Submission Instructions:")
    print(f"1. Fork: https://github.com/swe-bench/experiments")
    print(f"2. Create folder: experiments/evaluation/verified/trinity-swe/")
    print(f"3. Copy files from: {submission_path}/")
    print(f"4. Create PR with your submission")
    print(f"5. 🚀 Watch Trinity-SWE dominate the leaderboard!")

async def main():
    """Main execution"""
    
    print("🔱 Trinity-SWE: Multi-Agent SWE-bench Dominator (Powered by Qwen3-Coder)")
    print("=" * 50)
    
    api_key = setup_environment()
    if not api_key:
        return
    
    print("\nChoose evaluation mode:")
    print("1. Quick test (5 instances)")
    print("2. Verified subset (50 instances) - Recommended")
    print("3. Full Verified (500 instances)")
    print("4. FULL SWE-bench (2,294 instances) - 💰 Expensive!")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        submission_path = await run_verified_subset(api_key, max_instances=5)
    elif choice == "2":
        submission_path = await run_verified_subset(api_key, max_instances=50)
    elif choice == "3":
        submission_path = await run_verified_subset(api_key, max_instances=500)
    elif choice == "4":
        submission_path = await run_full_benchmark(api_key)
    else:
        print("Invalid choice. Exiting.")
        return
    
    print_submission_instructions(submission_path)

if __name__ == "__main__":
    asyncio.run(main())