"""Insere resultados completos sem alterar os controles ou a seleção histórica."""
from pathlib import Path
import argparse,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
fmt=lambda p,n=2:f'{100*p:.{n}f}'.replace('.',',')

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-source',type=Path,required=True);a=p.parse_args()
    base=ROOT/'artigo/historico/ARTIGO_ANTES_MELHORIA_RECONHECEDOR_2026-11-08.md'
    assert sha(base)=='bfe7168e62af945a1604eff77c72acc47331a1ad4641e823899711813d247983'
    text=base.read_text(encoding='utf-8');hfile=ROOT/'outputs/reconhecedor_confirmacao_2026-11-08/analise/AUDITORIA_FINAL.json';h=json.loads(hfile.read_text());assert len(h['records'])==13
    gfile=ROOT/'outputs/sam31_geometria_identidade_2026-11-08/CONCLUIDO.json';g=json.loads(gfile.read_text());assert not g['eligible_gain']
    trainfile=ROOT/'outputs/polar_sam31_adaptacao_entrega_2026-11-08/CONCLUIDO.json';training=json.loads(trainfile.read_text());assert not training['eligible_gain'] and training['epochs_completed']==6
    auditfile=ROOT/'outputs/polar_sam31_adaptacao_entrega_2026-11-08/analise/AUDITORIA_TREINO_FINAL.json';audit=json.loads(auditfile.read_text());assert audit['status']=='verified' and audit['selected_epoch'] is None
    def replace(prefix,new):
        nonlocal text
        parts=text.split('\n\n');matches=[i for i,s in enumerate(parts) if s.startswith(prefix)];assert len(matches)==1,(prefix,len(matches));parts[matches[0]]=new;text='\n\n'.join(parts)
    replace('A etapa móvel utilizou cadastro próprio',
        'O contorno foi comparado por grupos. A validação selecionou o ramo polar antes da grade completa; os ajustes supervisionados RGB e polar não produziram época elegível.')
    replace('Um controle posterior usou 78 imagens',
        'Em 78 imagens de validação, uma por lado de cada uma das 39 pessoas, o Dice médio da U-Net passou de 88,20% para 88,46% com a margem contínua interpolada, melhorando em 67 imagens. O refino interativo SAM3.1 obteve 76,70%. Contudo, aplicar o contorno contínuo aos nove descritores reduziu o Rank-1 limpo de 90,04% para 89,00%. O ganho de segmentação, portanto, não implicou ganho na cadeia biométrica. A referência só entrou no cálculo posterior do Dice; nenhum resultado clínico foi recalculado.')
    clean=next(r for r in h['records'] if r['condition']=='original');upper=next(r for r in h['records'] if r['condition']=='oclusao_superior' and r['level']==1);severe=next(r for r in h['records'] if r['condition']=='oclusao_inferior' and r['level']==31)
    bm=upper['recounted']['baseline']['metrics'];cm=upper['recounted']['candidate']['metrics'];lo,hi=[v[0] for v in upper['descriptive_interval95_pp']]
    paragraph=(f"A aplicação seletiva aos descritores polares trouxe ganho localizado no teste reutilizado. Com 1% de oclusão superior, o Rank-1 passou de {fmt(bm['rank1'])}% para {fmt(cm['rank1'])}%, com TAR de {fmt(cm['tar'])}% e FMR de {fmt(cm['far'],3)}%. A diferença descritiva de 1,23 ponto percentual teve intervalo de 95% de {lo:.2f} a {hi:.2f} pontos. Entretanto, com 31% de perda inferior, o Rank-1 caiu de 32,51% para 30,25% e a FMR aumentou. O candidato não aprovou a regra completa e não substituiu a referência.").replace(f'{lo:.2f}',f'{lo:.2f}'.replace('.',',')).replace(f'{hi:.2f}',f'{hi:.2f}'.replace('.',','))
    text=text.replace('<!-- pagina:28 -->',paragraph+'\n\n<!-- pagina:28 -->')
    lower=g['results']['oclusao_inferior'];gb=g['baseline']['oclusao_inferior']
    geometry=(f"Usar o SAM3.1 apenas para estimar o limbo da normalização polar, mantendo suporte e pupila anteriores, elevou o Rank-1 de validação sob perda inferior de 10% de {fmt(gb['rank1'])}% para {fmt(lower['rank1'])}%. A FMR caiu de {fmt(gb['far'])}% para {fmt(lower['far'])}%, mas o desempenho limpo diminuiu. A geometria e o ajuste polar supervisionado de seis épocas foram rejeitados.")
    text=text.replace('<!-- pagina:28 -->',geometry+'\n\n<!-- pagina:28 -->')
    replace('A proporção de um sucesso em quatro consultas',
        'O sucesso em uma de quatro consultas (25%) não estima com precisão uma população clínica. As consultas pertencem a apenas dois olhos e não são quatro pessoas independentes. Entre sessenta pares impostores, uma única falsa correspondência equivale a 1,67%, acima do alvo empírico de 1% de outro cenário. A pequena amostra e as aquisições distintas impedem atribuir os resultados somente às alterações oculares.')
    a.output_source.parent.mkdir(parents=True,exist_ok=True);a.output_source.write_text(text,encoding='utf-8')
    evidence={'base_source_sha256':sha(base),'output_source_sha256':sha(a.output_source),'inputs_sha256':{str(f):sha(f) for f in (hfile,gfile,trainfile,auditfile)},
        'new_trials_complete_only':True,'no_pending_training_result_inserted':True,'no_prior_recognition_result_replaced':True,'new_recognizer_promoted':False,
        'approximate_word_delta':len(text.split())-len(base.read_text(encoding='utf-8').split()),'conceptual_page_markers':text.count('<!-- pagina:')}
    (a.output_source.parent/'PROVENIENCIA_ATUALIZACAO.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8');print(json.dumps(evidence))

if __name__=='__main__':main()
