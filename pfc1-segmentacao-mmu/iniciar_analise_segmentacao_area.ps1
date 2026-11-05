$ErrorActionPreference = 'Stop'
$pfcTaskName = 'PFC_Iris_Relatorio_Area_20261027'
$pfcPython = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-path.txt') -Raw).Trim()
$pfcPythonw = Join-Path (Split-Path -Parent $pfcPython) 'pythonw.exe'
$pfcScript = Join-Path $PSScriptRoot 'acompanhar_analise_segmentacao_area.py'
$pfcOut = Join-Path $PSScriptRoot 'outputs/segmentacao_area_2026-10-27/analise'
$pfcProtocol = Get-Content -LiteralPath (Join-Path $pfcOut 'protocolo_analise.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'analisar_rodada_segmentacao_area.py') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pfcProtocol.source_sha256) {
    throw 'Analise divergente do registro; nao iniciar'
}
$pfcExisting = Get-ScheduledTask -TaskName $pfcTaskName -ErrorAction SilentlyContinue
if ($pfcExisting) {
    if ($pfcExisting.Actions.Count -ne 1 -or $pfcExisting.Actions[0].Execute -ne $pfcPythonw -or
        $pfcExisting.Actions[0].WorkingDirectory -ne $PSScriptRoot -or !$pfcExisting.Actions[0].Arguments.Contains($pfcScript)) {
        throw 'Tarefa de mesmo nome possui outra acao; nenhuma alteracao realizada'
    }
} else {
    $pfcUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $pfcAction = New-ScheduledTaskAction -Execute $pfcPythonw -Argument ('-u "' + $pfcScript + '"') -WorkingDirectory $PSScriptRoot
    $pfcPrincipal = New-ScheduledTaskPrincipal -UserId $pfcUser -LogonType Interactive -RunLevel Limited
    $pfcTrigger = New-ScheduledTaskTrigger -AtLogOn -User $pfcUser
    $pfcSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 24) -StartWhenAvailable `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew `
        -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
    Register-ScheduledTask -TaskName $pfcTaskName -Action $pfcAction -Trigger $pfcTrigger -Principal $pfcPrincipal -Settings $pfcSettings `
        -Description 'Relatorio local observacional da rodada de iris: aguarda resultados, audita escores e arquiva evidencias. Sem treino, inferencia, recalibracao ou envio de dados.' | Out-Null
}
if ((Get-ScheduledTask -TaskName $pfcTaskName).State -ne 'Running') { Start-ScheduledTask -TaskName $pfcTaskName }
$pfcResult = [ordered]@{
    checked_utc = (Get-Date).ToUniversalTime().ToString('o')
    task_name = $pfcTaskName
    state = (Get-ScheduledTask -TaskName $pfcTaskName).State.ToString()
    analysis_sha256 = $pfcProtocol.source_sha256
    observer_sha256 = (Get-FileHash -LiteralPath $pfcScript -Algorithm SHA256).Hash.ToLowerInvariant()
    automatic_resume_at_current_user_logon = $true
    observes_only = $true
}
$pfcResult | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $pfcOut 'AGENDAMENTO.json') -Encoding UTF8
$pfcResult | ConvertTo-Json
