$src = "E:\大学\学术项目\Agent-ChemiVerse\数据库"
$dst = (Join-Path (Split-Path $PSScriptRoot -Parent) "data")
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$files = @("chemiverse_species.json", "chemiverse_reactions.json")
foreach ($name in $files) {
    $from = Join-Path $src $name
    $to = Join-Path $dst $name
    if (-not (Test-Path $from)) {
        Write-Error "Missing: $from"
        exit 1
    }
    Copy-Item -Force $from $to
    $mb = [math]::Round((Get-Item $to).Length / 1MB, 2)
    Write-Host "OK $name -> $to (${mb} MB)"
}
Write-Host ""
Write-Host "Next: git add data/chemiverse_*.json"
Write-Host "      git commit -m 'Add ChemiVerse database'"
Write-Host "      git push"
