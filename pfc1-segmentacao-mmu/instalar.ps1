param([string]$Ambiente = (Join-Path $env:USERPROFILE 'pfc-tcc-venv'), [switch]$Sam3)
$ErrorActionPreference = 'Stop'
$pfcBase = Join-Path $PSScriptRoot '../.runtime/python312/python.exe'
if (-not (Test-Path $pfcBase)) { throw 'Python base ausente. Consulte INSTALACAO_LOCAL.md.' }
$pfcPython = Join-Path $Ambiente 'Scripts/python.exe'
if (-not (Test-Path $pfcPython)) {
    & $pfcBase -m venv $Ambiente
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente.' }
}
& $pfcPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Falha ao atualizar pip.' }
& $pfcPython -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar PyTorch CUDA.' }
$pfcRequirements = 'requirements.txt'
if ($Sam3) { $pfcRequirements = 'requirements-sam3.txt' }
& $pfcPython -m pip install -r (Join-Path $PSScriptRoot $pfcRequirements) gdown
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias.' }
& $pfcPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependencias inconsistentes.' }
New-Item -ItemType Directory -Force (Join-Path $PSScriptRoot 'data') | Out-Null
Set-Content -Encoding utf8 (Join-Path $PSScriptRoot 'data/python-path.txt') $pfcPython
Write-Output 'Ambiente configurado. Use executar.ps1 para executar os scripts.'
