#!/usr/bin/env python3
"""
Test script for local Trinity-SWE setup
"""

import asyncio
from local_inference import PRESET_CONFIGS, LocalInferenceManager

async def test_simple_generation():
    """Test basic generation with available backends"""
    print("🧪 Testing Trinity-SWE local inference...")
    
    # Try Ollama backends first
    configs_to_test = [
        PRESET_CONFIGS["ollama_qwen"],
        PRESET_CONFIGS["ollama_codellama"]
    ]
    
    for config in configs_to_test:
        try:
            manager = LocalInferenceManager([config])
            available = await manager.get_available_backends()
            
            if available:
                print(f"✅ Testing {config.backend} with {config.model_name}")
                
                # Test generation
                test_prompt = """Analyze this simple Python function:

def add_numbers(a, b):
    return a + b

Provide:
1. Brief description
2. Confidence score (0-1)
"""
                
                response = await manager.generate(test_prompt)
                if response:
                    print(f"✅ Generation successful!")
                    print(f"Response preview: {response[:200]}...")
                    return True
                else:
                    print(f"❌ Generation returned empty response")
            else:
                print(f"❌ {config.backend} not available")
                
        except Exception as e:
            print(f"❌ Error testing {config.backend}: {e}")
    
    return False

async def test_trinity_pipeline():
    """Test the full Trinity-SWE pipeline with a simple example"""
    try:
        from trinity_swe_local import LocalTrinitySWE, PRESET_CONFIGS
        
        print("\n🔱 Testing Trinity-SWE pipeline...")
        
        # Use available configs
        configs = [PRESET_CONFIGS["ollama_qwen"]]  # Start with one that works
        
        trinity = LocalTrinitySWE(configs)
        
        # Create a simple test instance
        test_instance = {
            "instance_id": "test-001",
            "problem_statement": "Fix a simple bug where the add function doesn't handle None values",
            "repo": "test-repo",
            "repo_context": """
def add(a, b):
    return a + b  # Bug: doesn't handle None values

# Tests expect None values to return 0
assert add(1, 2) == 3
assert add(None, 5) == 5  # This should work
assert add(3, None) == 3  # This should work
"""
        }
        
        print("Running Trinity-SWE analysis...")
        decision = await trinity.solve_issue(test_instance)
        
        print(f"✅ Trinity-SWE completed!")
        print(f"Confidence: {decision.confidence:.2f}")
        print(f"Consensus: {decision.consensus_reached}")
        print(f"Patch preview: {decision.final_patch[:300]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Trinity-SWE pipeline test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🔱 Trinity-SWE Local Testing Suite")
    print("=" * 40)
    
    # Test 1: Basic generation
    basic_test = await test_simple_generation()
    
    if basic_test:
        print("\n" + "="*40)
        # Test 2: Full pipeline
        pipeline_test = await test_trinity_pipeline()
        
        if pipeline_test:
            print("\n🎉 All tests passed! Trinity-SWE Local is ready!")
            print("\nNext steps:")
            print("1. Run: python3 trinity_swe_local.py")
            print("2. Choose your evaluation size")
            print("3. Enjoy API-free SWE-bench evaluation!")
        else:
            print("\n⚠️ Pipeline test failed, but basic generation works")
    else:
        print("\n❌ Basic generation test failed")
        print("Setup instructions:")
        print("1. Install Ollama: curl -fsSL https://ollama.ai/install.sh | sh")
        print("2. Pull model: ollama pull qwen2.5-coder:7b")
        print("3. Start service: ollama serve")

if __name__ == "__main__":
    asyncio.run(main())