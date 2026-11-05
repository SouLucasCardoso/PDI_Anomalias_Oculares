$ErrorActionPreference='Stop'
$pfcTaskName='PFC_SAM3_Residual_20261105'
$pfcPython=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-sam3-atual.txt') -Raw -Encoding UTF8).Trim()
$pfcPythonw=Join-Path (Split-Path -Parent $pfcPython) 'pythonw.exe'
$pfcMirror=Join-Path $PSScriptRoot 'outputs/sam31_residual_2026-11-05'
$pfcRun=Join-Path $env:TEMP 'pfc-s3-residual-20261105'
$pfcCache=Join-Path $env:TEMP 'pfc-sam3-iris-cache-20261103'
$pfcScript=Join-Path $PSScriptRoot 'executar_sam3_residual.py'
$env:MPLCONFIGDIR=Join-Path $env:TEMP 'pfc-matplotlib'
if((Get-PSDrive -Name C).Free -lt 5GB){throw 'Reservar pelo menos5GB livres para pesos, retomada e escores'}
& $pfcPython (Join-Path $PSScriptRoot 'treinar_sam3_residual.py') --run $pfcRun --cache $pfcCache --mirror $pfcMirror --epochs 24 --batch-size 8 --seed 20261105 --prepare
if($LASTEXITCODE -ne 0){throw 'Falha ao registrar o treino residual'}
& $pfcPython $pfcScript --prepare
if($LASTEXITCODE -ne 0){throw 'Falha ao registrar o fluxo residual'}
$pfcExisting=Get-ScheduledTask -TaskName $pfcTaskName -ErrorAction SilentlyContinue
if($pfcExisting){
    if($pfcExisting.Actions.Count -ne 1 -or $pfcExisting.Actions[0].Execute -ne $pfcPythonw -or $pfcExisting.Actions[0].Arguments -ne ('-u "'+$pfcScript+'"') -or $pfcExisting.Actions[0].WorkingDirectory -ne $PSScriptRoot){throw 'Tarefa existente com outra acao'}
}else{
    $pfcUser=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $pfcAction=New-ScheduledTaskAction -Execute $pfcPythonw -Argument ('-u "'+$pfcScript+'"') -WorkingDirectory $PSScriptRoot
    $pfcPrincipal=New-ScheduledTaskPrincipal -UserId $pfcUser -LogonType Interactive -RunLevel Limited
    $pfcTrigger=New-ScheduledTaskTrigger -AtLogOn -User $pfcUser
    $pfcSettings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 24) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
    Register-ScheduledTask -TaskName $pfcTaskName -Action $pfcAction -Trigger $pfcTrigger -Principal $pfcPrincipal -Settings $pfcSettings -Description 'Cabeca de correcao residual SAM3.1: base e extrator congelados, treino retomavel, observador isolado e identidade/area condicionais. Apenas treino/validacao; sem inferencia clinica automatica ou envio de dados.' | Out-Null
}
if((Get-ScheduledTask -TaskName $pfcTaskName).State -ne 'Running'){Start-ScheduledTask -TaskName $pfcTaskName}
[ordered]@{task_name=$pfcTaskName;run=$pfcRun;cache=$pfcCache;mirror=$pfcMirror;registered_utc=(Get-Date).ToUniversalTime().ToString('o');automatic_logon_resume=$true;report_failures_isolated=$true;identity_automatic_if_new_segmentation_candidate=$true;no_test_or_automatic_clinical_inference=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $pfcMirror 'AGENDAMENTO.json') -Encoding UTF8
Get-ScheduledTask -TaskName $pfcTaskName | Select-Object TaskName,State
