"""Apura o criterio predefinido sem nova inferencia ou escolha posterior de niveis."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parent
KINDS=('oclusao_superior','oclusao_inferior')

def minimum_fraction(original, conditions):
    """Exige aprovacao no original e em todos os niveis de maior area."""
    passes=lambda row: float(row['rank1'])>=.90 and float(row['tar'])>=.90
    if not passes(original): return None
    minimum=100
    for row in sorted(conditions,key=lambda r:int(r['level'])):
        if not passes(row): break
        minimum=100-int(row['level'])
    return minimum

def summarize(folder):
    if not (folder/'CONCLUIDO.json').is_file(): raise RuntimeError('Experimento ainda nao concluido')
    protocol=json.loads((folder/'protocolo.json').read_text(encoding='utf-8'))
    if not protocol.get('minimum_area_rule'): raise ValueError('Ausencia de criterio registrado')
    with (folder/'resumo.csv').open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    expected={(b,k,int(level)) for b in protocol['branches'] for k,level in protocol['conditions']}
    actual=[(r['branch'],r['condition'],int(r['level'])) for r in rows]
    if len(actual)!=len(set(actual)) or set(actual)!=expected:
        raise ValueError('Resultados ausentes, duplicados ou fora do protocolo')
    findings=[]
    for branch in protocol['branches']:
        original=next(r for r in rows if r['branch']==branch and r['condition']=='original')
        for kind in KINDS:
            conditions=[r for r in rows if r['branch']==branch and r['condition']==kind]
            if {int(r['level']) for r in conditions}!=set(range(10,100,10)):
                raise ValueError('Relatorio requer grade completa de 10% a 90%')
            minimum=minimum_fraction(original,conditions)
            findings.append({'branch':branch,'orientation':kind,
                'minimum_tested_preserved_percent':minimum,
                'status':'not_determined_baseline_below_criterion' if minimum is None else 'determined_on_tested_grid',
                'original_rank1':float(original['rank1']),'original_tar':float(original['tar']),
                'original_test_fmr':float(original['far']),
                'test_fmr_above_validation_target':float(original['far'])>.01,
                'interpretation':'context included; not iris-only evidence' if branch=='inteira' else 'iris crop; model-specific estimate'})
    result={'technical_pilot':bool(protocol['development_subsample']),
            'generated_utc':datetime.now(timezone.utc).isoformat(),
            'protocol_sha256':hashlib.sha256((folder/'protocolo.json').read_bytes()).hexdigest(),
            'summary_sha256':hashlib.sha256((folder/'resumo.csv').read_bytes()).hexdigest(),
            'criterion':protocol['minimum_area_rule'],'findings':findings,
            'limitations':['Point estimate criterion; not a confidence-bound guarantee',
                'Validation FMR <=1% does not guarantee test FMR <=1%',
                '10 percentage point grid; no universal or clinical minimum',
                'Synthetic loss of annotated pixels does not measure disease extent']}
    (folder/'area_minima.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    title='RELATORIO TECNICO DO PILOTO' if result['technical_pilot'] else 'AREA PRESERVADA — EXPERIMENTO COMPLETO'
    text=[f'# {title}','',
          'Resultados do piloto nao constituem estimativas finais do artigo.' if result['technical_pilot'] else 'Estimativas restritas ao modelo, amostra e grade registrados.',
          '', '| Ramo | Orientacao | Menor area testada aprovada | Rank-1 original | TAR original | FMR teste original |',
          '|---|---|---:|---:|---:|---:|']
    for f in findings:
        area='Nao determinado' if f['minimum_tested_preserved_percent'] is None else str(f['minimum_tested_preserved_percent'])+'%'
        text.append(f"| {f['branch']} | {f['orientation']} | {area} | {100*f['original_rank1']:.2f}% | {100*f['original_tar']:.2f}% | {100*f['original_test_fmr']:.2f}% |")
    text.extend(['','O criterio exige Rank-1 e TAR de pelo menos 90% no original e em todas as areas maiores. A FMR de teste e apresentada sem pressupor que coincida com a calibracao. A decisao usa estimativas pontuais e nao limites de confianca. A imagem inteira inclui contexto periocular.','',*result['limitations']])
    (folder/'RELATORIO_AREA.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--wait',action='store_true')
    args=parser.parse_args(); folder=args.output_dir
    if args.wait:
        deadline=time.monotonic()+12*3600
        while not (folder/'CONCLUIDO.json').is_file():
            if time.monotonic()>deadline: raise TimeoutError('Experimento nao concluiu em 12 horas')
            print('Aguardando CONCLUIDO.json: '+datetime.now(timezone.utc).isoformat(),flush=True)
            time.sleep(30)
    summarize(folder)

if __name__=='__main__': main()
