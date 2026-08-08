## Windows CMD

```bat
python run_billion_search.py ^
  --data .\ODIN_ENRICHED_PDUFA_1349_v2.csv ^
  --top-configs .\ODIN_TOP_CONFIGS_V5.json ^
  --outdir .\outputs\v38a_gpu ^
  --iters 200000000 ^
  --batch 500000 ^
  --explore-frac 0.30 ^
  --sigma-frac 0.12 ^
  --device gpu
```
