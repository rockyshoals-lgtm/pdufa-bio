#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  9REALMS — ODIN PDUFA EVOLVE: LightGBM FDA Approval Daemon             ║
║                                                                          ║
║  Thin wrapper around lgb_perpetual_daemon.py for dual-spear naming.     ║
║  Imports and runs the ODIN perpetual daemon directly.                    ║
║                                                                          ║
║  Data: ODIN_ENRICHED_1349.csv (FDA PDUFA events)                        ║
║  Target: outcome (APPROVAL=1, CRL=0)                                    ║
║  Kaizen: Shared engine via kaizen/ directory                             ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import sys
from pathlib import Path

# Ensure mcp_core is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lgb_perpetual_daemon import main

if __name__ == "__main__":
    main()
