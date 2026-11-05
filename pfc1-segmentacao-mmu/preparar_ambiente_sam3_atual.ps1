$ErrorActionPreference = 'Stop'
$pfcBasePython = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-path.txt') -Raw).Trim()
$pfcEnvironment = Join-Path $env:USERPROFILE 'pfc-sam3-20261103'
$pfcPython = Join-Path $pfcEnvironment 'Scripts/python.exe'
$pfcMarker = Join-Path $pfcEnvironment 'PFC_WORKSPACE.txt'
if (Test-Path -LiteralPath $pfcEnvironment) {
    if (!(Test-Path -LiteralPath $pfcMarker) -or (Get-Content -LiteralPath $pfcMarker -Raw).Trim() -ne $PSScriptRoot) {
        throw 'Pasta de ambiente existente nao foi criada para este projeto'
    }
} else {
    & $pfcBasePython -m venv --system-site-packages $pfcEnvironment
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente isolado' }
    $PSScriptRoot | Set-Content -LiteralPath $pfcMarker -Encoding UTF8
}
# Herdar apenas a leitura das dependencias validadas; novos pacotes ficam no novo prefixo.
@'
import sys, sysconfig
from pathlib import Path
target=Path(sys.argv[1])/'Lib/site-packages/pfc_base_readonly.pth'
target.write_text(sysconfig.get_path('purelib')+'\n',encoding='utf-8')
'@ | & $pfcBasePython - $pfcEnvironment
if ($LASTEXITCODE -ne 0) { throw 'Falha ao configurar dependencias de base' }
& $pfcPython -m pip install --no-cache-dir --upgrade --progress-bar off 'pip==26.3'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao atualizar pip isolado' }
# A revisao mudou, mas o pacote continua numerado 0.1.0: instalar no prefixo novo explicitamente.
& $pfcPython -m pip install --no-cache-dir --no-build-isolation --no-deps --ignore-installed --progress-bar off `
    'sam3 @ https://github.com/facebookresearch/sam3/archive/f1647e8d0c1d280991f4d1b7d974c2704537fe66.zip'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar a revisao atual do SAM3' }
& $pfcPython -m pip install --no-cache-dir --no-build-isolation --upgrade --progress-bar off -r (Join-Path $PSScriptRoot 'requirements-sam3-atual.txt')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar SAM3 atual' }
# Builds GPU oficiais mais recentes encontrados nos indices cu126/cu128/cu130 consultados.
& $pfcPython -m pip install --no-cache-dir --no-deps --ignore-installed --progress-bar off `
    'torch==2.14.1+cu130' 'torchvision==0.29.1+cu130' --index-url https://download.pytorch.org/whl/cu130
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar o par GPU isolado' }
& $pfcPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependencias inconsistentes no ambiente novo' }
$pfcPython | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'data/python-sam3-atual.txt') -Encoding UTF8
Write-Output "Ambiente SAM3 atualizado: $pfcPython"
