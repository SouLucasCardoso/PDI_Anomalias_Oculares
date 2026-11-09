"""Audita a grade concluida e gera figuras e texto para a defesa."""
from pathlib import Path
import argparse,csv,hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ensaio_entrega_oclusoes import LEVELS,digest,evaluate,write

ROOT=Path(__file__).resolve().parent

def interval(values,subjects):
    people=np.unique(subjects);rng=np.random.default_rng(20261108)
    draws=rng.integers(0,len(people),(5000,len(people)))
    numerator=np.array([values[subjects==s].sum() for s in people])[draws].sum(1)
    denominator=np.array([(subjects==s).sum() for s in people])[draws].sum(1)
    return np.quantile(100*numerator/denominator,[.025,.975]).tolist()

def illustrative_occlusions(out,rows):
    from treinar_segmentacao_ubipr import decode_mask
    from avaliar_robustez_reconhecimento import perturb
    # Selecao geometrica anterior a qualquer consulta ao reconhecimento desta figura.
    sample=None
    for row in sorted((r for r in rows if r.session==2),key=lambda r:Path(r.image).name):
        reference=decode_mask(Image.open(row.mask))==1
        if reference.sum()>10000:
            sample=row;break
    if sample is None:raise RuntimeError('Sem exemplo com referencia extensa para prancha')
    original=Image.open(sample.image).convert('RGB');mask=decode_mask(Image.open(sample.mask))==1
    ys,xs=np.where(mask);cx=(xs.min()+xs.max())/2;cy=(ys.min()+ys.max())/2
    width=max(xs.max()-xs.min()+1,ys.max()-ys.min()+1)*1.5
    box=(max(0,int(cx-width/2)),max(0,int(cy-width/2)),min(original.width,int(cx+width/2)),min(original.height,int(cy+width/2)))
    board=Image.new('RGB',(2240,760),'white');draw=ImageDraw.Draw(board)
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
    for j,level in enumerate(LEVELS):
        draw.text((j*320+8,5),f'Oclusão {level}%',font=font(44),fill='black')
        draw.text((j*320+8,55),f'Suporte {100-level}%',font=font(38),fill='black')
        for i,side in enumerate(('oclusao_superior','oclusao_inferior')):
            image,_=perturb(original,mask,side,level)
            board.paste(ImageOps.pad(image.crop(box),(304,260),color='white'),(j*320+8,120+i*310))
    draw.text((8,96),'Superior',font=font(27),fill='black')
    draw.text((8,393),'Inferior',font=font(32),fill='black')
    draw.text((8,715),f'Exemplo: {Path(sample.image).name} — enquadramento de exibição fixo em todos os níveis',font=font(28),fill='black')
    path=out/'exemplo_oclusoes.png';board.save(path,dpi=(300,300))
    return {'filename':Path(sample.image).name,'image_sha256':digest(sample.image),'reference_sha256':digest(sample.mask),
            'selection':'Primeira consulta ordenada por nome com >10000 pixels anotados, sem selecao por acerto. Enquadramento identico apenas para exibicao.',
            'dataset':'UBIPr Single Eyes Segmented; Padole e Proenca (2012)',
            'source':'https://iris.di.ubi.pt/ubipr.html','license':'CC BY-NC-SA 4.0; figura derivada para pesquisa nao comercial',
            'figure_sha256':digest(path)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args()
    run=a.run_dir.resolve();assert (run/'CONCLUIDO.json').is_file(),'Aguardar toda a grade.'
    out=run/'analise_final';out.mkdir(exist_ok=True)
    from avaliar_robustez_reconhecimento import load_splits
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())
    rows=load_splits(manifest)['test'];subjects=np.array([r.subject for r in rows if r.session==2])
    assert len(subjects)==486 and len(np.unique(subjects))==16
    records=json.loads((run/'resultados.json').read_text());assert len(records)==26
    chosen=[r for r in records if r['model']=='historico'];model=json.loads((run/'FUSAO_CONGELADA.json').read_text())
    original=next(r for r in chosen if r['condition']=='original');decisions={};raw={};audit=[];sensitivity=[]
    area_file=run/'inferencia/confirmacao_congelada_test_oclusao_superior_1_2026-10-21/interventions.json'
    area_rows=json.loads(area_file.read_text());defined=np.array([r['fraction_defined'] for r in area_rows],bool)
    assert defined.shape==(486,) and defined.sum()==480
    for r in chosen:
        side,loss=r['condition'],r['loss_percent'];key=f'{side}_{loss}'
        file=run/f'scores_historico_{key}.npz'
        with np.load(file,allow_pickle=False) as z:data={k:z[k] for k in z.files}
        suffix='' if side=='original' else '_'+key
        folder=run/'inferencia'/f'confirmacao_congelada_test{suffix}_2026-10-21'
        calculated,_=evaluate(folder,model,subjects,0.8581747485460748,np.array([1/8]*7+[1/16]*2))
        assert calculated['counts']==r['counts'];assert r['counts']['queries']==486 and r['counts']['impostors']==7290
        with np.load(folder/'scores_finais.npz',allow_pickle=False) as historical:
            np.testing.assert_allclose(data['scores'],historical['scores'],atol=1e-12,rtol=1e-12)
            for field in ('labels','valid','correct','accepted'):np.testing.assert_array_equal(data[field],historical[field])
        np.testing.assert_array_equal(data['correct'],(data['scores'].argmax(1)==data['labels'])&data['valid'])
        np.testing.assert_array_equal(data['accepted'],(data['scores'][np.arange(486),data['labels']]>=.8581747485460748)&data['valid'])
        decisions[(side,loss)]=data['correct'];raw[(side,loss)]=data
        audit.append({'condition':key,'scores_sha256':digest(file),'all_counts_recomputed':True,'historical_frozen_evaluator_scores_reproduced':True})
        from avaliar_robustez_reconhecimento import metrics
        measured,c,accepted=metrics(data['scores'][defined],data['labels'][defined],.8581747485460748,data['valid'][defined])
        sensitivity.append({'condition':key,'queries':480,'rates':measured,'joint':float((c&accepted).mean()),
                            'scope':'Sensibilidade secundaria pos-hoc no subconjunto fixo com referencia original nao vazia. Nao substitui o resultado principal com486.'})
    paired=[]
    for side in ('oclusao_superior','oclusao_inferior'):
        for loss in LEVELS[1:]:
            delta=decisions[('original',0)].astype(float)-decisions[(side,loss)].astype(float)
            paired.append({'condition':side,'loss_percent':loss,'rank1_drop_pp':100*float(delta.mean()),
                           'interval95_cluster_person_pp':interval(delta,subjects)})
    comparison=[]
    for side in ('oclusao_superior','oclusao_inferior'):
        delta=decisions[(side,30)].astype(float)-decisions[(side,31)].astype(float)
        comparison.append({'condition':side,'contrast':'30% para31% de oclusao (70% para69% do suporte anotado)',
                           'rank1_drop_pp':100*float(delta.mean()),'interval95_cluster_person_pp':interval(delta,subjects),
                           'lost_correct':int((delta==1).sum()),'gained_correct':int((delta==-1).sum())})
    difference=decisions[('oclusao_superior',10)].astype(float)-decisions[('oclusao_inferior',10)].astype(float)
    orientation10={'upper_minus_lower_rank1_pp':100*float(difference.mean()),'interval95_cluster_person_pp':interval(difference,subjects)}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(7.6,4.4),layout='constrained')
    for side,color,label in [('oclusao_superior','#1f5d99','Superior'),('oclusao_inferior','#ae4528','Inferior')]:
        rr=[original]+[next(r for r in chosen if r['condition']==side and r['loss_percent']==l) for l in LEVELS[1:]]
        for ax,metric in zip(axes,('rank1','far')):
            values=np.array([100*r['rates'][metric] for r in rr]);key='fmr' if metric=='far' else metric
            ci=np.array([r['interval95_cluster_person_pp'][key] for r in rr])
            ax.plot(LEVELS,values,'o-',color=color,label=label,linewidth=1.6,markersize=4)
            ax.fill_between(LEVELS,ci[:,0],ci[:,1],color=color,alpha=.12)
            ax.set_xlabel('Área anotada ocluída (%)');ax.grid(alpha=.18)
            ax.set_xticks([0,5,10,20,30]);ax.set_xlim(-1,32)
            ax.axvline(30,color='#777777',linestyle=':',linewidth=1)
    axes[0].axhline(90,color='black',linestyle='--',linewidth=1,label='Critério nominal 90%')
    axes[0].set_ylabel('Identificação Rank-1 (%)');axes[0].set_ylim(0,100);axes[0].legend(loc='lower left',fontsize=9.5)
    axes[1].axhline(1,color='black',linestyle='--',linewidth=1,label='Critério nominal 1%')
    axes[1].set_ylabel('Falsas correspondências FMR (%)');axes[1].legend(loc='upper left',fontsize=9.5)
    fig.suptitle('Cadastro e limiar fixos — 486 consultas por condição',fontsize=12)
    fig.savefig(out/'curva_area_identificacao.png',dpi=300);plt.close(fig)
    # Comparacao ampliada, sem interpolar ou inventar uma transicao em70%.
    fig,ax=plt.subplots(figsize=(7.2,3.5),layout='constrained')
    for j,(side,color,label) in enumerate([('oclusao_superior','#1f5d99','Superior'),('oclusao_inferior','#ae4528','Inferior')]):
        rr=[next(r for r in chosen if r['condition']==side and r['loss_percent']==loss) for loss in (30,31)]
        y=np.array([100*r['rates']['rank1'] for r in rr]);ci=np.array([r['interval95_cluster_person_pp']['rank1'] for r in rr])
        ax.errorbar(np.array([0,1])+j*.07-.035,y,yerr=np.maximum(0,np.array([y-ci[:,0],ci[:,1]-y])),fmt='o',capsize=4,color=color,label=label)
    ax.set_xticks([0,1],['30% de oclusão\n70% do suporte anotado','31% de oclusão\n69% do suporte anotado'])
    ax.set_xlim(-.5,1.5);ax.set_ylabel('Identificação Rank-1 (%)');ax.set_ylim(0,100);ax.legend();ax.grid(axis='y',alpha=.2)
    fig.savefig(out/'comparacao_30_31.png',dpi=300);plt.close(fig)
    example=illustrative_occlusions(out,rows)
    lines=['# Resultado para a defesa do PFC','',
           'O ensaio completo mede o efeito de retirar informação visível da imagem sobre uma cadeia de identificação ocular. Não estima um limite universal de anatomia nem o efeito causal de uma doença.','',
           'A tentativa de fusão aprendida não superou o controle na validação fora das dobras e manteve os pesos históricos. A curva principal usa esse controle e seu limiar histórico fixo; o ajuste não é anunciado como melhoria.','',
           '| Oclusão | Suporte nominal restante | Rank-1 superior | Rank-1 inferior | TAR superior | TAR inferior | FMR superior | FMR inferior |',
           '|---:|---:|---:|---:|---:|---:|---:|---:|']
    flat=[]
    for loss in LEVELS:
        pair=[original,original] if loss==0 else [next(r for r in chosen if r['condition']==side and r['loss_percent']==loss) for side in ('oclusao_superior','oclusao_inferior')]
        u,l=[r['rates'] for r in pair]
        lines.append(f"| {loss}% | {100-loss}% | {100*u['rank1']:.2f}% | {100*l['rank1']:.2f}% | {100*u['tar']:.2f}% | {100*l['tar']:.2f}% | {100*u['far']:.3f}% | {100*l['far']:.3f}% |")
        flat.append({'oclusao_percent':loss,'suporte_restante_percent':100-loss,'rank1_superior_percent':100*u['rank1'],'rank1_inferior_percent':100*l['rank1'],'tar_superior_percent':100*u['tar'],'tar_inferior_percent':100*l['tar'],'fmr_superior_percent':100*u['far'],'fmr_inferior_percent':100*l['far']})
    lines += ['', '![Curva do ensaio](curva_area_identificacao.png)','', '![Comparação entre os dois últimos níveis](comparacao_30_31.png)','']
    for c in comparison:
        lo,hi=c['interval95_cluster_person_pp'];drop=c['rank1_drop_pp']
        lines.append(f"Na orientação {c['condition'].removeprefix('oclusao_')}, passar de30% para31% de oclusão mudou o Rank-1 em {-drop:+.2f} pontos percentuais. O intervalo de95% da perda foi [{lo:.2f}; {hi:.2f}] pontos; {c['lost_correct']} consultas perderam acerto e {c['gained_correct']} ganharam acerto.")
    lines += ['', 'Use na defesa: “No sistema e no protocolo avaliados, a extensão e a localização da oclusão alteraram o reconhecimento. A passagem de70% para69% do suporte anotado foi medida diretamente, mas não constitui teste de um limiar anatômico universal de70%.”','',
              'A ISO/IEC 29794-6:2015 trata qualidade da imagem e área utilizável em relação ao anel estimado. Nossa máscara contém somente a região originalmente anotada; 70% e69% nesta curva usam outro denominador. A base não fornece a pupila como classe anatômica independente. Não foi validada uma medição normativa do anel completo.','',
              'O estudo mantém 486 consultas e 7.290 pares impostores em cada condição, com 16 candidatos do mesmo lado e cadastro original. As seis referências vazias permanecem nas métricas e têm área indefinida; a área real é conferida em 480 consultas. A auditoria inclui uma sensibilidade secundária no subconjunto fixo dessas 480 referências, sem substituir a análise principal. Os intervalos são descritivos, por pessoa, com galeria fixa; o teste já foi consultado durante o desenvolvimento. Não se recalibra o limiar em cada oclusão.','',
              'Os intervalos pareados desta análise usam5000 reamostragens e semente20261108. O campo auxiliar pareado do relatório bruto foi produzido pela função histórica com semente20261001; não é utilizado nas conclusões desta análise. As contagens e taxas brutas não mudam.','',
              'Fontes normativas: [ISO](https://www.iso.org/standard/54066.html); [prévia pública da norma, seção6.2.1.4](https://cdn.standards.iteh.ai/samples/54066/5bd98d11a8824ab29d5935edbfe997a9/ISO-IEC-29794-6-2015.pdf).','',
              '![Exemplo das intervenções](exemplo_oclusoes.png)','',
              'Fonte da fotografia e anotação: UBIPr Single Eyes Segmented, Padole e Proença (2012), CC BY-NC-SA 4.0. Oclusões e composição do autor.']
    report_text='\n'.join(lines)+'\n'
    for old,new in [('de30%','de 30%'),('para31%','para 31%'),('de95%','de 95%'),('de70%','de 70%'),
                    ('para69%','para 69%'),('e69%','e 69%'),('usam5000','usam 5.000'),
                    ('semente20261108','semente 20261108'),('semente20261001','semente 20261001'),('seção6.2','seção 6.2')]:
        report_text=report_text.replace(old,new)
    (out/'RESULTADO_PARA_DEFESA.md').write_text(report_text,encoding='utf-8')
    with (out/'tabela_defesa.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=flat[0].keys());writer.writeheader();writer.writerows(flat)
    write(out/'AUDITORIA_FINAL.json',{'counts_recomputed':audit,'paired_drops':paired,'contrast_30_to_31':comparison,
              'sensitivity_fixed_area_defined_480':sensitivity,
              'orientation_difference_at10':orientation10,'bootstrap_seed':20261108,'replicates':5000,
              'example':example,'raw_completion_sha256':digest(run/'CONCLUIDO.json'),
              'analysis_source_sha256':digest(__file__),'figures_sha256':{f.name:digest(f) for f in out.glob('*.png')}})
    print(json.dumps({'report':str(out/'RESULTADO_PARA_DEFESA.md'),'contrast_30_31':comparison,'counts_recomputed':len(audit)},ensure_ascii=False))

if __name__=='__main__':main()
