$ErrorActionPreference='Stop'
$pfcTaskName='PFC_SAM3_Sensibilidade_Area_20261103'
$pfcPython=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-sam3-atual.txt') -Raw -Encoding UTF8).Trim()
$pfcPythonw=Join-Path (Split-Path -Parent $pfcPython) 'pythonw.exe'
$pfcScript=Join-Path $PSScriptRoot 'acompanhar_sensibilidade_area.py'
& $pfcPython $pfcScript
if($LASTEXITCODE -ne 0){throw 'Falha ao registrar a analise de sensibilidade'}
$pfcExisting=Get-ScheduledTask -TaskName $pfcTaskName -ErrorAction SilentlyContinue
if($pfcExisting){
    if($pfcExisting.Actions.Count -ne 1 -or $pfcExisting.Actions[0].Execute -ne $pfcPythonw -or $pfcExisting.Actions[0].WorkingDirectory -ne $PSScriptRoot -or !$pfcExisting.Actions[0].Arguments.Contains($pfcScript)){throw 'Tarefa existente possui outra acao'}
}else{
    $pfcUser=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $pfcAction=New-ScheduledTaskAction -Execute $pfcPythonw -Argument ('-u "'+$pfcScript+'"') -WorkingDirectory $PSScriptRoot
    $pfcPrincipal=New-ScheduledTaskPrincipal -UserId $pfcUser -LogonType Interactive -RunLevel Limited
    $pfcTriggers=@((New-ScheduledTaskTrigger -AtLogOn -User $pfcUser),(New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 2)))
    $pfcSettings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName $pfcTaskName -Action $pfcAction -Trigger $pfcTriggers -Principal $pfcPrincipal -Settings $pfcSettings -Description 'Sensibilidade observacional de area UBIPr: conserva 482 consultas, distingue 472 referencias definidas de 10 indefinidas; sem treino, inferencia ou alteracao do criterio primario.' | Out-Null
}
Start-ScheduledTask -TaskName $pfcTaskName
[ordered]@{checked_utc=(Get-Date).ToUniversalTime().ToString('o');task_name=$pfcTaskName;state=[string](Get-ScheduledTask -TaskName $pfcTaskName).State;interval_minutes=5;observes_only=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'outputs/sam31_iris_adaptacao_2026-11-03/sensibilidade_referencia/AGENDAMENTO.json') -Encoding UTF8
Get-ScheduledTask -TaskName $pfcTaskName | Select-Object TaskName,State
