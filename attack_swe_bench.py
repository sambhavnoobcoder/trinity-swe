#!/usr/bin/env python3
"""
Trinity-SWE Local: Attack SWE-bench!
Direct execution script to dominate SWE-bench without API costs
"""

import asyncio
from trinity_swe_local import setup_local_trinity

async def attack_swe_bench():
    """Launch aggressive SWE-bench attack"""
    print("🔱 TRINITY-SWE LOCAL: ATTACKING SWE-BENCH!")
    print("=" * 50)
    print("💥 NO API TOKENS REQUIRED!")
    print("🎯 TARGET: SWE-bench Verified")
    print("⚡ INFERENCE: Local Ollama")
    print("=" * 50)
    
    # Setup Trinity with available backends
    print("\n🚀 Initializing Trinity-SWE Local...")
    trinity = await setup_local_trinity()
    if not trinity:
        print("❌ Setup failed!")
        return
    
    # Attack configurations - choose your weapon!
    attack_modes = {
        "stealth": {"instances": 5, "desc": "Stealth mode - Quick test run"},
        "assault": {"instances": 25, "desc": "Assault mode - Medium attack"},
        "domination": {"instances": 50, "desc": "Domination mode - Heavy attack"}, 
        "annihilation": {"instances": 100, "desc": "Total annihilation - Maximum attack"}
    }
    
    # Let's go with assault mode for a good balance
    mode = "assault"
    config = attack_modes[mode]
    
    print(f"\n⚔️  ATTACK MODE: {mode.upper()}")
    print(f"📈 TARGET INSTANCES: {config['instances']}")
    print(f"📝 STRATEGY: {config['desc']}")
    print(f"\n🔥 LAUNCHING ATTACK IN 3... 2... 1... GO!")
    
    # Execute the attack!
    predictions = await trinity.evaluate_dataset(
        dataset_name="princeton-nlp/SWE-bench_Verified",
        max_instances=config['instances']
    )
    
    # Generate battle report
    submission_path = trinity.save_submission_files(
        predictions, 
        output_dir=f"trinity_swe_attack_{config['instances']}"
    )
    
    # Victory statistics
    total = len(predictions)
    high_confidence = sum(1 for p in predictions if p.get("confidence", 0) > 0.7)
    medium_confidence = sum(1 for p in predictions if 0.5 <= p.get("confidence", 0) <= 0.7)
    consensus_reached = sum(1 for p in predictions if p.get("consensus", False))
    
    print(f"\n" + "="*50)
    print(f"🏆 TRINITY-SWE ATTACK COMPLETE!")
    print(f"=" * 50)
    print(f"📊 BATTLE STATISTICS:")
    print(f"   • Total Instances Attacked: {total}")
    print(f"   • High Confidence Kills: {high_confidence} ({high_confidence/total*100:.1f}%)")
    print(f"   • Medium Confidence Hits: {medium_confidence} ({medium_confidence/total*100:.1f}%)")
    print(f"   • Consensus Victories: {consensus_reached} ({consensus_reached/total*100:.1f}%)")
    print(f"   • Average Confidence: {sum(p.get('confidence', 0) for p in predictions)/total:.3f}")
    print(f"\n📂 WAR CHEST: {submission_path}")
    print(f"🎯 READY FOR SWE-BENCH SUBMISSION!")
    
    # Taunt the competition
    print(f"\n💬 TRASH TALK:")
    print(f"   🔥 Zero API costs, maximum damage!")  
    print(f"   ⚡ Local inference, global domination!")
    print(f"   🎖️  Trinity-SWE: The people's champion!")
    
    return submission_path

async def rapid_fire_mode():
    """Rapid fire mode - multiple quick attacks"""
    print("🔥 RAPID FIRE MODE ACTIVATED!")
    
    trinity = await setup_local_trinity()
    if not trinity:
        return
    
    # Quick successive attacks
    for round_num in range(3):
        print(f"\n⚡ ROUND {round_num + 1}: RAPID FIRE!")
        
        predictions = await trinity.evaluate_dataset(
            dataset_name="princeton-nlp/SWE-bench_Verified", 
            max_instances=5
        )
        
        success_rate = sum(1 for p in predictions if p.get("confidence", 0) > 0.5) / len(predictions)
        print(f"   💥 Round {round_num + 1} success rate: {success_rate*100:.1f}%")
    
    print(f"\n🏆 RAPID FIRE COMPLETE! TRINITY-SWE UNSTOPPABLE!")

if __name__ == "__main__":
    # Choose your attack mode
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--rapid":
        asyncio.run(rapid_fire_mode())
    else:
        asyncio.run(attack_swe_bench())