#!/usr/bin/env python3
"""
Fix SWE-bench patch format issues for Trinity-SWE
"""

import json
import re
from pathlib import Path

def clean_patch(patch_content: str) -> str:
    """Clean and validate patch format for SWE-bench"""
    if not patch_content or len(patch_content.strip()) < 10:
        return ""
    
    lines = patch_content.split('\n')
    cleaned_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip empty lines at the start
        if not cleaned_lines and not line.strip():
            i += 1
            continue
            
        # File headers
        if line.startswith('--- ') or line.startswith('+++ '):
            cleaned_lines.append(line)
            i += 1
            continue
        
        # Hunk headers - fix malformed ones
        if line.startswith('@@'):
            # Extract hunk info and validate format
            hunk_match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@(.*)$', line)
            if hunk_match:
                old_start, old_count, new_start, new_count, context = hunk_match.groups()
                cleaned_line = f"@@ -{old_start},{old_count} +{new_start},{new_count} @@{context}"
                cleaned_lines.append(cleaned_line)
            else:
                # Try to fix common malformed hunk headers
                if '@@ -' in line and '+' in line and '@@' in line:
                    # Keep as is, might be parseable
                    cleaned_lines.append(line)
            i += 1
            continue
        
        # Content lines (context, additions, deletions)
        if line.startswith(' ') or line.startswith('+') or line.startswith('-'):
            cleaned_lines.append(line)
        elif line.strip() and cleaned_lines:  # Non-empty content line
            # Treat as context line if we're in a patch
            cleaned_lines.append(' ' + line)
        
        i += 1
    
    # Remove trailing empty lines
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()
    
    return '\n'.join(cleaned_lines)

def validate_patch(patch_content: str) -> bool:
    """Validate that patch has required format"""
    if not patch_content:
        return False
    
    lines = patch_content.split('\n')
    
    # Must have file headers
    has_minus_header = any(line.startswith('--- ') for line in lines)
    has_plus_header = any(line.startswith('+++ ') for line in lines)
    
    # Must have at least one hunk header
    has_hunk = any(line.startswith('@@') for line in lines)
    
    # Must have some changes
    has_changes = any(line.startswith(('+', '-')) and not line.startswith(('+++', '---')) 
                     for line in lines)
    
    return has_minus_header and has_plus_header and has_hunk and has_changes

def fix_predictions_file(input_file: str, output_file: str):
    """Fix all patches in a predictions file"""
    
    fixed_predictions = []
    
    with open(input_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                pred = json.loads(line.strip())
                
                original_patch = pred.get('model_patch', '')
                cleaned_patch = clean_patch(original_patch)
                
                if validate_patch(cleaned_patch):
                    pred['model_patch'] = cleaned_patch
                    fixed_predictions.append(pred)
                    print(f"✅ Fixed patch for {pred['instance_id']}")
                else:
                    print(f"❌ Could not fix patch for {pred['instance_id']}")
                    # Keep original for now
                    fixed_predictions.append(pred)
                
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                continue
    
    # Save fixed predictions
    with open(output_file, 'w') as f:
        for pred in fixed_predictions:
            f.write(json.dumps(pred) + '\n')
    
    print(f"Fixed {len(fixed_predictions)} predictions saved to {output_file}")

if __name__ == "__main__":
    # Fix test predictions
    fix_predictions_file(
        "trinity_swe_test_predictions.jsonl",
        "trinity_swe_test_predictions_fixed.jsonl"
    )
    
    # Fix full 50-instance predictions
    fix_predictions_file(
        "trinity_swe_qwen3_local_50/all_preds.jsonl",
        "trinity_swe_qwen3_local_50_fixed.jsonl"
    )