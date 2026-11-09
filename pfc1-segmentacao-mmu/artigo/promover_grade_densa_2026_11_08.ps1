$ErrorActionPreference = 'Stop'
$articleDir = $PSScriptRoot
$stageDir = Join-Path $env:TEMP 'pfc-artigo-unisatc-20261105/versao17'
$sourceDir = Join-Path $env:TEMP 'pfc-artigo-unisatc-20261105/grade_densa_source'
$qaDir = Join-Path $articleDir 'verificacao_2026-11-08'
$archiveDir = Join-Path $qaDir 'antes_grade_densa'
$docxName = 'ARTIGO_AREA_IRIS_UNISATC_2026-11-08.docx'
$sourceName = 'ARTIGO_CONSOLIDADO_2026-11-08.md'
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Get-Sha([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }

# A revisão humana foi concluída antes desta promoção. Não reaproveitar este
# inventário para uma nova renderização ou outra versão do documento.
$inspected = @(1,16,17,18,19,24,25,27,28,29)
$carried = @(1..34 | Where-Object { $_ -notin $inspected })
if ((Get-Sha (Join-Path $articleDir $docxName)) -ne '8af5a58ad279782681cb94ebef100779fd57af7e47afa876f772604f556606ed') { throw 'DOCX canônico foi alterado; preservar a edição atual.' }
if ((Get-Sha (Join-Path $articleDir $sourceName)) -ne 'd2594dd736b56be76411388c7b028f2d33d9918e9ac5626e1e4bb66c623d6773') { throw 'Fonte canônica foi alterada.' }
if ((Get-Sha (Join-Path $stageDir $docxName)) -ne '24c0a0bef2f77f65f7af5f5b5a3478a25b62eea1e0308690acb7686005bf515e') { throw 'DOCX v17 diverge do documento revisado.' }
if ((Get-Sha (Join-Path $sourceDir $sourceName)) -ne '205994bc14fd247915473a8b1548461c9c300fb7bd8278658ca3c3cc750403b5') { throw 'Fonte v17 diverge da versão revisada.' }
$oldQa = Get-Content -LiteralPath (Join-Path $qaDir 'VERIFICACAO_FINAL.json') -Encoding UTF8 -Raw | ConvertFrom-Json
$pageHashes = [ordered]@{}
foreach ($n in 1..34) {
    $name = "page-$n.png"
    $actual = Get-Sha (Join-Path $stageDir "render/$name")
    $pageHashes[$name] = $actual
    if ($n -in $carried) {
        if ($actual -ne $oldQa.rendered_page_sha256.$name -or $n -notin $oldQa.all_pages_visually_reviewed_at_original_resolution) { throw "Página $n não pode herdar revisão." }
    }
}
if (Test-Path -LiteralPath $archiveDir) { throw 'Arquivo de QA anterior já existe; não sobrescrever.' }
$oldBody = [IO.File]::ReadAllText((Join-Path $articleDir $sourceName), $utf8)
$productionPath = Join-Path $articleDir 'ARTIGO_AREA_IRIS_EM_PRODUCAO.md'
if (-not [IO.File]::ReadAllText($productionPath, $utf8).StartsWith($oldBody.TrimEnd())) { throw 'Texto em produção contém outra edição.' }
New-Item -ItemType Directory -Path $archiveDir | Out-Null
Get-ChildItem -LiteralPath $qaDir -File | Copy-Item -Destination $archiveDir
Copy-Item -LiteralPath $productionPath -Destination (Join-Path $articleDir 'historico/ARTIGO_EM_PRODUCAO_ANTES_GRADE_DENSA_2026-11-08.md')
$previousFile = Join-Path $archiveDir 'VERIFICACAO_FINAL.json'
$review = [ordered]@{
    version = 'v17'
    current_docx_sha256 = Get-Sha (Join-Path $stageDir $docxName)
    previous_qa_file = $previousFile
    previous_qa_sha256 = Get-Sha $previousFile
    inspected_current_pages_at_original_resolution = $inspected
    unchanged_pages_carried_from_previous_review = $carried
    reviewed_resolution = '1414x2000 original'
    manual_review_completed_utc = [DateTime]::UtcNow.ToString('o')
    rendered_page_sha256 = $pageHashes
}
[IO.File]::WriteAllText((Join-Path $stageDir 'REVISAO_VISUAL.json'), ($review | ConvertTo-Json -Depth 8), $utf8)
Copy-Item -LiteralPath (Join-Path $stageDir $docxName) -Destination (Join-Path $articleDir $docxName)
Copy-Item -LiteralPath (Join-Path $sourceDir $sourceName) -Destination (Join-Path $articleDir $sourceName)
$body = [IO.File]::ReadAllText((Join-Path $sourceDir $sourceName), $utf8).TrimEnd()
$refs = [IO.File]::ReadAllText((Join-Path $stageDir 'REFERENCIAS_FORMATADAS.md'), $utf8).Trim()
$referenceHeading = '## REFER' + [char]0x00ca + 'NCIAS'
[IO.File]::WriteAllText($productionPath, ($body + "`n`n" + $referenceHeading + "`n`n" + $refs + "`n"), $utf8)
foreach ($name in @('verificacao_pacote.json','REFERENCIAS_FORMATADAS.md','REVISAO_VISUAL.json')) {
    Copy-Item -LiteralPath (Join-Path $stageDir $name) -Destination (Join-Path $qaDir $name)
}
Copy-Item -LiteralPath (Join-Path $stageDir 'render/PAGINACAO_WORD.json') -Destination (Join-Path $qaDir 'PAGINACAO_WORD.json')
Copy-Item -LiteralPath (Join-Path $sourceDir 'PROVENIENCIA_GRADE_DENSA.json') -Destination (Join-Path $qaDir 'PROVENIENCIA_GRADE_DENSA.json')
Write-Output 'v17 promovida; executar verificar_entrega_2026_11_08.py antes da entrega.'
