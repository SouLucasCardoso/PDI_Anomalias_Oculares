param(
    [string]$Script = 'diagnosticar_sam3_prompts_clinicos.py',
    [Parameter(ValueFromRemainingArguments = $true)] [string[]]$ScriptArguments
)
$ErrorActionPreference = 'Stop'
$pfcPythonFile = Join-Path $PSScriptRoot 'data/python-sam3-atual.txt'
if (!(Test-Path -LiteralPath $pfcPythonFile)) { throw 'Preparar o ambiente usando preparar_ambiente_sam3_atual.ps1' }
$pfcPython = (Get-Content -LiteralPath $pfcPythonFile -Raw -Encoding UTF8).Trim()
if (!(Test-Path -LiteralPath $pfcPython)) { throw 'Ambiente SAM3 ausente; executar novamente a preparacao' }
$pfcScript = Join-Path $PSScriptRoot $Script
if (!(Test-Path -LiteralPath $pfcScript -PathType Leaf)) { throw 'Script nao encontrado no projeto' }
$env:HF_HOME = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'data/hf-home.txt') -Raw -Encoding UTF8).Trim()
$env:MPLCONFIGDIR = Join-Path $env:TEMP 'pfc-matplotlib'
$env:PYTHONIOENCODING = 'utf-8'
Push-Location $PSScriptRoot
try {
    & $pfcPython -u $pfcScript @ScriptArguments
    exit $LASTEXITCODE
} finally { Pop-Location }
