"""Adaptador Windows: Word instalado exporta PDF; renderer empacotado produz PNGs."""
from pathlib import Path
import base64,importlib.util,os,subprocess

SKILL=Path('C:/Users/lucaz/.codex/plugins/cache/openai-primary-runtime/documents/26.1022.11436/skills/documents')
RUNTIME=Path('C:/Users/lucaz/.cache/codex-runtimes/codex-primary-runtime')
os.environ['PATH']=str(RUNTIME/'dependencies/native/poppler/Library/bin')+os.pathsep+os.environ.get('PATH','')
spec=importlib.util.spec_from_file_location('packaged_docx_renderer',SKILL/'render_docx.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)

def convert_with_word(input_path,user_profile,convert_tmp_dir,stem,verbose=False):
    pdf=Path(convert_tmp_dir)/(stem+'.pdf')
    script=r'''
$ErrorActionPreference='Stop'
$word=$null
$document=$null
try {
 $word=New-Object -ComObject Word.Application
 $word.Visible=$false
 $word.DisplayAlerts=0
 $document=$word.Documents.Open($env:PFC_RENDER_INPUT,$false,$true,$false)
 $document.Fields.Update() | Out-Null
 $document.Repaginate()
 $document.ExportAsFixedFormat($env:PFC_RENDER_OUTPUT,17)
 Write-Output ('Word PDF exported: '+$env:PFC_RENDER_OUTPUT)
} finally {
 if ($null -ne $document) {$document.Close(0)}
 if ($null -ne $word) {$word.Quit()}
}
'''
    environment=os.environ.copy();environment['PFC_RENDER_INPUT']=str(Path(input_path).resolve());environment['PFC_RENDER_OUTPUT']=str(pdf.resolve())
    command=['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode('ascii')]
    completed=subprocess.run(command,env=environment,capture_output=True,text=True,timeout=90)
    log=completed.stdout+'\n'+completed.stderr
    if completed.returncode or not pdf.exists():raise RuntimeError('Native Word PDF export failed\n'+log)
    return str(pdf),log

if __name__=='__main__':
    renderer.convert_to_pdf=convert_with_word
    renderer.main()
