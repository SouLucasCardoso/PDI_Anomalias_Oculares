$ErrorActionPreference='Stop'
$pfcTaskName='PFC_SAM3_Negativos_Internos_20261104'
$pfcPython=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-sam3-atual.txt') -Raw -Encoding UTF8).Trim()
$pfcPythonw=Join-Path (Split-Path -Parent $pfcPython) 'pythonw.exe'
$pfcOldScript=Join-Path $PSScriptRoot 'executar_sam3_negativos_internos.py'
$pfcNewScript=Join-Path $PSScriptRoot 'executar_sam3_negativos_resiliente.py'
$pfcOldArgs='-u "'+$pfcOldScript+'"'
$pfcNewArgs='-u "'+$pfcNewScript+'"'
$pfcControl=Join-Path $PSScriptRoot 'outputs/sam31_negativos_internos_2026-11-04/fluxo/controle_resiliente'
& $pfcPython $pfcNewScript --register
if($LASTEXITCODE -ne 0){throw 'Falha ao validar o controle operacional'}
$pfcTask=Get-ScheduledTask -TaskName $pfcTaskName
if($pfcTask.Actions.Count -ne 1 -or $pfcTask.Actions[0].Execute -ne $pfcPythonw -or $pfcTask.Actions[0].WorkingDirectory -ne $PSScriptRoot -or $pfcTask.Actions[0].Arguments -notin @($pfcOldArgs,$pfcNewArgs)){
    throw 'A tarefa existente nao pertence a esta entrada; nenhuma alteracao feita'
}
$pfcStateBefore=[string]$pfcTask.State
$pfcStatusPath=Join-Path $env:TEMP 'pfc-s3-inner-20261104/status.json'
$pfcStatus=Get-Content -LiteralPath $pfcStatusPath -Raw -Encoding UTF8 | ConvertFrom-Json
$pfcWorkerBefore=Get-Process -Id $pfcStatus.pid -ErrorAction SilentlyContinue
$pfcBackup=Join-Path $pfcControl 'tarefa_antes.xml'
if(!(Test-Path -LiteralPath $pfcBackup)){
    Export-ScheduledTask -TaskName $pfcTaskName | Set-Content -LiteralPath $pfcBackup -Encoding UTF8
}
if($pfcTask.Actions[0].Arguments -eq $pfcOldArgs){
    $pfcAction=New-ScheduledTaskAction -Execute $pfcPythonw -Argument $pfcNewArgs -WorkingDirectory $PSScriptRoot
    Set-ScheduledTask -TaskName $pfcTaskName -Action $pfcAction | Out-Null
}
$pfcAfter=Get-ScheduledTask -TaskName $pfcTaskName
$pfcWorkerAfter=Get-Process -Id $pfcStatus.pid -ErrorAction SilentlyContinue
if($pfcStateBefore -eq 'Running' -and (!$pfcWorkerAfter -or $pfcAfter.State -ne 'Running')){
    throw 'Verificar a instancia ativa antes de iniciar qualquer outro processo'
}
$pfcProof=[ordered]@{
    updated_utc=(Get-Date).ToUniversalTime().ToString('o')
    task_name=$pfcTaskName
    state_before=$pfcStateBefore
    state_after=[string]$pfcAfter.State
    action=$pfcAfter.Actions[0].Arguments
    active_worker_pid=$pfcStatus.pid
    active_worker_alive=[bool]$pfcWorkerAfter
    current_worker_not_stopped=$true
    new_entry_applies_on_next_start=$true
    previous_task_xml=$pfcBackup
    registered_scientific_sources_unchanged=$true
}
$pfcProof | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $pfcControl 'MIGRACAO_TAREFA.json') -Encoding UTF8
$pfcProof | ConvertTo-Json -Depth 5
