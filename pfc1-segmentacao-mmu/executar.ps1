param(
    [Parameter(Mandatory=$true, Position=0)][string]$Script,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Argumentos
)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $env:HF_HOME = Join-Path $PSScriptRoot 'data/modelos/huggingface'
    $pfcHFConfig = Join-Path $PSScriptRoot 'data/hf-home.txt'
    if (Test-Path $pfcHFConfig) { $env:HF_HOME = (Get-Content $pfcHFConfig -Raw).Trim() }
    $env:MPLCONFIGDIR = Join-Path $PSScriptRoot 'data/cache/matplotlib'
    $env:TORCH_HOME = Join-Path $PSScriptRoot 'data/modelos/torch'
    $pfcPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    $pfcConfig = Join-Path $PSScriptRoot 'data/python-path.txt'
    if (Test-Path $pfcConfig) { $pfcPython = (Get-Content $pfcConfig -Raw).Trim() }
    # Windows PowerShell trata stderr redirecionado como NativeCommandError.
    # Bibliotecas de ML usam stderr tambem para progresso: verificar o exit code.
    $ErrorActionPreference = 'Continue'
    & $pfcPython $Script @Argumentos
    $pfcExitCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($pfcExitCode -ne 0) { throw "Execucao terminou com codigo $pfcExitCode" }
} finally { Pop-Location }
