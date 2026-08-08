## Example commands

### 50M iteration local refinement
```bash
python run_billion_search.py   --data ./ODIN_ENRICHED_PDUFA_1349_v2.csv   --top-configs ./ODIN_TOP_CONFIGS_V5.json   --outdir ./outputs/v38a_50m   --iters 50000000   --batch 250000   --min-precision 0.94   --explore-frac 0.10   --sigma-frac 0.08
```

### More exploration (wider search)
```bash
python run_billion_search.py   --data ./ODIN_ENRICHED_PDUFA_1349_v2.csv   --top-configs ./ODIN_TOP_CONFIGS_V5.json   --outdir ./outputs/v38a_wide   --iters 200000000   --batch 500000   --explore-frac 0.30   --sigma-frac 0.12
```
