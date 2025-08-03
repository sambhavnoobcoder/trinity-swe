#!/usr/bin/env python3
"""
Trinity-SWE: Multi-Agent Ensemble for SWE-bench
A three-model ensemble designed to beat current SOTA on SWE-bench.

Models:
- Analyzer: Qwen3-Coder-480B-A35B (Issue analysis, root cause detection)
- Generator: Qwen3-Coder-480B-A35B (Code generation, patch creation) 
- Validator: Qwen3-Coder-480B-A35B (Code review, validation, testing)
"""

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from together import Together
from datasets import load_dataset

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

class TrinityAgent:
    def __init__(self, role: str, model_name: str, api_key: str):
        self.role = role
        self.model_name = model_name
        self.client = Together(api_key=api_key)
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

Your role: Code generation and patch creation.

Given analysis from the Analyzer, create:
1. Concrete code patches
2. Implementation details
3. Test cases if needed
4. Documentation updates
5. Confidence score (0-1)

Generate WORKING, TESTED code. Focus on correctness and following existing patterns.""",

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
            response = await self._call_model(prompt)
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
    
    async def _call_model(self, prompt: str) -> str:
        """Call the appropriate model API"""
        import asyncio
        
        def _sync_call():
            response = self.client.chat.completions.create(
                model=self.model_name,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        
        # Run sync call in thread pool to maintain async compatibility
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_call)
    
    def _extract_confidence(self, response: str) -> float:
        """Extract confidence score from response"""
        # Simple regex/parsing for confidence score
        import re
        confidence_match = re.search(r'confidence[:\s]*([0-9.]+)', response.lower())
        if confidence_match:
            return min(1.0, max(0.0, float(confidence_match.group(1))))
        return 0.5  # Default confidence
    
    def _extract_reasoning(self, response: str) -> str:
        """Extract reasoning from response"""
        return response[:500]  # First 500 chars as reasoning summary

class TrinitySWE:
    def __init__(self, api_key: str):
        # Using Qwen3-Coder-480B-A35B for all agents
        model_name = "Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8"
        self.analyzer = TrinityAgent("analyzer", model_name, api_key)
        self.generator = TrinityAgent("generator", model_name, api_key) 
        self.validator = TrinityAgent("validator", model_name, api_key)
        
        self.results = []
        self.reasoning_traces = {}
    
    async def solve_issue(self, task_instance: Dict) -> EnsembleDecision:
        """Main ensemble solver pipeline"""
        instance_id = task_instance.get('instance_id', 'unknown')
        trace = [f"=== Trinity-SWE Processing: {instance_id} ==="]
        
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
        validator_approved = "reject" not in validator.content.lower()
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
                    "model_name_or_path": "trinity-swe-ensemble",
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
                    "model_name_or_path": "trinity-swe-ensemble", 
                    "confidence": 0.0,
                    "consensus": False
                })
        
        return predictions
    
    def save_submission_files(self, predictions: List[Dict], output_dir: str = "trinity_swe_submission"):
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
            "model_name": "Trinity-SWE Ensemble",
            "model_description": "Multi-agent ensemble with Qwen3-Coder-480B-A35B",
            "agents": {
                "analyzer": "Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8",
                "generator": "Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8", 
                "validator": "Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8"
            },
            "ensemble_method": "weighted_voting_with_validation",
            "submission_date": datetime.now().isoformat(),
            "total_predictions": len(predictions),
            "avg_confidence": sum(p.get("confidence", 0) for p in predictions) / len(predictions)
        }
        
        with open(output_path / "metadata.yaml", "w") as f:
            import yaml
            yaml.dump(metadata, f, default_flow_style=False)
        
        # 4. Save README
        readme_content = f"""# Trinity-SWE Submission

## Model Description
Trinity-SWE is a multi-agent ensemble system designed to solve GitHub issues on SWE-bench.

### Architecture
- **Analyzer**: Qwen3-Coder-480B-A35B - Deep issue analysis and root cause identification
- **Generator**: Qwen3-Coder-480B-A35B - Code generation and patch creation  
- **Validator**: Qwen3-Coder-480B-A35B - Code review and validation

### Ensemble Method
Weighted voting with validation gate. Each agent provides confidence scores, and the validator acts as a quality gate.

### Results
- Total Predictions: {len(predictions)}
- Average Confidence: {metadata['avg_confidence']:.3f}
- Submission Date: {metadata['submission_date']}

### Files
- `all_preds.jsonl`: Predictions in SWE-bench format
- `trajs/`: Reasoning traces for each instance
- `metadata.yaml`: Model metadata and configuration
"""
        
        with open(output_path / "README.md", "w") as f:
            f.write(readme_content)
        
        print(f"💾 Submission files saved to: {output_path}")
        print(f"📝 Ready for SWE-bench submission!")
        
        return output_path

async def main():
    """Demo run on a small subset"""
    
    # Use environment variable or provide Together AI API key
    import os
    api_key = os.getenv('TOGETHER_API_KEY', 'your-together-api-key-here')
    
    trinity = TrinitySWE(api_key)
    
    # Test on first 5 instances of SWE-bench Verified
    predictions = await trinity.evaluate_dataset(
        dataset_name="princeton-nlp/SWE-bench_Verified",
        max_instances=5
    )
    
    # Generate submission files
    submission_path = trinity.save_submission_files(predictions)
    
    print(f"🎯 Trinity-SWE ready to dominate SWE-bench!")
    print(f"📂 Submission files: {submission_path}")

if __name__ == "__main__":
    asyncio.run(main())