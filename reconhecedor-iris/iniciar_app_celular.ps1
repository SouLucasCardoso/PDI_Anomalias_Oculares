param([int]$Porta=8787,[switch]$RedeLocal,[switch]$Usb)
$ErrorActionPreference='Stop'
$appRoot=$PSScriptRoot
$researchRoot=Join-Path (Split-Path $appRoot) 'pfc1-segmentacao-mmu'
$appData=Join-Path $appRoot 'dados_app_celular'
$python=(Get-Content -LiteralPath (Join-Path $researchRoot 'data/python-sam3-atual.txt') -Raw).Trim()
$pythonw=Join-Path (Split-Path $python) 'pythonw.exe'
$ipLocal='127.0.0.1'
if($RedeLocal){
    $ipList=@(Get-NetIPConfiguration | Where-Object {$_.IPv4DefaultGateway -and $_.IPv4Address} | ForEach-Object {$_.IPv4Address.IPAddress})
    if($ipList.Count -eq 0){throw 'Conecte o PC ao hotspot do S23 ou a uma rede local.'}
    $ipLocal=$ipList[0]
}
$existing=Get-NetTCPConnection -LocalPort $Porta -State Listen -ErrorAction SilentlyContinue
if($existing){
    if(($RedeLocal -and $existing.LocalAddress -eq '127.0.0.1') -or ($Usb -and $existing.LocalAddress -ne '127.0.0.1')){
        throw 'Encerre o demonstrador com parar_app_celular.ps1 antes de trocar entre USB e Wi-Fi.'
    }
    Write-Host "A porta $Porta ja esta em uso. Abra http://localhost:$Porta ou consulte dados_app_celular/execucao.log."
    exit 0
}
New-Item -ItemType Directory -Force -Path $appData | Out-Null
Set-Content -LiteralPath (Join-Path $appData '.gitignore') -Value '*'
$env:HF_HOME=(Get-Content -LiteralPath (Join-Path $researchRoot 'data/hf-home.txt') -Raw).Trim()
$env:MPLCONFIGDIR=Join-Path $env:TEMP 'pfc-matplotlib'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:PYTHONUTF8='1'
$server=Join-Path $appRoot 'app_celular/servidor.py'
$bindAddress=if($RedeLocal){'0.0.0.0'}else{'127.0.0.1'}
$arguments='"'+$server+'" --port '+$Porta+' --address '+$ipLocal+' --bind '+$bindAddress
if($Usb){$arguments+=' --transport usb'}
$process=Start-Process -FilePath $pythonw -ArgumentList $arguments -WorkingDirectory $appRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $appData 'stdout.log') -RedirectStandardError (Join-Path $appData 'stderr.log')
for($i=0;$i -lt 30;$i++){
    Start-Sleep -Milliseconds 300
    $probeCode="import urllib.request,sys`ntry: urllib.request.urlopen('http://127.0.0.1:$Porta/api/status',timeout=1).read()`nexcept Exception: sys.exit(1)"
    & $python -c $probeCode
    if($LASTEXITCODE -eq 0){$online=$true;break}
}
if(-not $online){throw 'O servidor nao iniciou. Consulte dados_app_celular/stderr.log.'}
Write-Host "PC: http://localhost:$Porta"
if($RedeLocal){Write-Host "S23 na mesma rede: http://${ipLocal}:$Porta"}elseif($Usb){Write-Host "S23 por USB: http://127.0.0.1:$Porta (apos conectar_app_usb.ps1)"}else{Write-Host 'Modo somente PC. O acesso LAN ainda nao foi habilitado.'}
Write-Host 'O codigo e o QR Code aparecem na pagina aberta no PC.'
