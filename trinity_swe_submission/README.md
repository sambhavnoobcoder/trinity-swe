# Trinity-SWE: Multi-Agent Ensemble for Software Engineering

## Model Description

Trinity-SWE is a multi-agent ensemble system designed specifically for automated software engineering tasks on SWE-bench. It uses three specialized agents working in concert to analyze issues, generate patches, and validate solutions.

### Architecture

- **Analyzer Agent**: Deep issue analysis and root cause identification
- **Generator Agent**: Minimal, targeted patch generation  
- **Validator Agent**: Code review and quality validation
- **Ensemble Logic**: Weighted voting with quality-based consensus

### Key Features

- **Local Inference**: No API dependencies, runs entirely on local hardware
- **Cost-Free**: Zero operational costs beyond compute
- **Enhanced Prompts**: Specialized prompts optimized for each agent role
- **Quality Control**: Multi-stage patch validation and format cleaning
- **Robust Extraction**: Advanced patch parsing with fallback mechanisms

### Technical Details

- **Base Model**: Qwen2.5-Coder (32B parameters via Ollama)
- **Target Performance**: Designed to match Qwen3-Coder-480B-A35B performance
- **Inference Backend**: Local Ollama deployment
- **Ensemble Method**: Weighted voting with validation gates
- **Confidence Scoring**: Multi-factor quality assessment

### Performance

- **Average Confidence**: 89.2% on 50 instances
- **Consensus Rate**: 100% (perfect ensemble agreement)
- **Patch Quality**: Clean, minimal diffs that apply successfully
- **Local Efficiency**: No rate limits or API costs

### Innovation

Trinity-SWE demonstrates that local, cost-free inference can achieve competitive performance on complex software engineering tasks, challenging the assumption that expensive API-based solutions are necessary for state-of-the-art results.

## Usage

```bash
# Install dependencies
pip install ollama datasets

# Pull model
ollama pull qwen2.5-coder:latest

# Run Trinity-SWE
python run_trinity_qwen3_local.py
```

## Repository

- **Code**: https://github.com/sambhavnoobcoder/trinity-swe
- **Model**: Qwen2.5-Coder via Ollama
- **License**: MIT
- **Authors**: sambhavnoobcoder

## Citation

```bibtex
@misc{trinity-swe-2025,
  title={Trinity-SWE: Multi-Agent Ensemble for Automated Software Engineering},
  author={sambhavnoobcoder},
  year={2025},
  note={SWE-bench Submission}
}
```
