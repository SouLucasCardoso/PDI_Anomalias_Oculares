$ErrorActionPreference='Stop'
$pfcTaskName='PFC_SAM3_Prontidao_Anomalias_20261103'
$pfcPython=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-sam3-atual.txt') -Raw -Encoding UTF8).Trim()
$pfcPythonw=Join-Path (Split-Path -Parent $pfcPython) 'pythonw.exe'
$pfcScript=Join-Path $PSScriptRoot 'executar_avaliacao_sam3_persistente.py'
$pfcLegacyScript=Join-Path $PSScriptRoot 'acompanhar_prontidao_anomalias.py'
$pfcExisting=Get-ScheduledTask -TaskName $pfcTaskName -ErrorAction SilentlyContinue
if($pfcExisting){
    if($pfcExisting.Actions.Count -ne 1 -or $pfcExisting.Actions[0].Execute -ne $pfcPythonw -or $pfcExisting.Actions[0].WorkingDirectory -ne $PSScriptRoot){throw 'Tarefa existente possui outra acao'}
    if(!$pfcExisting.Actions[0].Arguments.Contains($pfcScript)){
        if(!$pfcExisting.Actions[0].Arguments.Contains($pfcLegacyScript)){throw 'Tarefa existente possui outro script'}
        if([string]$pfcExisting.State -eq 'Running'){throw 'Avaliador antigo ainda ativo; preservar processo e aguardar termino antes de migrar supervisor'}
        $pfcBackup=Join-Path $PSScriptRoot 'outputs/prontidao_anomalias_2026-11-03/controle_tarefa'
        New-Item -ItemType Directory -Path $pfcBackup -Force | Out-Null
        $pfcStamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
        Export-ScheduledTask -TaskName $pfcTaskName | Set-Content -LiteralPath (Join-Path $pfcBackup ($pfcStamp+'_antes_supervisor.xml')) -Encoding UTF8
        $pfcAction=New-ScheduledTaskAction -Execute $pfcPythonw -Argument ('-u "'+$pfcScript+'"') -WorkingDirectory $PSScriptRoot
        Set-ScheduledTask -TaskName $pfcTaskName -Action $pfcAction | Out-Null
    }
}else{
    $pfcUser=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $pfcAction=New-ScheduledTaskAction -Execute $pfcPythonw -Argument ('-u "'+$pfcScript+'"') -WorkingDirectory $PSScriptRoot
    $pfcPrincipal=New-ScheduledTaskPrincipal -UserId $pfcUser -LogonType Interactive -RunLevel Limited
    $pfcTrigger=New-ScheduledTaskTrigger -AtLogOn -User $pfcUser
    $pfcSettings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 24) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
    Register-ScheduledTask -TaskName $pfcTaskName -Action $pfcAction -Trigger $pfcTrigger -Principal $pfcPrincipal -Settings $pfcSettings -Description 'SAM3: valida identidade em controles pareados, calcula curva condicional de area e acompanha referencias humanas; piloto de anomalias depende dos criterios registrados.' | Out-Null
}
if((Get-ScheduledTask -TaskName $pfcTaskName).State -ne 'Running'){Start-ScheduledTask -TaskName $pfcTaskName}
Get-ScheduledTask -TaskName $pfcTaskName | Select-Object TaskName,State
