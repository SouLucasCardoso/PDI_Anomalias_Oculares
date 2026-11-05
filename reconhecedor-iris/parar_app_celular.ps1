$ErrorActionPreference='Stop'
$statusFile=Join-Path $PSScriptRoot 'dados_app_celular/servidor.json'
if(-not(Test-Path -LiteralPath $statusFile)){Write-Host 'Nenhum servidor registrado.';exit}
$status=Get-Content -LiteralPath $statusFile -Raw | ConvertFrom-Json
$recorded=Get-CimInstance Win32_Process -Filter "ProcessId = $($status.pid)" -ErrorAction SilentlyContinue
$expected=Join-Path $PSScriptRoot 'app_celular\servidor.py'
if($recorded -and $recorded.CommandLine.Contains($expected)){
    $launcher=Get-CimInstance Win32_Process -Filter "ProcessId = $($recorded.ParentProcessId)" -ErrorAction SilentlyContinue
    Stop-Process -Id $recorded.ProcessId
    Wait-Process -Id $recorded.ProcessId -Timeout 5 -ErrorAction SilentlyContinue
    if($launcher -and $launcher.CommandLine -and $launcher.CommandLine.Contains($expected) -and $launcher.Name -eq 'pythonw.exe'){
        Stop-Process -Id $launcher.ProcessId -ErrorAction SilentlyContinue
        Wait-Process -Id $launcher.ProcessId -Timeout 5 -ErrorAction SilentlyContinue
    }
    Write-Host 'Aplicativo do celular encerrado. Cadastro preservado.'
}else{Write-Host 'O processo registrado nao esta ativo. Nenhum outro processo foi encerrado.'}
