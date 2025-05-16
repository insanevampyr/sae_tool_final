# ─── check_accuracy.ps1 ────────────────────────────────────────────────────
# Usage: Open PowerShell in your project folder and run:
#    .\check_accuracy.ps1

# 1) Load the JSON log
$json = Get-Content .\prediction_log.json | Out-String | ConvertFrom-Json

# 2) Compute 24h cutoff
$cutoff = (Get-Date).ToUniversalTime().AddHours(-24)

# 3) Loop coins and tally
$json.PSObject.Properties | ForEach-Object {
  $coin    = $_.Name
  $entries = $_.Value |
             Where-Object { [DateTime]::Parse($_.timestamp) -gt $cutoff }
  $total   = $entries.Count
  $correct = ($entries | Where-Object { $_.accurate }).Count
  $pct     = if ($total -gt 0) { "{0:P0}" -f ($correct/$total) } else { "-" }

  # Note escaping of the colon so PS doesn’t treat it as part of the variable name
  Write-Host "${coin}:`t$correct/$total correct → $pct"
}
