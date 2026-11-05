$ErrorActionPreference='Stop'
$appRoot=$PSScriptRoot
$adb=Join-Path $appRoot '.runtime/android_sdk/platform-tools/adb.exe'
if(-not(Test-Path -LiteralPath $adb)){throw 'Prepare as ferramentas oficiais com app_celular/preparar_usb.py antes de sair para a apresentacao.'}
$env:ANDROID_USER_HOME=Join-Path $appRoot 'dados_app_celular/android'
New-Item -ItemType Directory -Force $env:ANDROID_USER_HOME | Out-Null
Write-Host 'Conecte o S23 com cabo USB de dados. A autorizacao de depuracao deve ser feita por voce no celular.'
$ErrorActionPreference='Continue'
& $adb -P 5038 devices -l
$state=& $adb -P 5038 -d get-state 2>$null
$stateExit=$LASTEXITCODE
$ErrorActionPreference='Stop'
if($stateExit -ne 0 -or -not $state -or $state.Trim() -ne 'device'){
    Write-Host 'O celular ainda nao esta autorizado ou nao foi detectado. Consulte APP_CELULAR.md, secao USB.'
    exit 2
}
$forward=& $adb -P 5038 -d reverse --list
if($forward -notmatch 'tcp:8787\s+tcp:8787'){
    & $adb -P 5038 -d reverse --no-rebind tcp:8787 tcp:8787
    if($LASTEXITCODE -ne 0){throw 'Nao foi possivel encaminhar a porta. Nenhuma outra porta foi alterada.'}
}
& (Join-Path $appRoot 'iniciar_app_celular.ps1') -Usb
Write-Host 'No navegador do S23 abra http://127.0.0.1:8787 e toque em Conectar.'
Write-Host 'O cabo pode permanecer conectado durante as capturas. Nao precisa de internet.'
