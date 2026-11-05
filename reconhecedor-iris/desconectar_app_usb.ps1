$ErrorActionPreference='Stop'
$adb=Join-Path $PSScriptRoot '.runtime/android_sdk/platform-tools/adb.exe'
if(Test-Path -LiteralPath $adb){
    $env:ANDROID_USER_HOME=Join-Path $PSScriptRoot 'dados_app_celular/android'
    & $adb -P 5038 -d reverse --remove tcp:8787
}
& (Join-Path $PSScriptRoot 'parar_app_celular.ps1')
Write-Host 'Desative a depuracao USB no S23 quando terminar. Cadastro local preservado.'
