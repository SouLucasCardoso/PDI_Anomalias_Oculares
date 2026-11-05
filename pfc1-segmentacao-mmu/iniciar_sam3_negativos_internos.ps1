$ErrorActionPreference='Stop'
$pfcTaskName='PFC_SAM3_Negativos_Internos_20261104'
$pfcPython=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-sam3-atual.txt') -Raw -Encoding UTF8).Trim()
$pfcPythonw=Join-Path (Split-Path -Parent $pfcPython) 'pythonw.exe'
$pfcMirror=Join-Path $PSScriptRoot 'outputs/sam31_negativos_internos_2026-11-04'
$pfcRun=Join-Path $env:TEMP 'pfc-s3-inner-20261104'
$pfcCache=Join-Path $env:TEMP 'pfc-sam3-iris-cache-20261103'
$pfcScript=Join-Path $PSScriptRoot 'executar_sam3_negativos_resiliente.py'
$pfcFlowScript=Join-Path $PSScriptRoot 'executar_sam3_negativos_internos.py'
if((Get-PSDrive -Name C).Free -lt 5GB){throw 'Reservar pelo menos5GB livres para retomada e escores; o cache existente sera reutilizado'}
& $pfcPython (Join-Path $PSScriptRoot 'treinar_sam3_negativos_internos.py') --run $pfcRun --cache $pfcCache --mirror $pfcMirror --epochs 12 --batch-size 16 --seed 20261104 --prepare
if($LASTEXITCODE -ne 0){throw 'Falha ao registrar treino'}
& $pfcPython $pfcFlowScript --prepare
if($LASTEXITCODE -ne 0){throw 'Falha ao registrar fluxo'}
& $pfcPython $pfcScript --register
if($LASTEXITCODE -ne 0){throw 'Falha ao validar controle operacional externo'}
$pfcExisting=Get-ScheduledTask -TaskName $pfcTaskName -ErrorAction SilentlyContinue
if($pfcExisting){
    if($pfcExisting.Actions.Count -ne 1 -or $pfcExisting.Actions[0].Execute -ne $pfcPythonw -or $pfcExisting.Actions[0].Arguments -ne ('-u "'+$pfcScript+'"') -or $pfcExisting.Actions[0].WorkingDirectory -ne $PSScriptRoot){throw 'Tarefa existente com outra acao'}
}else{
    $pfcUser=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $pfcAction=New-ScheduledTaskAction -Execute $pfcPythonw -Argument ('-u "'+$pfcScript+'"') -WorkingDirectory $PSScriptRoot
    $pfcPrincipal=New-ScheduledTaskPrincipal -UserId $pfcUser -LogonType Interactive -RunLevel Limited
    $pfcTrigger=New-ScheduledTaskTrigger -AtLogOn -User $pfcUser
    $pfcSettings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 24) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
    Register-ScheduledTask -TaskName $pfcTaskName -Action $pfcAction -Trigger $pfcTrigger -Principal $pfcPrincipal -Settings $pfcSettings -Description 'Continuacao SAM3.1 com negativos internos conhecidos, cache fechado, treino retomavel e identidade/area condicionais; somente treino/validacao, sem inferencia clinica automatica ou envio de dados.' | Out-Null
}
if((Get-ScheduledTask -TaskName $pfcTaskName).State -ne 'Running'){Start-ScheduledTask -TaskName $pfcTaskName}
[ordered]@{task_name=$pfcTaskName;run=$pfcRun;cache=$pfcCache;mirror=$pfcMirror;registered_utc=(Get-Date).ToUniversalTime().ToString('o');automatic_logon_resume=$true;identity_automatic_if_new_segmentation_candidate=$true;no_test_or_automatic_clinical_inference=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $pfcMirror 'AGENDAMENTO.json') -Encoding UTF8
Get-ScheduledTask -TaskName $pfcTaskName | Select-Object TaskName,State
