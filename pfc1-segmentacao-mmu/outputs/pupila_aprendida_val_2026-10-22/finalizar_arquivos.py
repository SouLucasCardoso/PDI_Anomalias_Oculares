from pathlib import Path
import hashlib,json,zipfile,shutil

ROOT=Path(__file__).resolve().parents[2]
report=ROOT.parent/'Relatórios-de-Avanço/RELATORIO_AVANCO_2026-10-22.md'
text=report.read_text(encoding='utf-8').replace('O treinamento e a avaliação dessa nova hipótese ainda não foram executados.', 'No diagnóstico inicial, a hipótese ainda não havia sido treinada; a continuação está registrada na seção 7.')
text+='''

## 7. Continuação: localização aprendida da pupila

Foi treinado um localizador auxiliar em 6.282 exemplos de 167 participantes, com seleção interna em 879 exemplos de outros 16 participantes do treino original. Foram concluídas 12 épocas e selecionada a época 8. A perda geométrica aproximada caiu de 0,0008265906 para 0,0001663508. Os alvos vieram de buracos na anotação da íris; essa perda não comprova precisão anatômica.

Todas as 482 consultas foram mantidas. O Rank-1 limpo permaneceu em 90,0415% (434 acertos). A calibração fixa produziu TAR de 90,2490% e FMR de 1,0235%, acima do máximo. A recalibração limpa produziu TAR de 89,8340%, abaixo da meta, e FMR de 0,9820%. Nenhuma variante cumpriu todos os critérios. Na oclusão inferior de 10%, o Rank-1 subiu de 59,96% para 61,00% ou 61,20%, mas o TAR não melhorou e os intervalos dos ganhos incluem zero.

Não houve promoção, nova inferência no teste ou mudança nas áreas nominais anteriormente aprovadas. O resultado anterior de teste permanece 91,36%, nas condições já documentadas. A reprodução dos escores teve diferença máxima zero e a suíte completa passou em 87 testes. Os arquivos foram salvos no projeto dentro do OneDrive; o upload na nuvem não foi verificado.

Detalhes e imagem com fotos reais e texturas: [relatório da localização da pupila](../pfc1-segmentacao-mmu/PUPILA_APRENDIDA_2026-10-22.md).
'''
report.write_text(text,encoding='utf-8')
for name,link in [('README.md','PUPILA_APRENDIDA_2026-10-22.md'),('artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md','../PUPILA_APRENDIDA_2026-10-22.md')]:
    path=ROOT/name
    addition=f'''\n\n### Localização aprendida da pupila — 22/10/2026

Um localizador auxiliar foi treinado exclusivamente no treino original, com alvos geométricos aproximados obtidos de buracos nas máscaras. Na validação com 482 consultas, o Rank-1 limpo permaneceu em 90,0415%. A calibração fixa produziu TAR de 90,2490% e FMR de 1,0235%; a recalibração limpa produziu TAR de 89,8340% e FMR de 0,9820%. Nenhuma cumpriu os critérios simultâneos e o candidato anterior foi preservado. O ganho de Rank-1 sob oclusão inferior de 10% teve intervalo por participante incluindo zero. Não houve nova inferência no teste. Alvos aproximados e reutilização da validação limitam as conclusões. A suíte completa passou em 87 testes. Ver [protocolo, resultados e imagem]({link}).
'''
    path.write_text(path.read_text(encoding='utf-8')+addition,encoding='utf-8')

evaluation=ROOT/'outputs/pupila_aprendida_val_2026-10-22'
sources=['localizador_pupila.py','treinar_localizador_pupila.py','validar_localizador_pupila.py','verificar_localizador_pupila.py','visualizar_pupila_aprendida.py','test_localizador_pupila.py','PUPILA_APRENDIDA_2026-10-22.md','status_producao.py']
for name in sources:
    shutil.copyfile(ROOT/name,evaluation/('final_'+name))
archive=ROOT/'backups/pupila_aprendida_2026-10-22.zip'
files=sorted(f for folder in [ROOT/'outputs/localizador_pupila_2026-10-22',evaluation] for f in folder.rglob('*') if f.is_file())
files += [report,ROOT/'README.md',ROOT/'artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
manifest={str(f.relative_to(ROOT.parent)):sha(f) for f in files}
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for f in files:z.write(f,f.relative_to(ROOT.parent))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
audit={'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'files':manifest,'crc_and_member_hashes_verified':True,'cloud_upload_verified':False,'scope':'Both new output folders, source snapshots and updated reports; original frozen models and raw dataset remain in previous backups.'}
(archive.parent/'pupila_aprendida_2026-10-22_VERIFICACAO.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in audit.items() if k!='files'},ensure_ascii=False,indent=2))
