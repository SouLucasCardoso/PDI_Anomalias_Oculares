"""Integra somente a grade completa auditada e figuras com máscaras preservadas."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
fmt=lambda v,n=2:f'{100*v:.{n}f}'.replace('.',',')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-source',type=Path,required=True);a=p.parse_args()
    base=ROOT/'artigo/historico/ARTIGO_ANTES_GRADE_DENSA_2026-11-08.md'
    assert sha(base)=='d2594dd736b56be76411388c7b028f2d33d9918e9ac5626e1e4bb66c623d6773'
    dense=ROOT/'outputs/grade_densa_analise_2026-11-08';audit_file=dense/'AUDITORIA_FINAL.json'
    audit=json.loads(audit_file.read_text());assert audit['status']=='verified' and audit['conditions']==63
    assert len(audit['counts_recomputed'])==63 and audit['all_queries_retained']==486
    candidate_file=ROOT/'outputs/grade_densa_contorno_misto_2026-11-08/resultados.json'
    candidates=json.loads(candidate_file.read_text());assert len(candidates)==63
    gate=audit['comparison_gate_passed'];assert isinstance(gate,bool)
    sam_file=ROOT/'outputs/sam31_prompts_exteriores_2026-11-08/CONCLUIDO.json';sam=json.loads(sam_file.read_text())
    assert not sam['segmentation_gate_passed']
    mean24=sam['summary']['original']['24'];fallbacks=sum(r['variants']['24']['status']=='coarse_fallback' for r in sam['records'] if r['condition']=='original')
    figures=ROOT/'artigo/figuras_2026-11-08_final/PROVENIENCIA.json';assert figures.exists()
    text=base.read_text(encoding='utf-8');before_words=len(text.split())
    def replace_paragraph(prefix,new):
        nonlocal text
        blocks=text.split('\n\n');indices=[i for i,b in enumerate(blocks) if b.startswith(prefix)];assert len(indices)==1,(prefix,len(indices))
        blocks[indices[0]]=new;text='\n\n'.join(blocks)
    old='A grade completa incluiu perdas de 0%, 1%, 5%, 10%, 20%, 30% e 31%, nas orientações superior e inferior, com cadastro e limiar fixos.'
    new='A grade completa incluiu o controle e perdas de 1% a 31%, em passos de um ponto percentual, nas orientações superior e inferior, com cadastro e limiar fixos.'
    assert old in text;text=text.replace(old,new,1)
    text=text.replace('a grade de perdas de 0%, 1%, 5%, 10%, 20%, 30% e 31%, executada integralmente nas duas orientações',
        'o controle e todos os níveis inteiros de perda de 1% a 31%, executados nas duas orientações',1)
    old='Os níveis completos foram medidos mesmo após a primeira reprovação, para caracterizar a degradação e comparar diretamente os dois últimos níveis.'
    new='Treze condições auditadas foram reutilizadas e cinquenta acrescentadas, mantendo pesos, ambiente e execução após reprovações.'
    assert old in text;text=text.replace(old,new,1)
    replace_paragraph('O contorno foi comparado por grupos.',
        'O contorno foi comparado por grupos. Os ajustes supervisionados não produziram época elegível. Uma mistura fixa de 50% do escore polar novo foi selecionada na validação antes da grade densa.')
    text=text.replace('A transição alfa de um pixel afeta apenas a apresentação, preservando RGB e máscara binária.',
        'A cobertura alfa subpixel de até um pixel afeta apenas a apresentação, preservando RGB e máscara binária.',1)
    text=text.replace('Tabela 7 - Grade completa de oclusão na execução de 08/11/2026',
        'Tabela 7 - Resumo da grade de 1% a 31% na execução de 08/11/2026',1)
    text=text.replace('a grade completa atual não interpolou níveis ausentes',
        'a grade completa atual mediu todos os níveis inteiros',1)
    upper=audit['minimum']['reference']['oclusao_superior']['marginal']['minimum_nominal_support_on_registered_prefix']
    lower=audit['minimum']['reference']['oclusao_inferior']['marginal']['minimum_nominal_support_on_registered_prefix']
    assert upper is not None and lower is not None
    text=text.replace('As fronteiras históricas de 99,5% e 99% pertencem a outra grade; não se interpolaram níveis ausentes.',
        f'Na grade inteira, o prefixo aprovado preservou {upper}% na posição superior e {lower}% na inferior.',1)
    text=text.replace('../outputs/ensaio_oclusoes_2026-11-08/analise_final/curva_area_identificacao.png',
        '../outputs/grade_densa_analise_2026-11-08/curva_area_identificacao.png')
    text=text.replace('Fonte: do autor (2026). Faixas de 95% por pessoa, com galeria fixa; linha vertical em 30%.',
        'Fonte: do autor (2026). 63 condições; faixas de 95% por pessoa, galeria fixa e linha vertical em 30%.',1)
    text=text.replace('figuras_2026-11-08/recortes_','figuras_2026-11-08_final/recortes_')
    clean=next(r for r in candidates if r['condition']=='original');bm=clean['baseline']['metrics'];cm=clean['candidate']['metrics']
    worse=sum(r['candidate']['counts']['false_accepts']>r['baseline']['counts']['false_accepts'] for r in candidates)
    decision=('A regra relativa das 63 condições foi aprovada; os alvos absolutos continuaram a falhar nas perdas severas.' if gate else
        f'A FMR aumentou em {worse} condições e a regra completa não foi aprovada.')
    paragraph=(f'O SAM3.1 com até 24 pontos positivos e negativos exteriores alcançou Dice de {fmt(mean24)}%, '
        f'com retorno à máscara inicial em {fallbacks} de 78 imagens. Esse resultado híbrido ficou abaixo dos 88,46% do controle contínuo. '
        'O filtro de pequenos fragmentos mudou o Dice em menos de 0,01 ponto percentual. '
        f'Na grade densa, a mistura polar elevou o acerto aceito limpo de {fmt(bm["joint_success"])}% para {fmt(cm["joint_success"])}%, com FMR de {fmt(cm["far"],3)}%. '+decision)
    replace_paragraph('Usar o SAM3.1 apenas para estimar o limbo',paragraph)
    if gate:
        old='Os ensaios de segmentação diversa, adaptação SAM3.1 e reajuste da fusão não produziram melhora conjunta suficiente para substituir o controle.'
        new='A mistura final do escore polar melhorou a comparação relativa na grade inteira, mas não atingiu os alvos absolutos nas oclusões severas.'
        assert old in text;text=text.replace(old,new,1)
    assert text.count('<!-- pagina:')==30
    a.output_source.parent.mkdir(parents=True,exist_ok=True);a.output_source.write_text(text,encoding='utf-8')
    provenance={'base_sha256':sha(base),'source_sha256':sha(a.output_source),'word_delta':len(text.split())-before_words,
        'dense_conditions':63,'candidate_relative_gate_passed':gate,'candidate_fmr_worse_conditions':worse,
        'input_sha256':{str(f):sha(f) for f in (audit_file,candidate_file,sam_file,figures)},
        'recognition_counts_not_replaced':True,'new_clinical_accuracy_claimed':False,'universal_minimum_claimed':False}
    (a.output_source.parent/'PROVENIENCIA_GRADE_DENSA.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    print(json.dumps(provenance))


if __name__=='__main__':main()
