#!/usr/bin/env python3
"""
Quick test of Trinity-SWE system
"""

import asyncio
import json
from trinity_swe import TrinitySWE

async def test_trinity_swe():
    """Test Trinity-SWE with a small sample"""
    
    print("🔱 Testing Trinity-SWE System (Powered by Qwen3-Coder)...")
    
    # Use environment variable for Together API key
    import os
    api_key = os.getenv('TOGETHER_API_KEY')
    
    if not api_key:
        print("⚠️  Please set TOGETHER_API_KEY environment variable")
        print("   export TOGETHER_API_KEY='your-key-here'")
        print("   Get your key from: https://api.together.ai/settings/api-keys")
        return False
    
    trinity = TrinitySWE(api_key)
    
    print("📊 Testing on 1 instance from SWE-bench Verified...")
    
    try:
        predictions = await trinity.evaluate_dataset(
            dataset_name="princeton-nlp/SWE-bench_Verified",
            max_instances=1
        )
        
        print(f"✅ Success! Processed {len(predictions)} instances")
        
        # Show results
        for i, pred in enumerate(predictions):
            print(f"\nInstance {i+1}: {pred['instance_id']}")
            print(f"Confidence: {pred['confidence']:.3f}")
            print(f"Consensus: {pred['consensus']}")
            print(f"Patch Length: {len(pred['model_patch'])} chars")
        
        # Generate submission files
        print("\n💾 Generating submission files...")
        submission_path = trinity.save_submission_files(
            predictions, 
            output_dir="trinity_test_submission"
        )
        
        print(f"🎯 Test Complete! Files saved to: {submission_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_trinity_swe())
    
    if success:
        print("\n🚀 Trinity-SWE is ready for full evaluation!")
        print("Next steps:")
        print("1. Run full SWE-bench Verified (500 instances)")
        print("2. Submit to leaderboard")
        print("3. Watch Trinity-SWE dominate! 🏆")
    else:
        print("\n⚠️ Fix issues before proceeding to full evaluation")