param([int]$Epocas = 30)
$ErrorActionPreference = 'Stop'
$pfcPython = (Get-Content (Join-Path $PSScriptRoot 'data/python-path.txt') -Raw).Trim()
$pfcRun = Join-Path $env:TEMP 'pfc-segmentacao-diversa-20261027'
$pfcMirror = Join-Path $PSScriptRoot 'outputs/segmentacao_diversa_2026-10-27'
$pfcStdout = Join-Path $PSScriptRoot 'outputs/segmentacao_diversa_2026-10-27.stdout.log'
$pfcStderr = Join-Path $PSScriptRoot 'outputs/segmentacao_diversa_2026-10-27.stderr.log'
foreach ($pfcTarget in @($pfcRun, $pfcMirror, $pfcStdout, $pfcStderr)) {
    if (Test-Path -LiteralPath $pfcTarget) { throw "Execucao ja existe: $pfcTarget. Nao sobrescrever." }
}
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONIOENCODING = 'utf-8'
$pfcArguments = @('-u', 'treinar_segmentacao_diversa.py', '--output-dir', $pfcRun,
    '--mirror-dir', 'outputs/segmentacao_diversa_2026-10-27', '--epochs', "$Epocas", '--batch-size', '16')
$pfcProcess = Start-Process -FilePath $pfcPython -ArgumentList $pfcArguments -WorkingDirectory $PSScriptRoot `
    -WindowStyle Hidden -RedirectStandardOutput $pfcStdout -RedirectStandardError $pfcStderr -PassThru
$pfcLaunch = [ordered]@{ pid = $pfcProcess.Id; started = (Get-Date).ToUniversalTime().ToString('o');
    runtime_directory = $pfcRun; mirror_directory = $pfcMirror; stdout = $pfcStdout; stderr = $pfcStderr;
    epochs = $Epocas; batch_size = 16; script = 'treinar_segmentacao_diversa.py' }
$pfcLaunch | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $PSScriptRoot 'outputs/segmentacao_diversa_lancamento_2026-10-27.json')
$pfcLaunch | ConvertTo-Json
