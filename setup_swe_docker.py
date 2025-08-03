#!/usr/bin/env python3
"""
Setup Docker images for SWE-bench evaluation
"""

import subprocess
import sys

def run_command(cmd, description):
    """Run shell command with error handling"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed")
            return True
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} error: {e}")
        return False

def setup_swe_bench_images():
    """Setup required Docker images for SWE-bench"""
    
    print("🚀 Setting up SWE-bench Docker environment...")
    
    # Build base images for the failing instances
    commands = [
        # Build missing astropy images
        ("python3 -m swebench.harness.docker_build --dataset_name princeton-nlp/SWE-bench_Verified --instance_ids astropy__astropy-13033", 
         "Building astropy-13033 image"),
        ("python3 -m swebench.harness.docker_build --dataset_name princeton-nlp/SWE-bench_Verified --instance_ids astropy__astropy-13453", 
         "Building astropy-13453 image"),
    ]
    
    success_count = 0
    for cmd, desc in commands:
        if run_command(cmd, desc):
            success_count += 1
    
    print(f"\n🎯 Docker setup complete: {success_count}/{len(commands)} images built successfully")
    
    if success_count < len(commands):
        print("\n⚠️ Some images failed to build. The evaluation will skip those instances.")
        print("This is normal for the first run. Re-running evaluation often resolves image issues.")
    
    return success_count > 0

if __name__ == "__main__":
    setup_swe_bench_images()