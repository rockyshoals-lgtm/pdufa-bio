import subprocess
import json
import os

# --- CONFIGURATION ---
SCRIPT_NAME = "gpt_v2_6_honing.py"
DATA_FILE = "historical_readouts_2000.csv"
INPUT_JSON = "odin_phase_v2.2_strategist.json"
OUTPUT_JSON = "odin_phase_v2.2_refined.json"
STATE_FILE = "odin_optimizer.state.json"
LOG_CSV = "learning_trace.csv"

# Hyper-parameters for the loop
STEPS_PER_EPOCH = 500
CONVERGENCE_THRESHOLD = 0.000001  # Stop if Brier improvement is less than this
MAX_ITERATIONS = 20

def run_honing_iteration(is_first_run):
    cmd = [
        "python", SCRIPT_NAME,
        "--data", DATA_FILE,
        "--input_json", INPUT_JSON,
        "--output", OUTPUT_JSON,
        "--state_out", STATE_FILE,
        "--steps", str(STEPS_PER_EPOCH),
        "--log_csv", LOG_CSV,
        "--append_log"
    ]
    
    # After the first run, always resume from the state file
    if not is_first_run:
        cmd.extend(["--state_in", STATE_FILE])
    
    subprocess.run(cmd)

def get_best_brier():
    if not os.path.exists(STATE_FILE):
        return float('inf')
    with open(STATE_FILE, "r") as f:
        data = json.load(f)
        return data.get("best_val_brier", float('inf'))

def main():
    last_brier = float('inf')
    print(f"🚀 Starting Auto-Learning loop...")

    for i in range(MAX_ITERATIONS):
        print(f"\n--- Iteration {i+1} ---")
        
        run_honing_iteration(is_first_run=(i == 0))
        
        current_brier = get_best_brier()
        improvement = last_brier - current_brier
        
        print(f"Current Best Brier: {current_brier:.6f}")
        print(f"Improvement: {improvement:.6f}")

        if improvement < CONVERGENCE_THRESHOLD and i > 0:
            print(f"✅ Convergence reached. Stopping.")
            break
            
        last_brier = current_brier

    print(f"\n✨ Auto-Learning Complete. Final model: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()