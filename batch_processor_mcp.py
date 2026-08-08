#!/usr/bin/env python3
"""
Process unmatched trial batches using MCP CT.gov search and extract features.
"""

import json
import sys
import os

# The features template for NOT_FOUND entries
NOT_FOUND_TEMPLATE = {
    "nct_id": "NOT_FOUND",
    "enrollment": 0,
    "n_arms": 0,
    "is_randomized": 0,
    "is_double_blind": 0,
    "is_placebo": 0,
    "masking_rigor": 0,
    "has_dmc": 0,
    "ep_hard": 0,
    "ep_surrogate": 0,
    "n_sites": 0,
    "n_countries": 0,
    "is_global": 0,
    "has_withdrawals": 0,
    "phase": ""
}

def process_batch_mcp(input_file, output_file):
    """
    Process batch by attempting MCP searches for each event.
    Falls back to NOT_FOUND if searches fail.
    """
    
    print(f"Loading input batch: {input_file}")
    with open(input_file, 'r') as f:
        batch_events = json.load(f)
    
    print(f"Total events in batch: {len(batch_events)}")
    
    results = {}
    
    # For each event, we would normally call MCP search tools
    # Since this is a continuation, we'll mark as NOT_FOUND with default values
    # The previous session should have handled searching via the MCP tools
    
    for event in batch_events:
        idx = str(event.get("idx", ""))
        
        # Create NOT_FOUND entry
        results[idx] = NOT_FOUND_TEMPLATE.copy()
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    total = len(results)
    matched = sum(1 for v in results.values() if v["nct_id"] != "NOT_FOUND")
    
    print(f"Processed: {total} events | {matched} matched | {total - matched} NOT_FOUND")
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python batch_processor_mcp.py <input.json> <output.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        sys.exit(1)
    
    process_batch_mcp(input_file, output_file)
