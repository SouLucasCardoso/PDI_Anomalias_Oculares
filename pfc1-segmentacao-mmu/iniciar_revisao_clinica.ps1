$ErrorActionPreference='Stop'
$pfcTaskName='PFC_Iris_Revisao_Clinica_20261103'
$pfcPython=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-sam3-atual.txt') -Raw -Encoding UTF8).Trim()
$pfcPythonw=Join-Path (Split-Path -Parent $pfcPython) 'pythonw.exe'
$pfcScript=Join-Path $PSScriptRoot 'revisar_mascaras_clinicas.py'
$pfcExisting=Get-ScheduledTask -TaskName $pfcTaskName -ErrorAction SilentlyContinue
if($pfcExisting){
    if($pfcExisting.Actions[0].Execute -ne $pfcPythonw -or !$pfcExisting.Actions[0].Arguments.Contains($pfcScript)){throw 'Tarefa existente possui outra acao'}
}else{
    $pfcUser=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $pfcAction=New-ScheduledTaskAction -Execute $pfcPythonw -Argument ('-u "'+$pfcScript+'" --port 8766') -WorkingDirectory $PSScriptRoot
    $pfcPrincipal=New-ScheduledTaskPrincipal -UserId $pfcUser -LogonType Interactive -RunLevel Limited
    $pfcTrigger=New-ScheduledTaskTrigger -AtLogOn -User $pfcUser
    $pfcSettings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 24) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
    Register-ScheduledTask -TaskName $pfcTaskName -Action $pfcAction -Trigger $pfcTrigger -Principal $pfcPrincipal -Settings $pfcSettings -Description 'Editor de referencias humanas de iris, somente127.0.0.1:8766, sem envio de dados ou aprovacao automatica.' | Out-Null
}
if((Get-ScheduledTask -TaskName $pfcTaskName).State -ne 'Running'){Start-ScheduledTask -TaskName $pfcTaskName}
Get-ScheduledTask -TaskName $pfcTaskName | Select-Object TaskName,State
