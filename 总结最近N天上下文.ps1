param(
    [int]$Days = 7
)

$scriptPath = "C:\Users\Administrator\.openclaw\workspace\smart_context_summary.py"
python $scriptPath $Days
