$ErrorActionPreference = 'Stop'
$pfcLaunch = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'outputs/segmentacao_area_lancamento_2026-10-27.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$pfcMirror = $pfcLaunch.mirror_directory
$pfcProtocol = Get-Content -LiteralPath (Join-Path $pfcMirror 'protocolo_rodada.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($pfcSource in $pfcProtocol.source_hashes.PSObject.Properties) {
    $pfcActual = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $pfcSource.Name) -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($pfcActual -ne $pfcSource.Value) { throw "Fonte registrada divergente: $($pfcSource.Name)" }
}
$pfcPython = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-path.txt') -Raw).Trim()
$pfcPythonw = Join-Path (Split-Path -Parent $pfcPython) 'pythonw.exe'
$pfcSupervisor = Join-Path $PSScriptRoot 'executar_rodada_segmentacao_persistente.py'
& $pfcPython $pfcSupervisor --check-only
if ($LASTEXITCODE -ne 0) { throw 'Verificacao do supervisor falhou' }
$pfcTask = Get-ScheduledTask -TaskName $pfcLaunch.task_name
if ($pfcTask.Actions.Count -ne 1 -or $pfcTask.Actions[0].WorkingDirectory -ne $PSScriptRoot -or
    $pfcTask.Actions[0].Execute -ne $pfcPythonw -or
    (!$pfcTask.Actions[0].Arguments.Contains($pfcLaunch.script) -and !$pfcTask.Actions[0].Arguments.Contains($pfcSupervisor))) {
    throw 'Tarefa existente possui uma acao inesperada; nenhuma alteracao realizada'
}
$pfcAudit = Get-Content -LiteralPath (Join-Path $pfcMirror 'VERIFICACAO_RETOMADA_2026-11-03.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$pfcRecovery = Join-Path $pfcLaunch.runtime_directory 'retomada.pt'
if ($pfcTask.State -ne 'Running' -and !(Test-Path -LiteralPath (Join-Path $pfcMirror 'CONCLUIDO_RODADA.json'))) {
    if (!$pfcAudit.finite_model_and_optimizer -or !$pfcAudit.mirror_recovery_matches -or
        (Get-FileHash -LiteralPath $pfcRecovery -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pfcAudit.recovery_sha256) {
        throw 'Checkpoint mudou desde a auditoria; conferir antes de retomar'
    }
}
$pfcStamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$pfcBackup = Join-Path $pfcMirror "tarefa_antes_retomada_$pfcStamp.xml"
Export-ScheduledTask -TaskName $pfcTask.TaskName | Set-Content -LiteralPath $pfcBackup -Encoding UTF8
$pfcAction = New-ScheduledTaskAction -Execute $pfcPythonw -Argument ('-u "' + $pfcSupervisor + '"') -WorkingDirectory $PSScriptRoot
$pfcLogon = New-ScheduledTaskTrigger -AtLogOn -User $pfcTask.Principal.UserId
$pfcSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 24) -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
Set-ScheduledTask -TaskName $pfcTask.TaskName -Action $pfcAction -Trigger $pfcLogon -Settings $pfcSettings | Out-Null
if ($pfcTask.State -ne 'Running') { Start-ScheduledTask -TaskName $pfcTask.TaskName }
$pfcAfter = Get-ScheduledTask -TaskName $pfcTask.TaskName
$pfcReport = [ordered]@{
    checked_utc = (Get-Date).ToUniversalTime().ToString('o')
    task_name = $pfcAfter.TaskName
    state = $pfcAfter.State.ToString()
    automatic_resume_at_current_user_logon = $true
    restart_count_on_failure = 3
    restart_interval_minutes = 2
    completed_run_guard = $true
    temporary_idle_sleep_request_during_run = $true
    science_source_hashes_match = $true
    supervisor_sha256 = (Get-FileHash -LiteralPath $pfcSupervisor -Algorithm SHA256).Hash.ToLowerInvariant()
    previous_task_xml = $pfcBackup
}
$pfcReport | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $pfcMirror "RETOMADA_PERSISTENTE_$pfcStamp.json") -Encoding UTF8
$pfcReport | ConvertTo-Json
