# PowerShell wrapper for ODIN v38a signal discovery
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = "$ScriptDir;" + $env:PYTHONPATH
python (Join-Path $ScriptDir "run_v38a_signal_discovery.py") @args
