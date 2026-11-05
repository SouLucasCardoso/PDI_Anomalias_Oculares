$ErrorActionPreference='Stop'
$pfcTaskName='PFC_SAM3_Iris_Adaptacao_20261103'
$pfcPython=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-sam3-atual.txt') -Raw -Encoding UTF8).Trim()
$pfcPythonw=Join-Path (Split-Path -Parent $pfcPython) 'pythonw.exe'
$pfcMirror=Join-Path $PSScriptRoot 'outputs/sam31_iris_adaptacao_2026-11-03'
$pfcRun=Join-Path $env:TEMP 'pfc-sam3-iris-adaptado-20261103'
$pfcCache=Join-Path $env:TEMP 'pfc-sam3-iris-cache-20261103'
$pfcScript=Join-Path $PSScriptRoot 'executar_sam3_iris_adaptado.py'
if((Get-PSDrive -Name C).Free -lt 90GB){throw 'Reservar pelo menos90GB livres para cache e trabalho desta rodada'}
& $pfcPython (Join-Path $PSScriptRoot 'treinar_sam3_iris_adaptado.py') --run $pfcRun --cache $pfcCache --mirror $pfcMirror --wait-reference --epochs 20 --batch-size 16 --prepare
if($LASTEXITCODE -ne 0){throw 'Falha ao registrar protocolo SAM3'}
$pfcExisting=Get-ScheduledTask -TaskName $pfcTaskName -ErrorAction SilentlyContinue
if($pfcExisting){
    if($pfcExisting.Actions[0].Execute -ne $pfcPythonw -or !$pfcExisting.Actions[0].Arguments.Contains($pfcScript)){throw 'Tarefa existente com outra acao'}
}else{
    $pfcUser=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $pfcAction=New-ScheduledTaskAction -Execute $pfcPythonw -Argument ('-u "'+$pfcScript+'"') -WorkingDirectory $PSScriptRoot
    $pfcPrincipal=New-ScheduledTaskPrincipal -UserId $pfcUser -LogonType Interactive -RunLevel Limited
    $pfcTrigger=New-ScheduledTaskTrigger -AtLogOn -User $pfcUser
    $pfcSettings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 24) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
    Register-ScheduledTask -TaskName $pfcTaskName -Action $pfcAction -Trigger $pfcTrigger -Principal $pfcPrincipal -Settings $pfcSettings -Description 'Adaptacao supervisionada SAM3.1 local: aguarda a referencia, constroi cache e treina apenas treino/validacao; sem GT clinico automatico, teste final ou envio de dados.' | Out-Null
}
if((Get-ScheduledTask -TaskName $pfcTaskName).State -ne 'Running'){Start-ScheduledTask -TaskName $pfcTaskName}
[ordered]@{task_name=$pfcTaskName;run=$pfcRun;cache=$pfcCache;mirror=$pfcMirror;registered_utc=(Get-Date).ToUniversalTime().ToString('o');sam3_supervised_decoder=$true;automatic_logon_resume=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $pfcMirror 'AGENDAMENTO.json') -Encoding UTF8
Get-ScheduledTask -TaskName $pfcTaskName | Select-Object TaskName,State
