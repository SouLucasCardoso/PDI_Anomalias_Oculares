$ErrorActionPreference = 'Stop'
$pfcLaunchFile = Join-Path $PSScriptRoot 'outputs/segmentacao_area_lancamento_2026-10-27.json'
if (!(Test-Path -LiteralPath $pfcLaunchFile)) { $pfcLaunchFile = Join-Path $PSScriptRoot 'outputs/segmentacao_diversa_lancamento_2026-10-27.json' }
$pfcLaunch = Get-Content -LiteralPath $pfcLaunchFile -Raw | ConvertFrom-Json
$pfcStageState = $null
$pfcParentAlive = $false
if ($pfcLaunch.run_root) {
    $pfcStage = Join-Path $pfcLaunch.run_root 'estado_rodada.json'
    if (Test-Path -LiteralPath $pfcStage) {
        $pfcStageState = Get-Content -LiteralPath $pfcStage -Raw | ConvertFrom-Json
        $pfcParentAlive = [bool](Get-Process -Id $pfcStageState.pid -ErrorAction SilentlyContinue)
        [pscustomobject]@{ stage=$pfcStageState.stage; pid=$pfcStageState.pid;
            process_alive=$pfcParentAlive; utc=$pfcStageState.utc; error=$pfcStageState.error } | Format-List
    }
}
$pfcStatePath = Join-Path $pfcLaunch.runtime_directory 'status.json'
$pfcProgressPath = Join-Path $pfcLaunch.runtime_directory 'progresso.json'
if (Test-Path -LiteralPath $pfcStatePath) {
    $pfcState = Get-Content -LiteralPath $pfcStatePath -Raw | ConvertFrom-Json
    $pfcAlive = [bool](Get-Process -Id $pfcState.pid -ErrorAction SilentlyContinue)
    $pfcStatus = $pfcState.status
    if ($pfcStatus -eq 'running' -and !$pfcAlive) {
        if ($pfcParentAlive -and $pfcStageState.stage -eq 'training') { $pfcStatus = 'starting_or_resuming_child' }
        else { $pfcStatus = 'interrupted_process_absent' }
    }
    [pscustomobject]@{ status=$pfcStatus; epoch=$pfcState.epoch; best_epoch=$pfcState.best_epoch;
        pid=$pfcState.pid; process_alive=$pfcAlive;
        error=$pfcState.error } | Format-List
}
if (Test-Path -LiteralPath $pfcProgressPath) { Get-Content -LiteralPath $pfcProgressPath -Raw }
if (Test-Path -LiteralPath $pfcLaunch.stdout) { Get-Content -LiteralPath $pfcLaunch.stdout -Tail 6 }
if ($pfcLaunch.stderr -ne $pfcLaunch.stdout -and (Test-Path -LiteralPath $pfcLaunch.stderr) -and (Get-Item -LiteralPath $pfcLaunch.stderr).Length -gt 0) { Get-Content -LiteralPath $pfcLaunch.stderr -Tail 12 }
