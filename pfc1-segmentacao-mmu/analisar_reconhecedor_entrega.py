"""Auditoria pareada do ajuste; nao seleciona pesos nem reescreve o artigo."""
from pathlib import Path
import argparse,json
import numpy as np
from recorte_iris_sam31_alta_res import sha
from rodada_reconhecedor_entrega import write
from avaliar_robustez_reconhecimento import load_splits,metrics,operating_threshold
ROOT=Path(__file__).resolve().parent
CONDITIONS=('original','oclusao_superior','oclusao_inferior')

def measure(d,threshold):
    m,c,a=metrics(d['scores'],d['labels'],threshold,d['valid']);m['joint_success']=float((c&a).mean())
    imp=np.ones(d['scores'].shape,bool);imp[np.arange(len(c)),d['labels']]=False
    counts={'queries':len(c),'correct':int(c.sum()),'accepted':int(a.sum()),'joint':int((c&a).sum()),
        'impostors':int(imp.sum()),'false_accepts':int(((d['scores']>=threshold)&imp&d['valid'][:,None]).sum()),'failed':int((~d['valid']).sum())}
    return m,counts,c,a

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args();run=a.run_dir.resolve()
    final=json.loads((run/'CONCLUIDO.json').read_text());protocol=json.loads((run/'protocolo.json').read_text())
    for name,expected in protocol['sources_sha256'].items():assert sha(ROOT/name)==expected
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    subjects=np.array([r.subject for r in rows if r.session==2]);people=np.unique(subjects)
    draws=np.random.default_rng(20261108).integers(0,len(people),(5000,len(people)))
    data={};calibrated={};records=[]
    for method in ('baseline','selected'):
        data[method]={};thresholds=[]
        for condition in CONDITIONS:
            with np.load(run/f'scores_fusion_{method}_{condition}.npz',allow_pickle=False) as z:d={k:z[k].copy() for k in ('scores','labels','valid')}
            assert len(d['labels'])==len(subjects)==482
            data[method][condition]=d;mask=np.ones(d['scores'].shape,bool);mask[np.arange(len(subjects)),d['labels']]=False
            effective=np.where(d['valid'][:,None],d['scores'],-2.)
            thresholds.append(operating_threshold(effective[mask],.01))
        calibrated[method]=max(thresholds)
    for condition in CONDITIONS:
        b=data['baseline'][condition];s=data['selected'][condition];np.testing.assert_array_equal(b['labels'],s['labels'])
        threshold=final['baseline'][condition]['threshold'];bm,bc,bcorrect,baccept=measure(b,threshold);sm,sc,scorrect,saccept=measure(s,threshold)
        for original,recounted in ((final['baseline'][condition],bm),(final['results'][condition],sm)):
            for key in ('rank1','tar','far','joint_success'):assert abs(original[key]-recounted[key])<1e-12
        diffs=np.column_stack((scorrect.astype(float)-bcorrect,saccept.astype(float)-baccept,(scorrect&saccept).astype(float)-(bcorrect&baccept)))
        sums=np.array([diffs[subjects==person].sum(0) for person in people]);totals=np.array([(subjects==person).sum() for person in people])
        paired=100*sums[draws].sum(1)/totals[draws].sum(1)[:,None];ci=np.quantile(paired,[.025,.975],axis=0)
        secondary={}
        for name in ('baseline','selected'):
            m,counts,_,_=measure(data[name][condition],calibrated[name]);assert m['far']<=.01
            secondary[name]={'threshold':calibrated[name],'metrics':m,'counts':counts}
        records.append({'condition':condition,'baseline':bm,'selected':sm,'counts_baseline':bc,'counts_selected':sc,
            'paired_gain_pp':dict(zip(('rank1','tar','joint'),(100*diffs.mean(0)).tolist())),
            'descriptive_interval95_pp':{k:ci[:,i].tolist() for i,k in enumerate(('rank1','tar','joint'))},'secondary_calibrated':secondary})
    out=run/'analise';out.mkdir(exist_ok=True)
    audit={'registered_selection_preserved':True,'selected_epoch':final['selected_epoch'],'eligible_gain':final['eligible_gain'],
        'absolute_fmr_target_all_conditions':final['absolute_fmr_target_all_conditions'],'n_queries':482,'people':len(people),'bootstrap':5000,
        'independent_confirmation':False,'clinical_effect_measured':False,'test_inference':False,'records':records,
        'completed_sha256':sha(run/'CONCLUIDO.json'),'analyst_sha256':sha(__file__),'protocol_sha256':sha(run/'protocolo.json')}
    write(out/'AUDITORIA.json',audit)
    lines=['# Resultado do ajuste do reconhecedor','',f"Época selecionada: **{final['selected_epoch']}**. Ganho elegível pela regra registrada: **{'sim' if final['eligible_gain'] else 'não'}**.",'',
        '| Condição | Versão | Rank-1 | TAR | FMR | Correto e aceito |','|---|---|---:|---:|---:|---:|']
    for r in records:
        for method in ('baseline','selected'):
            m=r[method];lines.append(f"| {r['condition']} | {method} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
    lines+=['','Os pesos, a padronização e o limiar da fusão foram mantidos nesta comparação primária. Cada linha usa todas as482consultas de validação. Intervalos descritivos pareados por pessoa e contagens independentes constam de AUDITORIA.json. A validação foi reutilizada no desenvolvimento e na seleção; os intervalos não removem esse viés. Não houve teste independente, ensaio clínico ou estimativa de mínimo universal.','',
        '## Controle secundário de falsas correspondências','',
        'Aplicou-se às duas versões a mesma regra previamente registrada: calibrar em cada condição para FMR≤1% e usar o maior dos três limiares, fixo nas três condições. Este diagnóstico não escolheu a época nem os pesos. Seus valores são de calibração na própria validação, sem certificação fora dela.','',
        '| Condição | Versão | Limiar fixo | Rank-1 | TAR | FMR |','|---|---|---:|---:|---:|---:|']
    for r in records:
        for method,z in r['secondary_calibrated'].items():
            m=z['metrics'];lines.append(f"| {r['condition']} | {method} | {z['threshold']:.9f} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% |")
    lines+=['','Nenhum arquivo, modelo ou resultado do artigo já concluído foi substituído automaticamente. Um eventual novo ensaio de teste exige congelar o candidato e executar a grade completa, mantendo as falhas no denominador.']
    (out/'RESULTADO.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in audit.items() if k!='records'}),flush=True)

if __name__=='__main__':main()
