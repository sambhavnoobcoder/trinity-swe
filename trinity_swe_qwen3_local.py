#!/usr/bin/env python3
"""
Trinity-SWE with Local Qwen3-Coder Support
Modified version targeting Qwen3-Coder models for local inference
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

# GPU Configuration - Uncomment for GPU acceleration with HuggingFace models
# GPU_CONFIG = {
#     'backend': 'vllm',  # or 'tgi' for Text Generation Inference  
#     'model_name': 'Qwen/QwQ-32B-Preview',  # Qwen3-Coder equivalent via HuggingFace
#     'gpu_memory_utilization': 0.9,
#     'tensor_parallel_size': 1,  # Increase for multi-GPU
#     'max_model_len': 32768,
#     'dtype': 'bfloat16'
# }

# Ollama Configuration - For local Qwen3-Coder execution
QWEN3_CONFIG = {
    'backend': 'ollama',
    'model_name': 'qwen3-coder:30b',  # 30B params, 3.3B activated
    'context_length': 32768,  # Up to 256K supported
    'temperature': 0.1
}

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
        """Load role-specific prompts optimized for Qwen3-Coder"""
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

Format your response as:
## Analysis
[Your analysis here]

## Root Cause
[Root cause identification]

## Implementation Strategy
[Step-by-step approach]

## Confidence: [0.0-1.0]

Be thorough but concise. Focus on UNDERSTANDING the problem deeply.""",

            "generator": """You are the GENERATOR in a multi-agent ensemble for solving GitHub issues.

CRITICAL: Output ONLY a valid git diff patch. No explanations, no markdown, no extra text.

EXACT FORMAT REQUIRED:
--- a/filename.py
+++ b/filename.py
@@ -10,5 +10,6 @@
 existing code line
-line to remove
+line to add
 existing code line

RULES:
1. Start immediately with --- (no markdown blocks)
2. File paths must be real files from the repository
3. Line numbers must be accurate
4. Only add/remove/modify the minimum needed
5. End with a blank line
6. Maximum 20 lines of changes

EXAMPLE:
--- a/src/module.py
+++ b/src/module.py
@@ -15,3 +15,4 @@
 def function():
     return value
+    # fix applied

Confidence: 0.8""",

            "validator": """You are the VALIDATOR in a multi-agent ensemble for solving GitHub issues.

Your role: Code review and validation of generated patches.

Given patches from the Generator, validate:
1. Code correctness and style consistency
2. Edge case handling
3. Potential breaking changes
4. Integration concerns
5. Syntax and logic errors

Provide your assessment as:
## Validation Result
[APPROVE/REJECT/MODIFY]

## Issues Found
[List any problems or concerns]

## Recommendations
[Specific improvements if needed]

## Confidence: [0.0-1.0]

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
        """Build role-specific prompt optimized for Qwen3-Coder"""
        base_prompt = self.prompts[self.role]
        
        issue_text = task_data.get('problem_statement', '')
        repo_info = task_data.get('repo', '')
        
        # Enhanced context for better code understanding
        prompt = f"""{base_prompt}

## Repository Information
Repository: {repo_info}
Base commit: {task_data.get('base_commit', 'unknown')}

## GitHub Issue
{issue_text}

## Codebase Context
{task_data.get('repo_context', 'Limited context available')}
"""
        
        if context and self.role != "analyzer":
            if self.role == "generator":
                prompt += f"\n## Analysis from Analyzer\n{context.get('previous_analysis', '')}"
            elif self.role == "validator":
                prompt += f"\n## Analysis\n{context.get('previous_analysis', '')}"
                prompt += f"\n## Generated Patch\n{context.get('generated_patch', '')}"
        
        prompt += f"\n\nProvide your {self.role} response following the format above:"
        
        return prompt
    
    def _extract_confidence(self, response: str) -> float:
        """Extract confidence score from response"""
        import re
        
        # Look for confidence patterns with higher precision
        patterns = [
            r'confidence[:\s]*([0-9]\.[0-9]+)',
            r'confidence score[:\s]*([0-9]\.[0-9]+)',
            r'## confidence[:\s]*([0-9]\.[0-9]+)',
            r'confidence:\s*([0-9]\.[0-9]+)'
        ]
        
        for pattern in patterns:
            confidence_match = re.search(pattern, response.lower())
            if confidence_match:
                score = float(confidence_match.group(1))
                if 0 <= score <= 1:
                    return score
                elif score > 1 and score <= 10:  # Handle 0-10 scale
                    return score / 10
        
        # Semantic confidence indicators with adjusted scores
        response_lower = response.lower()
        if any(word in response_lower for word in ['high confidence', 'very confident', 'certain', 'definitely']):
            return 0.85
        elif any(word in response_lower for word in ['medium confidence', 'moderately confident', 'likely']):
            return 0.65
        elif any(word in response_lower for word in ['low confidence', 'uncertain', 'unsure']):
            return 0.35
        elif 'approve' in response_lower and self.role == 'validator':
            return 0.8
        elif 'reject' in response_lower and self.role == 'validator':
            return 0.2
        
        return 0.5  # Default confidence
    
    def _extract_reasoning(self, response: str) -> str:
        """Extract reasoning from response"""
        # Try to extract the first substantive section
        lines = response.split('\n')
        reasoning_lines = []
        
        for line in lines[:15]:  # First 15 lines
            if line.strip() and not line.startswith('#'):
                reasoning_lines.append(line.strip())
        
        return ' '.join(reasoning_lines)[:500]

class LocalTrinitySWEQwen3:
    def __init__(self, inference_configs: List[InferenceConfig]):
        """Initialize with local Qwen3-Coder inference backends"""
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
        trace = [f"=== Trinity-SWE Qwen3-Coder Local: {instance_id} ==="]
        
        # Check available backends
        available_backends = await self.inference_manager.get_available_backends()
        trace.append(f"Available backends: {', '.join(available_backends)}")
        
        # Phase 1: Analysis
        trace.append("Phase 1: Deep Issue Analysis (Qwen3-Coder)")
        analyzer_response = await self.analyzer.process(task_instance)
        trace.append(f"Analyzer Confidence: {analyzer_response.confidence:.3f}")
        trace.append(f"Analysis Preview: {analyzer_response.reasoning}")
        
        # Phase 2: Generation  
        trace.append("Phase 2: Code Generation (Qwen3-Coder)")
        generation_context = {"previous_analysis": analyzer_response.content}
        generator_response = await self.generator.process(task_instance, generation_context)
        trace.append(f"Generator Confidence: {generator_response.confidence:.3f}")
        
        # Extract patch from generator response
        patch_content = self._extract_patch(generator_response.content)
        trace.append(f"Generated Patch Length: {len(patch_content)} chars")
        
        # Phase 3: Validation
        trace.append("Phase 3: Code Validation (Qwen3-Coder)")
        validation_context = {
            "previous_analysis": analyzer_response.content,
            "generated_patch": patch_content
        }
        validator_response = await self.validator.process(task_instance, validation_context)
        trace.append(f"Validator Confidence: {validator_response.confidence:.3f}")
        trace.append(f"Validation Result: {validator_response.reasoning}")
        
        # Phase 4: Ensemble Decision
        trace.append("Phase 4: Ensemble Decision Making")
        decision = self._make_ensemble_decision(
            analyzer_response, generator_response, validator_response, trace, patch_content
        )
        
        # Store reasoning trace
        self.reasoning_traces[instance_id] = "\n".join(trace)
        
        return decision
    
    def _extract_patch(self, generator_content: str) -> str:
        """Extract and validate the actual patch from generator response"""
        import re
        
        # Remove any markdown blocks first
        content = generator_content.strip()
        if '```diff' in content:
            diff_pattern = r'```diff\n(.*?)\n```'
            diff_match = re.search(diff_pattern, content, re.DOTALL)
            if diff_match:
                content = diff_match.group(1).strip()
        elif '```' in content:
            # Remove any generic code blocks
            content = re.sub(r'```.*?\n(.*?)\n```', r'\1', content, flags=re.DOTALL)
        
        lines = content.split('\n')
        patch_lines = []
        in_patch = False
        
        for line in lines:
            line = line.rstrip()  # Remove trailing whitespace
            
            # Start patch extraction
            if line.startswith('--- '):
                in_patch = True
                patch_lines = [line]  # Reset and start fresh
            elif line.startswith('+++ ') and in_patch:
                patch_lines.append(line)
            elif line.startswith('@@') and in_patch:
                patch_lines.append(line)
            elif in_patch and (line.startswith(('+', '-', ' ')) or not line.strip()):
                patch_lines.append(line)
            elif line.startswith('Confidence:') and in_patch:
                break  # Stop at confidence
            elif in_patch and line and not line.startswith(('---', '+++')):
                # If we hit non-patch content, we might be done
                if any(c in line.lower() for c in ['explanation', 'note:', 'this', 'the']):
                    break
        
        if not patch_lines:
            return ""
        
        # Join and clean
        patch = '\n'.join(patch_lines)
        
        # Final validation and cleaning
        return self._validate_and_clean_patch(patch)
    
    def _clean_patch_format(self, patch: str) -> str:
        """Clean patch format for SWE-bench compatibility"""
        if not patch:
            return patch
            
        lines = patch.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Fix malformed hunk headers
            if line.startswith('@@'):
                import re
                hunk_match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@(.*)$', line)
                if hunk_match:
                    old_start, old_count, new_start, new_count, context = hunk_match.groups()
                    cleaned_line = f"@@ -{old_start},{old_count} +{new_start},{new_count} @@{context}"
                    cleaned_lines.append(cleaned_line)
                else:
                    # Keep original if it looks like a hunk header
                    if '@@ -' in line and '+' in line:
                        cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)
        
        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
            
        return '\n'.join(cleaned_lines)
    
    def _validate_and_clean_patch(self, patch: str) -> str:
        """Final validation and cleaning of extracted patch"""
        if not patch:
            return ""
        
        lines = patch.split('\n')
        cleaned = []
        
        # Must start with file headers
        if not any(line.startswith('--- ') for line in lines[:5]):
            return ""
        
        for line in lines:
            # Fix common issues
            line = line.rstrip()
            
            # File headers
            if line.startswith(('--- ', '+++ ')):
                cleaned.append(line)
            # Hunk headers - validate format
            elif line.startswith('@@'):
                import re
                if re.match(r'@@ -\d+,\d+ \+\d+,\d+ @@', line):
                    cleaned.append(line)
                else:
                    # Try to fix simple hunk headers
                    numbers = re.findall(r'\d+', line)
                    if len(numbers) >= 4:
                        context = line[line.rfind('@@')+2:] if line.count('@@') >= 2 else ''
                        fixed = f"@@ -{numbers[0]},{numbers[1]} +{numbers[2]},{numbers[3]} @@{context}"
                        cleaned.append(fixed)
            # Content lines
            elif line.startswith(('+', '-', ' ')):
                cleaned.append(line)
            # Empty lines in patch body
            elif not line and cleaned and not cleaned[-1].startswith('@@'):
                cleaned.append(line)
        
        result = '\n'.join(cleaned)
        
        # Final check - must have minimum structure
        if (result.count('--- ') >= 1 and 
            result.count('+++ ') >= 1 and 
            result.count('@@') >= 1):
            return result
        
        return ""
    
    def _is_valid_patch(self, patch: str) -> bool:
        """Validate patch format and quality"""
        if not patch or len(patch) < 10:
            return False
        
        # Check for basic diff format
        has_file_headers = ('---' in patch and '+++' in patch)
        has_hunk_headers = '@@' in patch
        has_changes = any(line.startswith(('+', '-')) for line in patch.split('\n'))
        
        # Check length (reject overly long patches)
        line_count = len(patch.split('\n'))
        if line_count > 100:  # Too verbose
            return False
        
        # Check for repetitive patterns (like the astropy issue)
        lines = patch.split('\n')
        unique_lines = set(lines)
        if len(lines) > 20 and len(unique_lines) / len(lines) < 0.3:  # Too repetitive
            return False
        
        return has_file_headers and (has_hunk_headers or has_changes)
    
    def _extract_fallback_patch(self, content: str) -> str:
        """Fallback patch extraction for edge cases"""
        lines = content.split('\n')
        
        # Look for any lines that look like code changes
        code_lines = []
        for line in lines:
            if (line.startswith(('+', '-', ' ', '@')) or 
                line.startswith(('---', '+++')) or
                'def ' in line or 'class ' in line or 'import ' in line):
                code_lines.append(line)
        
        return '\n'.join(code_lines[:50])  # Limit to 50 lines max
    
    def _make_ensemble_decision(self, analyzer: ModelResponse, generator: ModelResponse, 
                              validator: ModelResponse, trace: List[str], patch_content: str) -> EnsembleDecision:
        """Enhanced ensemble voting with improved decision logic"""
        
        # Improved weights - generator is most important for patch quality
        weights = {"analyzer": 0.20, "generator": 0.65, "validator": 0.15}
        
        # Calculate base confidence
        base_confidence = (
            analyzer.confidence * weights["analyzer"] +
            generator.confidence * weights["generator"] + 
            validator.confidence * weights["validator"]
        )
        
        # Enhanced validation logic with more nuanced approval
        validator_content_lower = validator.content.lower()
        strong_approval = "approve" in validator_content_lower and "reject" not in validator_content_lower
        moderate_approval = validator.confidence > 0.6 and "reject" not in validator_content_lower
        validator_approved = strong_approval or moderate_approval
        
        # Multi-factor patch quality assessment
        patch_quality_score = self._assess_enhanced_patch_quality(patch_content, generator.content)
        
        # Adaptive confidence calculation
        if validator_approved and patch_quality_score > 0.7:
            # High quality patch with validator approval - boost confidence
            adjusted_confidence = min(0.95, base_confidence * 1.15)
        elif patch_quality_score > 0.8:
            # Very high quality patch - trust it even without full validator approval
            adjusted_confidence = min(0.90, base_confidence * 1.05)
        else:
            # Apply quality penalty
            adjusted_confidence = base_confidence * patch_quality_score
        
        # Consensus threshold - more lenient for high-quality patches
        consensus_threshold = 0.5 if patch_quality_score > 0.7 else 0.6
        consensus_reached = adjusted_confidence > consensus_threshold and patch_quality_score > 0.4
        
        # Decision logic with iterative refinement capability
        if consensus_reached:
            final_patch = patch_content
            trace.append(f"✅ Consensus Reached - Quality:{patch_quality_score:.2f}, Confidence:{adjusted_confidence:.3f}")
        elif generator.confidence > 0.4 and patch_quality_score > 0.5:
            # Use generator output if it meets minimum standards
            final_patch = patch_content
            trace.append(f"⚠️ Moderate Quality - Using Generator - Quality:{patch_quality_score:.2f}")
        elif analyzer.confidence > 0.7:
            # High analyzer confidence but poor generation - use analysis as patch hint
            final_patch = self._generate_fallback_patch(analyzer.content, patch_content)
            trace.append(f"🔄 Using Analysis-Guided Fallback")
        else:
            # Last resort
            final_patch = patch_content if patch_content else generator.content
            trace.append(f"🚨 Emergency Fallback")
        
        voting_breakdown = {
            "analyzer_confidence": analyzer.confidence,
            "generator_confidence": generator.confidence,
            "validator_confidence": validator.confidence,
            "base_confidence": base_confidence,
            "patch_quality_score": patch_quality_score,
            "adjusted_confidence": adjusted_confidence,
            "validator_approved": validator_approved,
            "consensus_threshold": consensus_threshold
        }
        
        return EnsembleDecision(
            final_patch=final_patch,
            confidence=adjusted_confidence,
            voting_breakdown=voting_breakdown,
            reasoning_trace=trace.copy(),
            consensus_reached=consensus_reached
        )
    
    def _assess_enhanced_patch_quality(self, patch_content: str, raw_generator_content: str) -> float:
        """Enhanced patch quality assessment with multiple factors"""
        if not patch_content or len(patch_content.strip()) < 10:
            return 0.1
        
        quality_score = 0.3  # Base score
        
        # 1. Format quality (30% weight)
        if self._is_valid_patch(patch_content):
            quality_score += 0.25
        
        # 2. Length appropriateness (20% weight)
        line_count = len(patch_content.split('\n'))
        if 5 <= line_count <= 50:  # Sweet spot for most fixes
            quality_score += 0.20
        elif line_count <= 100:  # Acceptable but penalized
            quality_score += 0.10
        
        # 3. Content quality (25% weight)
        # Penalize verbose explanations in patch
        explanation_indicators = ['this function', 'this method', 'the issue', 'fix for', 'updated to']
        has_explanations = any(indicator in patch_content.lower() for indicator in explanation_indicators)
        if not has_explanations:
            quality_score += 0.15
        
        # Reward actual code changes
        has_real_changes = any(line.strip().startswith(('+', '-')) and 
                              not line.strip().startswith(('+++', '---')) 
                              for line in patch_content.split('\n'))
        if has_real_changes:
            quality_score += 0.10
        
        # 4. Repetition penalty (15% weight)
        lines = patch_content.split('\n')
        unique_lines = set(line.strip() for line in lines if line.strip())
        if len(lines) > 10:
            repetition_ratio = len(unique_lines) / len([l for l in lines if l.strip()])
            if repetition_ratio > 0.7:  # Good variety
                quality_score += 0.15
        else:
            quality_score += 0.15  # Short patches get benefit of doubt
        
        # 5. Coherence check (10% weight)
        # Check if patch makes logical sense (not just random code)
        has_coherent_structure = ('def ' in patch_content or 'class ' in patch_content or 
                                 'import ' in patch_content or 'return ' in patch_content or
                                 any(op in patch_content for op in ['==', '!=', '<=', '>=', '=']))
        if has_coherent_structure:
            quality_score += 0.10
        
        return min(1.0, quality_score)
    
    def _generate_fallback_patch(self, analyzer_content: str, failed_patch: str) -> str:
        """Generate a simple fallback patch based on analysis"""
        # Extract key information from analyzer content
        lines = analyzer_content.split('\n')
        
        # Look for specific suggestions or file mentions
        suggestions = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['should', 'need to', 'fix', 'add', 'remove', 'change']):
                suggestions.append(line.strip())
        
        if not suggestions:
            return failed_patch  # Return original if no better option
        
        # Create a minimal comment-based patch as fallback
        fallback_lines = [
            "# Based on analysis, this issue requires:",
            *[f"# - {suggestion}" for suggestion in suggestions[:3]],
            "",
            "# Manual implementation needed for:"
        ]
        
        return '\n'.join(fallback_lines)
    
    def _assess_patch_quality(self, patch_content: str) -> float:
        """Legacy patch quality assessment - kept for compatibility"""
        return self._assess_enhanced_patch_quality(patch_content, patch_content)
    
    async def evaluate_dataset(self, dataset_name: str = "princeton-nlp/SWE-bench_Verified", 
                              max_instances: Optional[int] = None):
        """Evaluate on SWE-bench dataset"""
        
        print(f"🚀 Loading {dataset_name}...")
        dataset = load_dataset(dataset_name, split='test')
        
        if max_instances:
            dataset = dataset.select(range(min(max_instances, len(dataset))))
        
        print(f"📊 Evaluating {len(dataset)} instances with Qwen3-Coder...")
        
        predictions = []
        
        for i, instance in enumerate(dataset):
            print(f"Processing {i+1}/{len(dataset)}: {instance['instance_id']}")
            
            try:
                decision = await self.solve_issue(instance)
                
                prediction = {
                    "instance_id": instance['instance_id'],
                    "model_patch": decision.final_patch,
                    "model_name_or_path": "trinity-swe-qwen3-local",
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
                    "model_name_or_path": "trinity-swe-qwen3-local", 
                    "confidence": 0.0,
                    "consensus": False
                })
        
        return predictions
    
    def save_submission_files(self, predictions: List[Dict], output_dir: str = "trinity_swe_qwen3_local"):
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
            "model_name": "Trinity-SWE Qwen3-Coder Local",
            "model_description": "Multi-agent ensemble with local Qwen3-Coder inference",
            "target_model": "Qwen3-Coder-480B-A35B (or compatible local model)",
            "inference_backends": [backend.config.backend for backend in self.inference_manager.backends],
            "ensemble_method": "weighted_voting_with_enhanced_validation",
            "submission_date": datetime.now().isoformat(),
            "total_predictions": len(predictions),
            "avg_confidence": sum(p.get("confidence", 0) for p in predictions) / len(predictions) if predictions else 0
        }
        
        with open(output_path / "metadata.yaml", "w") as f:
            import yaml
            yaml.dump(metadata, f, default_flow_style=False)
        
        print(f"💾 Submission files saved to: {output_path}")
        return output_path

# Predefined configurations for Qwen3-Coder models
QWEN3_PRESET_CONFIGS = {
    "vllm_qwen3_32b": InferenceConfig(
        backend="vllm",
        model_name="Qwen/Qwen2.5-Coder-32B-Instruct",  # Closest available
        base_url="http://localhost:8000",
        max_tokens=6000,
        temperature=0.1
    ),
    
    "ollama_qwen3": InferenceConfig(
        backend="ollama",
        model_name="qwen3-coder:30b",  # Actual Qwen3-Coder model (30B params, 3.3B activated)
        base_url="http://localhost:11434",
        max_tokens=6000,
        temperature=0.1
    ),
    
    "tgi_qwen3_32b": InferenceConfig(
        backend="tgi",
        model_name="Qwen/Qwen2.5-Coder-32B-Instruct",
        base_url="http://localhost:3000",
        max_tokens=6000,
        temperature=0.1
    ),
    
    # Experimental: larger model configs (if available)
    "vllm_qwen3_72b": InferenceConfig(
        backend="vllm",
        model_name="Qwen/Qwen2.5-Coder-72B-Instruct",
        base_url="http://localhost:8000",
        max_tokens=6000,
        temperature=0.05  # Lower temp for larger model
    )
}

async def setup_qwen3_trinity():
    """Setup Trinity-SWE with Qwen3-Coder local backends"""
    print("🔍 Detecting Qwen3-Coder compatible backends...")
    
    # Try configurations in order of preference (larger models first)
    configs_to_try = [
        QWEN3_PRESET_CONFIGS["vllm_qwen3_72b"],    # Best if available
        QWEN3_PRESET_CONFIGS["vllm_qwen3_32b"],    # Good performance
        QWEN3_PRESET_CONFIGS["ollama_qwen3"],      # Easy setup
        QWEN3_PRESET_CONFIGS["tgi_qwen3_32b"],     # HuggingFace option
    ]
    
    available_configs = []
    
    for config in configs_to_try:
        try:
            manager = LocalInferenceManager([config])
            backends = await manager.get_available_backends()
            if backends:
                available_configs.append(config)
                print(f"✅ Found {config.backend}: {config.model_name}")
        except Exception as e:
            print(f"❌ {config.backend} ({config.model_name}) not available")
    
    if not available_configs:
        print("\n❌ No Qwen3-Coder compatible backends found!")
        print("\nSetup instructions for Qwen3-Coder models:")
        print("1. Ollama: ollama pull qwen3-coder:30b")
        print("2. vLLM: python -m vllm.entrypoints.openai.api_server --model Qwen/QwQ-32B-Preview")
        print("3. TGI: docker run --gpus all -p 3000:80 ghcr.io/huggingface/text-generation-inference:1.4 --model-id Qwen/QwQ-32B-Preview")
        print("\nNote: Qwen3-Coder-480B-A35B is too large for most local setups.")
        print("      Using Qwen2.5-Coder-32B/72B as the best available alternative.")
        return None
    
    return LocalTrinitySWEQwen3(available_configs)

async def main():
    """Main function for Qwen3-Coder Trinity-SWE"""
    print("🔱 Trinity-SWE Qwen3-Coder Local: Advanced Code Generation")
    print("=" * 60)
    
    trinity = await setup_qwen3_trinity()
    if not trinity:
        return
    
    print("\nChoose evaluation mode:")
    print("1. Quick test (2 instances)")
    print("2. Small batch (5 instances)")
    print("3. Medium batch (20 instances)")
    print("4. Large batch (50 instances)")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    instance_counts = {"1": 2, "2": 5, "3": 20, "4": 50}
    max_instances = instance_counts.get(choice, 2)
    
    print(f"\n🚀 Running Trinity-SWE Qwen3-Coder on {max_instances} instances...")
    
    predictions = await trinity.evaluate_dataset(
        dataset_name="princeton-nlp/SWE-bench_Verified",
        max_instances=max_instances
    )
    
    # Generate submission files
    submission_path = trinity.save_submission_files(
        predictions, 
        output_dir=f"trinity_swe_qwen3_local_{max_instances}"
    )
    
    print(f"\n🎯 Trinity-SWE Qwen3-Coder evaluation complete!")
    print(f"📂 Submission files: {submission_path}")
    print(f"📈 Processed: {len(predictions)} instances")
    
    # Enhanced stats
    successful = sum(1 for p in predictions if p.get("confidence", 0) > 0.5)
    high_confidence = sum(1 for p in predictions if p.get("confidence", 0) > 0.7)
    
    print(f"✅ High confidence predictions: {successful}/{len(predictions)} ({successful/len(predictions)*100:.1f}%)")
    print(f"🎯 Very high confidence: {high_confidence}/{len(predictions)} ({high_confidence/len(predictions)*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())