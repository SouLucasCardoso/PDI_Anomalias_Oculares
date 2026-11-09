"""Renderer empacotado com exportacao PDF pelo Word local, sem editar a origem."""
from pathlib import Path
import importlib.util,os,base64,subprocess,sys
RUNTIME=Path('C:/Users/lucaz/.cache/codex-runtimes/codex-primary-runtime')
SKILL=Path('C:/Users/lucaz/.codex/plugins/cache/openai-primary-runtime/documents/26.1105.12137/skills/documents')
os.environ['PATH']=str(RUNTIME/'dependencies/native/poppler/Library/bin')+os.pathsep+os.environ.get('PATH','')
spec=importlib.util.spec_from_file_location('native_word_adapter',Path(__file__).with_name('render_word_docx.py'))
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
spec=importlib.util.spec_from_file_location('managed_renderer',SKILL/'render_docx.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
def convert_with_metrics(input_path,user_profile,convert_tmp_dir,stem,verbose=False):
    pdf=Path(convert_tmp_dir)/(stem+'.pdf')
    environment=os.environ.copy()
    environment['PFC_RENDER_INPUT']=str(Path(input_path).resolve())
    environment['PFC_RENDER_OUTPUT']=str(pdf.resolve())
    environment['PFC_RENDER_METRICS']=str(Path(sys.argv[sys.argv.index('--output_dir')+1]).resolve()/'PAGINACAO_WORD.json')
    script=r'''
$ErrorActionPreference='Stop'
$word=$null
$document=$null
$ownsWord=$false
$previousAlerts=$null
try {
 try { $word=[Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application') }
 catch { $word=New-Object -ComObject Word.Application; $ownsWord=$true; $word.Visible=$false }
 $previousAlerts=$word.DisplayAlerts
 $word.DisplayAlerts=0
 $document=$word.Documents.Open($env:PFC_RENDER_INPUT,$false,$true,$false)
 $document.Fields.Update() | Out-Null
 $document.Repaginate()
 $document.ExportAsFixedFormat($env:PFC_RENDER_OUTPUT,17)
 $bookmarks=@{}
 foreach($item in $document.Bookmarks){if($item.Name.StartsWith('PFC_PAGINA_')){$bookmarks[$item.Name]=$item.Range.Information(3)}}
 @{pages=$document.ComputeStatistics(2);bookmarks=$bookmarks} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $env:PFC_RENDER_METRICS -Encoding utf8
 Write-Output 'Word PDF exported and pagination recorded.'
} finally {
 if($null -ne $document){$document.Close(0)}
 if($null -ne $word){
  if($null -ne $previousAlerts){$word.DisplayAlerts=$previousAlerts}
  if($ownsWord){$word.Quit()}
 }
}
'''
    command=['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode('ascii')]
    completed=subprocess.run(command,env=environment,capture_output=True,text=True,timeout=150)
    log=completed.stdout+'\n'+completed.stderr
    if completed.returncode or not pdf.exists():raise RuntimeError('Word render failed\n'+log)
    return str(pdf),log
renderer.convert_to_pdf=convert_with_metrics
if __name__=='__main__':renderer.main()
