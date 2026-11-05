$ErrorActionPreference = 'Stop'
$pfcTaskName = 'PFC_Iris_Segmentacao_Area_20261027'
$pfcPython = (Get-Content (Join-Path $PSScriptRoot 'data/python-path.txt') -Raw).Trim()
$pfcPythonw = Join-Path (Split-Path -Parent $pfcPython) 'pythonw.exe'
$pfcScript = Join-Path $PSScriptRoot 'avaliar_area_segmentador_diverso.py'
$pfcRun = Join-Path $env:TEMP 'pfc-segmentacao-area-20261027'
$pfcMirror = Join-Path $PSScriptRoot 'outputs/segmentacao_area_2026-10-27'
if (!(Test-Path -LiteralPath $pfcPythonw)) { throw 'Pythonw ausente; nao iniciar tarefa sem executavel.' }
if (!(Test-Path -LiteralPath (Join-Path $pfcMirror 'protocolo_rodada.json'))) { throw 'Registrar e verificar protocolo antes do lancamento.' }
$pfcExisting = Get-ScheduledTask -TaskName $pfcTaskName -ErrorAction SilentlyContinue
if ($pfcExisting) { throw "Tarefa ja existe: $pfcTaskName. Inspecionar antes de iniciar outra instancia." }
$pfcArgs = '-u "' + $pfcScript + '" --run-root "' + $pfcRun + '" --mirror-root outputs/segmentacao_area_2026-10-27 --baseline-dir outputs/segmentacao_diversa_2026-10-27 --epochs 30'
$pfcAction = New-ScheduledTaskAction -Execute $pfcPythonw -Argument $pfcArgs -WorkingDirectory $PSScriptRoot
$pfcPrincipal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$pfcSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 24) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
$pfcTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(5)
Register-ScheduledTask -TaskName $pfcTaskName -Action $pfcAction -Trigger $pfcTrigger -Principal $pfcPrincipal -Settings $pfcSettings `
    -Description 'Rodada local autorizada: segmentacao diversa retomavel e avaliacao de identidade/area apenas na validacao. Sem envio de dados, teste final ou substituicao automatica do modelo.' | Out-Null
$pfcLaunch = [ordered]@{ task_name=$pfcTaskName; registered_utc=(Get-Date).ToUniversalTime().ToString('o');
    run_root=$pfcRun; runtime_directory=(Join-Path $pfcRun 'training'); mirror_directory=$pfcMirror;
    stdout=(Join-Path $pfcMirror 'execucao.log'); stderr=(Join-Path $pfcMirror 'execucao.log');
    execution_limit_hours=24; recurring=$false; epochs=30; batch_size=16; script=$pfcScript }
$pfcLaunch | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $PSScriptRoot 'outputs/segmentacao_area_lancamento_2026-10-27.json')
Get-ScheduledTask -TaskName $pfcTaskName | Select-Object TaskName,State
$pfcLaunch | ConvertTo-Json
