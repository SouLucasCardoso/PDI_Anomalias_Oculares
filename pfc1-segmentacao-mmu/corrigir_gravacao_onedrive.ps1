[CmdletBinding(SupportsShouldProcess=$true)]
param([switch]$AplicarPermissoes)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonVenv = Join-Path $env:USERPROFILE 'pfc-tcc-venv\Scripts\python.exe'
$pythonBase = Join-Path $repoRoot '.runtime\python312\python.exe'
$gitBlocked = Join-Path $env:ProgramFiles 'Git\ucrt64\bin\git.exe'
$apps = @($pythonVenv, $pythonBase, $gitBlocked)
foreach ($app in $apps) {
    if (-not (Test-Path -LiteralPath $app -PathType Leaf)) { throw "Executavel ausente: $app" }
}
Write-Host 'Plano: permitir somente estes executaveis no Acesso Controlado a Pastas:'
$apps | ForEach-Object { Write-Host "  $_" }
Write-Host 'Isso permite que esses programas gravem nas pastas protegidas do Windows.'
Write-Host 'Nao altera antivirus, pastas protegidas, exclusoes de varredura ou o OneDrive.'
if (-not $AplicarPermissoes) {
    Write-Host 'Somente plano. Para aplicar, executar como administrador com -AplicarPermissoes.'
    return
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'A alteracao do Defender exige PowerShell aberto como administrador.'
}
$preferences = Get-MpPreference
$before = @($preferences.ControlledFolderAccessAllowedApplications | Where-Object { $_ })
$missing = @($apps | Where-Object { $_ -notin $before })
if ($WhatIfPreference) {
    foreach ($app in $missing) { [void]$PSCmdlet.ShouldProcess($app, 'Permitir no Acesso Controlado a Pastas') }
    return
}
$backupRoot = Join-Path $env:USERPROFILE 'pfc-tcc-backups'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$configFile = Join-Path $backupRoot "defender_antes_$stamp.json"
if ($PSCmdlet.ShouldProcess($configFile, 'Salvar configuracao anterior')) {
    [pscustomobject]@{BeforeAllowedApplications=$before;PlannedAdditions=$missing;ControlledFolderAccessMode=$preferences.EnableControlledFolderAccess} |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $configFile -Encoding UTF8
}
foreach ($app in $missing) {
    if ($PSCmdlet.ShouldProcess($app, 'Permitir no Acesso Controlado a Pastas')) {
        Add-MpPreference -ControlledFolderAccessAllowedApplications $app
    }
}
$after = Get-MpPreference
if ($after.EnableControlledFolderAccess -ne $preferences.EnableControlledFolderAccess) { throw 'Modo de protecao mudou; interrompendo.' }
foreach ($app in $apps) {
    if ($app -notin $after.ControlledFolderAccessAllowedApplications) { throw "Permissao nao confirmada: $app" }
}
Write-Host "Permissoes confirmadas. Configuracao anterior: $configFile"
& $pythonVenv (Join-Path $PSScriptRoot 'sincronizar_backups_onedrive.py')
if ($LASTEXITCODE -ne 0) { throw 'A verificacao/copia dos backups falhou; conferir a mensagem acima.' }
Write-Host 'Backups copiados e verificados na pasta do OneDrive. Confirmar o upload no icone do OneDrive.'
