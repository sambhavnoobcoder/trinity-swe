#!/usr/bin/env python3
"""
Trinity-SWE with Local Inference Support
Modified version that uses local inference instead of API calls
"""

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datasets import load_dataset

from local_inference import LocalInferenceManager, InferenceConfig, PRESET_CONFIGS

@dataclass
class ModelResponse:
    content: str
    confidence: float
    reasoning: str
    model_role: str
    timestamp: str

@dataclass
class EnsembleDecision:
    final_patch: str
    confidence: float
    voting_breakdown: Dict[str, Any]
    reasoning_trace: List[str]
    consensus_reached: bool

class LocalTrinityAgent:
    def __init__(self, role: str, inference_manager: LocalInferenceManager):
        self.role = role
        self.inference_manager = inference_manager
        self.prompts = self._load_specialized_prompts()
    
    def _load_specialized_prompts(self) -> Dict[str, str]:
        """Load role-specific prompts optimized for each agent"""
        prompts = {
            "analyzer": """You are the ANALYZER in a multi-agent ensemble for solving GitHub issues.

Your role: Deep issue analysis and root cause identification.

Given a GitHub issue and codebase, provide:
1. Issue categorization (bug, feature, refactor, etc.)
2. Root cause analysis 
3. Affected code areas/files
4. Implementation strategy
5. Edge cases to consider
6. Confidence score (0-1)

Be thorough but concise. Focus on UNDERSTANDING the problem deeply.""",

            "generator": """You are the GENERATOR in a multi-agent ensemble for solving GitHub issues.

Your role: Generate EXECUTABLE CODE PATCHES for SWE-bench.

IMPORTANT: You must output ONLY the code patch/diff, not analysis.

Format your response as a git diff patch:
```diff
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -line_num,num_lines +line_num,num_lines @@
 context line
-old code line
+new code line
 context line
```

Focus on:
1. EXECUTABLE code changes only
2. Following existing code patterns
3. Minimal, targeted fixes
4. Confidence score (0-1) at the end

DO NOT provide explanations, analysis, or documentation - ONLY executable patches.""",

            "validator": """You are the VALIDATOR in a multi-agent ensemble for solving GitHub issues.

Your role: Code review and validation.

Given patches from the Generator, validate:
1. Code correctness and style
2. Edge case handling
3. Test coverage
4. Integration concerns
5. Potential breaking changes
6. Final recommendation (APPROVE/REJECT/MODIFY)
7. Confidence score (0-1)

Be critical but constructive. Focus on QUALITY and preventing regressions."""
        }
        return prompts
    
    async def process(self, task_data: Dict, context: Optional[Dict] = None) -> ModelResponse:
        """Process a task based on agent role"""
        prompt = self._build_prompt(task_data, context)
        
        try:
            response = await self.inference_manager.generate(prompt)
            confidence = self._extract_confidence(response)
            
            return ModelResponse(
                content=response,
                confidence=confidence,
                reasoning=self._extract_reasoning(response),
                model_role=self.role,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logging.error(f"Error in {self.role}: {e}")
            return ModelResponse(
                content="",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                model_role=self.role,
                timestamp=datetime.now().isoformat()
            )
    
    def _build_prompt(self, task_data: Dict, context: Optional[Dict] = None) -> str:
        """Build role-specific prompt"""
        base_prompt = self.prompts[self.role]
        
        issue_text = task_data.get('problem_statement', '')
        repo_info = task_data.get('repo', '')
        
        prompt = f"""{base_prompt}

## GitHub Issue
Repository: {repo_info}
Issue: {issue_text}

## Codebase Context
{task_data.get('repo_context', 'Limited context available')}
"""
        
        if context and self.role != "analyzer":
            prompt += f"\n## Previous Agent Analysis\n{context.get('previous_analysis', '')}"
        
        prompt += f"\n\nProvide your {self.role} response with confidence score:"
        
        return prompt
    
    def _extract_confidence(self, response: str) -> float:
        """Extract confidence score from response"""
        import re
        # Look for confidence patterns
        patterns = [
            r'confidence[:\s]*([0-9.]+)',
            r'confidence score[:\s]*([0-9.]+)', 
            r'score[:\s]*([0-9.]+)',
            r'\b([0-9]\.[0-9]+)\b'  # Any decimal number
        ]
        
        for pattern in patterns:
            confidence_match = re.search(pattern, response.lower())
            if confidence_match:
                score = float(confidence_match.group(1))
                if 0 <= score <= 1:
                    return score
                elif score > 1 and score <= 10:  # Handle 0-10 scale
                    return score / 10
        
        # Check for semantic confidence indicators
        response_lower = response.lower()
        if any(word in response_lower for word in ['high confidence', 'very confident', 'certain']):
            return 0.8
        elif any(word in response_lower for word in ['medium confidence', 'moderately confident']):
            return 0.6
        elif any(word in response_lower for word in ['low confidence', 'uncertain']):
            return 0.3
        
        return 0.5  # Default confidence
    
    def _extract_reasoning(self, response: str) -> str:
        """Extract reasoning from response"""
        return response[:500]  # First 500 chars as reasoning summary

class LocalTrinitySWE:
    def __init__(self, inference_configs: List[InferenceConfig]):
        """Initialize with local inference backends"""
        self.inference_manager = LocalInferenceManager(inference_configs)
        
        # Create agents using the same inference manager
        self.analyzer = LocalTrinityAgent("analyzer", self.inference_manager)
        self.generator = LocalTrinityAgent("generator", self.inference_manager)
        self.validator = LocalTrinityAgent("validator", self.inference_manager)
        
        self.results = []
        self.reasoning_traces = {}
    
    async def solve_issue(self, task_instance: Dict) -> EnsembleDecision:
        """Main ensemble solver pipeline"""
        instance_id = task_instance.get('instance_id', 'unknown')
        trace = [f"=== Trinity-SWE Local Processing: {instance_id} ==="]
        
        # Check available backends
        available_backends = await self.inference_manager.get_available_backends()
        trace.append(f"Available backends: {', '.join(available_backends)}")
        
        # Phase 1: Analysis
        trace.append("Phase 1: Deep Issue Analysis")
        analyzer_response = await self.analyzer.process(task_instance)
        trace.append(f"Analyzer Confidence: {analyzer_response.confidence:.2f}")
        trace.append(f"Analysis: {analyzer_response.reasoning}")
        
        # Phase 2: Generation  
        trace.append("Phase 2: Code Generation")
        generation_context = {"previous_analysis": analyzer_response.content}
        generator_response = await self.generator.process(task_instance, generation_context)
        trace.append(f"Generator Confidence: {generator_response.confidence:.2f}")
        trace.append(f"Generated Patch: {generator_response.reasoning}")
        
        # Phase 3: Validation
        trace.append("Phase 3: Code Validation")
        validation_context = {
            "previous_analysis": analyzer_response.content,
            "generated_patch": generator_response.content
        }
        validator_response = await self.validator.process(task_instance, validation_context)
        trace.append(f"Validator Confidence: {validator_response.confidence:.2f}")
        trace.append(f"Validation Result: {validator_response.reasoning}")
        
        # Phase 4: Ensemble Decision
        trace.append("Phase 4: Ensemble Decision Making")
        decision = self._make_ensemble_decision(
            analyzer_response, generator_response, validator_response, trace
        )
        
        # Store reasoning trace
        self.reasoning_traces[instance_id] = "\n".join(trace)
        
        return decision
    
    def _make_ensemble_decision(self, analyzer: ModelResponse, generator: ModelResponse, 
                              validator: ModelResponse, trace: List[str]) -> EnsembleDecision:
        """Ensemble voting and decision logic"""
        
        # Weighted confidence scoring
        weights = {"analyzer": 0.3, "generator": 0.5, "validator": 0.2}
        
        total_confidence = (
            analyzer.confidence * weights["analyzer"] +
            generator.confidence * weights["generator"] + 
            validator.confidence * weights["validator"]
        )
        
        # Simple consensus: Use generator's patch if validator doesn't reject
        validator_approved = "reject" not in validator.content.lower() and "approve" in validator.content.lower()
        consensus_reached = total_confidence > 0.6 and validator_approved
        
        if consensus_reached:
            final_patch = generator.content
            trace.append(f"✅ Consensus Reached - Confidence: {total_confidence:.2f}")
        else:
            # Fallback: Use best individual response
            best_response = max([analyzer, generator, validator], key=lambda x: x.confidence)
            final_patch = best_response.content
            trace.append(f"⚠️ No Consensus - Using Best Individual: {best_response.model_role}")
        
        voting_breakdown = {
            "analyzer_confidence": analyzer.confidence,
            "generator_confidence": generator.confidence,
            "validator_confidence": validator.confidence,
            "weighted_total": total_confidence,
            "validator_approved": validator_approved
        }
        
        return EnsembleDecision(
            final_patch=final_patch,
            confidence=total_confidence,
            voting_breakdown=voting_breakdown,
            reasoning_trace=trace.copy(),
            consensus_reached=consensus_reached
        )
    
    async def evaluate_dataset(self, dataset_name: str = "princeton-nlp/SWE-bench_Verified", 
                              max_instances: Optional[int] = None):
        """Evaluate on SWE-bench dataset"""
        
        print(f"🚀 Loading {dataset_name}...")
        dataset = load_dataset(dataset_name, split='test')
        
        if max_instances:
            dataset = dataset.select(range(min(max_instances, len(dataset))))
        
        print(f"📊 Evaluating {len(dataset)} instances...")
        
        predictions = []
        
        for i, instance in enumerate(dataset):
            print(f"Processing {i+1}/{len(dataset)}: {instance['instance_id']}")
            
            try:
                decision = await self.solve_issue(instance)
                
                prediction = {
                    "instance_id": instance['instance_id'],
                    "model_patch": decision.final_patch,
                    "model_name_or_path": "trinity-swe-local",
                    "confidence": decision.confidence,
                    "consensus": decision.consensus_reached
                }
                
                predictions.append(prediction)
                
            except Exception as e:
                logging.error(f"Error processing {instance['instance_id']}: {e}")
                
                # Add empty prediction to maintain order
                predictions.append({
                    "instance_id": instance['instance_id'],
                    "model_patch": "",
                    "model_name_or_path": "trinity-swe-local", 
                    "confidence": 0.0,
                    "consensus": False
                })
        
        return predictions
    
    def save_submission_files(self, predictions: List[Dict], output_dir: str = "trinity_swe_local_submission"):
        """Generate SWE-bench submission files"""
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 1. Save predictions
        with open(output_path / "all_preds.jsonl", "w") as f:
            for pred in predictions:
                f.write(json.dumps(pred) + "\n")
        
        # 2. Save reasoning traces
        trajs_dir = output_path / "trajs"
        trajs_dir.mkdir(exist_ok=True)
        
        for instance_id, trace in self.reasoning_traces.items():
            with open(trajs_dir / f"{instance_id}.md", "w") as f:
                f.write(trace)
        
        # 3. Save metadata
        metadata = {
            "model_name": "Trinity-SWE Local",
            "model_description": "Multi-agent ensemble with local inference",
            "inference_backends": [backend.config.backend for backend in self.inference_manager.backends],
            "ensemble_method": "weighted_voting_with_validation",
            "submission_date": datetime.now().isoformat(),
            "total_predictions": len(predictions),
            "avg_confidence": sum(p.get("confidence", 0) for p in predictions) / len(predictions)
        }
        
        with open(output_path / "metadata.yaml", "w") as f:
            import yaml
            yaml.dump(metadata, f, default_flow_style=False)
        
        print(f"💾 Submission files saved to: {output_path}")
        return output_path

async def setup_local_trinity():
    """Setup Trinity-SWE with available local backends"""
    print("🔍 Detecting available local inference backends...")
    
    # Try different configurations in order of preference
    configs_to_try = [
        PRESET_CONFIGS["vllm_qwen"],      # Best performance
        PRESET_CONFIGS["ollama_qwen"],    # Easy setup
        PRESET_CONFIGS["tgi_qwen"],       # HuggingFace option
        PRESET_CONFIGS["ollama_codellama"] # Fallback
    ]
    
    available_configs = []
    
    for config in configs_to_try:
        # Test if this backend is available
        from local_inference import LocalInferenceManager
        try:
            manager = LocalInferenceManager([config])
            backends = await manager.get_available_backends()
            if backends:
                available_configs.append(config)
                print(f"✅ Found {config.backend}: {config.model_name}")
        except Exception as e:
            print(f"❌ {config.backend} not available: {e}")
    
    if not available_configs:
        print("\n❌ No local inference backends found!")
        print("\nSetup instructions:")
        print("1. Ollama: curl -fsSL https://ollama.ai/install.sh | sh && ollama pull qwen2.5-coder:32b")
        print("2. vLLM: pip install vllm && python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-Coder-32B-Instruct")
        print("3. TGI: docker run --gpus all -p 3000:80 -v $PWD/data:/data ghcr.io/huggingface/text-generation-inference:1.4 --model-id Qwen/Qwen2.5-Coder-32B-Instruct")
        return None
    
    return LocalTrinitySWE(available_configs)

async def main():
    """Main function for local Trinity-SWE"""
    print("🔱 Trinity-SWE Local: No API Tokens Required!")
    print("=" * 50)
    
    trinity = await setup_local_trinity()
    if not trinity:
        return
    
    print("\nChoose evaluation mode:")
    print("1. Quick test (3 instances)")
    print("2. Small batch (10 instances)")
    print("3. Medium batch (50 instances)")
    print("4. Large batch (100 instances)")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    instance_counts = {"1": 3, "2": 10, "3": 50, "4": 100}
    max_instances = instance_counts.get(choice, 3)
    
    print(f"\n🚀 Running Trinity-SWE Local on {max_instances} instances...")
    
    predictions = await trinity.evaluate_dataset(
        dataset_name="princeton-nlp/SWE-bench_Verified",
        max_instances=max_instances
    )
    
    # Generate submission files
    submission_path = trinity.save_submission_files(
        predictions, 
        output_dir=f"trinity_swe_local_{max_instances}"
    )
    
    print(f"\n🎯 Trinity-SWE Local evaluation complete!")
    print(f"📂 Submission files: {submission_path}")
    print(f"📈 Processed: {len(predictions)} instances")
    
    # Quick stats
    successful = sum(1 for p in predictions if p.get("confidence", 0) > 0.5)
    print(f"✅ High confidence predictions: {successful}/{len(predictions)} ({successful/len(predictions)*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())