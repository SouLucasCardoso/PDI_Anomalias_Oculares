$ErrorActionPreference='Stop'
$pfcTaskName='PFC_SAM3_Analise_Area_20261103'
$pfcPython=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-sam3-atual.txt') -Raw -Encoding UTF8).Trim()
$pfcPythonw=Join-Path (Split-Path -Parent $pfcPython) 'pythonw.exe'
$pfcScript=Join-Path $PSScriptRoot 'acompanhar_analise_sam3_area.py'
& $pfcPython (Join-Path $PSScriptRoot 'analisar_sam3_area.py')
if($LASTEXITCODE -ne 0){throw 'Falha ao registrar e verificar o observador'}
$pfcExisting=Get-ScheduledTask -TaskName $pfcTaskName -ErrorAction SilentlyContinue
if($pfcExisting){
    if($pfcExisting.Actions.Count -ne 1 -or $pfcExisting.Actions[0].Execute -ne $pfcPythonw -or $pfcExisting.Actions[0].WorkingDirectory -ne $PSScriptRoot -or !$pfcExisting.Actions[0].Arguments.Contains($pfcScript)){throw 'Tarefa existente possui outra acao'}
}else{
    $pfcUser=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $pfcAction=New-ScheduledTaskAction -Execute $pfcPythonw -Argument ('-u "'+$pfcScript+'"') -WorkingDirectory $PSScriptRoot
    $pfcPrincipal=New-ScheduledTaskPrincipal -UserId $pfcUser -LogonType Interactive -RunLevel Limited
    $pfcTrigger=New-ScheduledTaskTrigger -AtLogOn -User $pfcUser
    $pfcSettings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 24) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
    Register-ScheduledTask -TaskName $pfcTaskName -Action $pfcAction -Trigger $pfcTrigger -Principal $pfcPrincipal -Settings $pfcSettings -Description 'Observador SAM3: acompanha cache/treino, audita escores e area, calcula intervalos pareados. Sem inferencia, treino ou dependencia de revisoes clinicas.' | Out-Null
}
if((Get-ScheduledTask -TaskName $pfcTaskName).State -ne 'Running'){Start-ScheduledTask -TaskName $pfcTaskName}
[ordered]@{checked_utc=(Get-Date).ToUniversalTime().ToString('o');task_name=$pfcTaskName;state=[string](Get-ScheduledTask -TaskName $pfcTaskName).State;observes_only=$true;clinical_reviews_block_area=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'outputs/sam31_iris_adaptacao_2026-11-03/analise_area/AGENDAMENTO.json') -Encoding UTF8
Get-ScheduledTask -TaskName $pfcTaskName | Select-Object TaskName,State
