"""Gera figuras, relatorio e HTML local a partir do ensaio completo, sem nova inferencia."""
from pathlib import Path
import csv
import json
import html
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from avaliar_robustez_reconhecimento import ROOT, BRANCHES, perturb, paired_ci, metrics
from treinar_segmentacao_ubipr import decode_mask

OUT=ROOT/'outputs/robustez_reconhecimento_2026-10-01'
NAMES={'inteira':'Imagem inteira','iris_referencia':'Íris · referência manual','iris_unet':'Íris · U-Net'}
KINDS={'oclusao_superior':'Oclusão superior','oclusao_inferior':'Oclusão inferior',
       'desfoque_iris':'Desfoque na íris','contraste_iris':'Redução de contraste na íris'}
COLORS={'inteira':'#146b8c','iris_referencia':'#c05d25','iris_unet':'#6848a3'}


def read_csv(name):
    with (OUT/name).open(encoding='utf-8-sig') as f: return list(csv.DictReader(f))


def fmt(x): return f'{float(x):.2f}'.replace('.',',')


def main():
    if not (OUT/'CONCLUIDO.json').exists(): raise RuntimeError('Ensaio ainda nao concluido')
    rows=read_csv('resumo.csv'); natural=read_csv('qualidade_natural.csv')
    queries=read_csv('consultas.csv'); manifest=read_csv('manifesto_auditado.csv')
    config=json.loads((OUT/'protocolo.json').read_text(encoding='utf-8'))
    calibration=json.loads((OUT/'calibracao.json').read_text(encoding='utf-8'))
    baseline={b:next(r for r in rows if r['branch']==b and r['condition']=='original') for b in BRANCHES}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    for metric,filename,title,ylabel in [
        ('rank1','curvas_rank1.png','Reconhecimento entre sessões · galeria fixa de 32 olhos','Identificação Rank-1 (%)'),
        ('loss_rank1_pp','perda_rank1_ic95.png','Perda pareada de identificação · IC 95% por pessoa','Queda de Rank-1 (pontos percentuais)'),
        ('tar','curvas_tar.png','Verificação · limiar calibrado no original da validação','TAR no limiar fixo (%)')]:
        fig,axes=plt.subplots(2,2,figsize=(12,8))
        for ax,(kind,name) in zip(axes.flat,KINDS.items()):
            for b in BRANCHES:
                subset=[baseline[b]]+[r for r in rows if r['branch']==b and r['condition']==kind]
                x=[int(r['level']) for r in subset]
                y=np.array([float(r[metric]) for r in subset])*(1 if metric=='loss_rank1_pp' else 100)
                ax.plot(x,y,'o-',color=COLORS[b],label=NAMES[b],lw=2,ms=4)
                if metric=='loss_rank1_pp':
                    ax.fill_between(x,[float(r['ci_low_pp']) for r in subset],[float(r['ci_high_pp']) for r in subset],color=COLORS[b],alpha=.12)
            ax.set_title(name); ax.set_ylabel(ylabel)
            ax.set_xlabel('Sigma / largura da íris (%)' if kind=='desfoque_iris' else 'Mistura com cinza (%)' if kind=='contraste_iris' else 'Área anotada substituída (%)')
            ax.grid(alpha=.2); ax.axhline(0,color='#777',lw=.7)
            if metric!='loss_rank1_pp': ax.set_ylim(0,100)
        handles,labels=axes.flat[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='lower center',ncol=3,frameon=False)
        fig.suptitle(title,fontsize=16,y=.99)
        fig.tight_layout(rect=(0,.05,1,.96)); fig.savefig(OUT/filename,dpi=160); plt.close(fig)

    # Visual examples selected reproducibly by median iris-mask size, not recognition outcome.
    candidates=[r for r in manifest if r['split']=='test' and r['session']=='2' and int(r['iris_pixels'])>0]
    candidates.sort(key=lambda r:int(r['iris_pixels']))
    example=candidates[len(candidates)//2]
    with Image.open(example['image']) as im: image=im.convert('RGB')
    with Image.open(example['mask']) as m: mask=decode_mask(m)==1
    fig,axes=plt.subplots(4,4,figsize=(12,12))
    for row,(kind,levels) in enumerate([('oclusao_superior',[20,40,60]),('oclusao_inferior',[20,40,60]),('desfoque_iris',[1,3,5]),('contraste_iris',[25,50,75])]):
        for col,level in enumerate([0]+levels):
            altered,_=perturb(image,mask,kind if level else 'original',level)
            axes[row,col].imshow(altered); axes[row,col].axis('off')
            axes[row,col].set_title('Original' if not level else f'{KINDS[kind]}\n{level}%',fontsize=10,pad=9)
    fig.suptitle('Exemplo real do UBIPr e perturbações restritas à íris anotada',fontsize=15)
    fig.subplots_adjust(top=.91,bottom=.03,hspace=.40,wspace=.08)
    fig.savefig(OUT/'exemplos_perturbacoes.png',dpi=150); plt.close(fig)

    fig,axes=plt.subplots(1,3,figsize=(13,4.8))
    for ax,feature,label in zip(axes,('sharpness','contrast','occupancy'),('Nitidez (proxy)','Contraste','Área de íris / imagem')):
        for b in BRANCHES:
            selected=[r for r in natural if r['branch']==b and r['feature']==feature]
            ax.plot(range(3),[100*float(r['rank1']) for r in selected],'o-',label=NAMES[b],color=COLORS[b])
        ax.set_xticks(range(3),['Baixo','Médio','Alto']); ax.set_title(label); ax.set_ylim(0,100); ax.grid(alpha=.2)
        ax.set_xlabel('Terços definidos na validação'); ax.set_ylabel('Rank-1 (%)')
    fig.suptitle('Imagens originais: associação com qualidade visual, sem inferência causal',fontsize=13)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',ncol=3,frameon=False)
    fig.tight_layout(rect=(0,.06,1,.93)); fig.savefig(OUT/'qualidade_natural.png',dpi=160); plt.close(fig)

    fig,axes=plt.subplots(3,4,figsize=(12,9))
    for j,(feature,label) in enumerate([('sharpness','Nitidez'),('contrast','Contraste'),('occupancy','Proporção de íris')]):
        bins=[r for r in natural if r['branch']=='inteira' and r['feature']==feature]
        edges=[float(bins[0]['validation_cut1']),float(bins[0]['validation_cut2'])]
        for k,group in enumerate((0,2)):
            pool=sorted([r for r in candidates if np.searchsorted(edges,float(r[feature]),side='right')==group],key=lambda r:float(r[feature]))
            for l,fraction in enumerate((.33,.67)):
                r=pool[min(len(pool)-1,int(len(pool)*fraction))]
                with Image.open(r['image']) as im: visual=im.convert('RGB')
                ax=axes[j,2*k+l]; ax.imshow(visual); ax.axis('off')
                ax.set_title(f"{label} · {'baixo' if group==0 else 'alto'}\n{Path(r['image']).stem}",fontsize=9)
    fig.suptitle('Imagens originais do UBIPr · exemplos dos grupos de qualidade\nSem alteração sintética ou atribuição de diagnóstico',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.94)); fig.savefig(OUT/'exemplos_qualidade_natural.png',dpi=150); plt.close(fig)

    # Cluster CIs for natural low-vs-high association. Not paired condition intervention.
    natural_ci=[]
    for b in BRANCHES:
        q=[r for r in queries if r['branch']==b and r['condition']=='original']
        by_image={r['image']:r for r in q}
        for feature in ('sharpness','contrast','occupancy'):
            bins=[r for r in natural if r['branch']==b and r['feature']==feature]
            edge=np.array([float(bins[0]['validation_cut1']),float(bins[0]['validation_cut2'])])
            cluster=[]
            for subject in sorted({r['subject'] for r in candidates}):
                cs=[r for r in candidates if r['subject']==subject]
                values=[]
                for group in (0,2):
                    selected=[r for r in cs if r[feature] and np.searchsorted(edge,float(r[feature]),side='right')==group]
                    values.extend([sum(int(by_image[Path(r['image']).name]['correct']) for r in selected),len(selected)])
                cluster.append(values)
            cluster=np.array(cluster); rng=np.random.default_rng(20261001)
            res=cluster[rng.integers(0,len(cluster),(5000,len(cluster)))].sum(1)
            ok=(res[:,1]>0)&(res[:,3]>0)
            delta=100*(res[ok,2]/res[ok,3]-res[ok,0]/res[ok,1])
            ci=np.quantile(delta,[.025,.975])
            natural_ci.append({'branch':b,'feature':feature,'high_minus_low_pp':100*(float(bins[2]['rank1'])-float(bins[0]['rank1'])),
               'ci_low_pp':float(ci[0]),'ci_high_pp':float(ci[1]),'successful_bootstrap_replicates':int(ok.sum())})
    with (OUT/'associacao_qualidade_ic95.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=natural_ci[0]); w.writeheader(); w.writerows(natural_ci)

    # Additional natural-quality analysis controls identity: same eye must have >=2
    # low and >=2 high quality captures, using the unchanged validation cut points.
    within=[]
    for b in BRANCHES:
        q={r['image']:r for r in queries if r['branch']==b and r['condition']=='original'}
        for feature in ('sharpness','contrast','occupancy'):
            bins=[r for r in natural if r['branch']==b and r['feature']==feature]
            edges=[float(bins[0]['validation_cut1']),float(bins[0]['validation_cut2'])]
            differences=[]
            for subject,side in sorted({(r['subject'],r['side']) for r in candidates}):
                cs=[r for r in candidates if r['subject']==subject and r['side']==side]
                low=[r for r in cs if np.searchsorted(edges,float(r[feature]),side='right')==0]
                high=[r for r in cs if np.searchsorted(edges,float(r[feature]),side='right')==2]
                if min(len(low),len(high))<2: continue
                low_acc=np.mean([int(q[Path(r['image']).name]['correct']) for r in low])
                high_acc=np.mean([int(q[Path(r['image']).name]['correct']) for r in high])
                differences.append((subject,100*(high_acc-low_acc),len(low),len(high)))
            subjects=sorted({v[0] for v in differences})
            if subjects:
                sums=np.array([sum(v[1] for v in differences if v[0]==s) for s in subjects])
                counts=np.array([sum(v[0]==s for v in differences) for s in subjects])
                draws=np.random.default_rng(20261001).integers(0,len(subjects),(5000,len(subjects)))
                delta=sums[draws].sum(1)/counts[draws].sum(1); ci=np.quantile(delta,[.025,.975])
                within.append({'branch':b,'feature':feature,'eyes':len(differences),'people':len(subjects),
                    'low_queries':sum(v[2] for v in differences),'high_queries':sum(v[3] for v in differences),
                    'mean_eye_high_minus_low_pp':float(sums.sum()/counts.sum()),'ci_low_pp':float(ci[0]),'ci_high_pp':float(ci[1])})
    if within:
        with (OUT/'qualidade_mesmo_olho.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=within[0]); w.writeheader(); w.writerows(within)

    # Sensitivity analysis: exclude only the six original empty references, fixed
    # cohort across all conditions, never excluding a perturbation-induced failure.
    test_manifest=[r for r in manifest if r['split']=='test' and r['session']=='2']
    cohort=np.array([int(r['iris_pixels'])>0 for r in test_manifest])
    people=np.array([int(r['subject']) for r in test_manifest])[cohort]
    sensitivity=[]
    for b in BRANCHES:
        with np.load(OUT/f'scores_{b}_original.npz') as z:
            base,bc,ba=metrics(z['scores'][cohort],z['labels'][cohort],calibration[b]['threshold'],z['valid'][cohort])
        for r in [r for r in rows if r['branch']==b]:
            suffix='original' if r['condition']=='original' else f"{r['condition']}_{r['level']}"
            with np.load(OUT/f'scores_{b}_{suffix}.npz') as z:
                mm,correct,accepted=metrics(z['scores'][cohort],z['labels'][cohort],calibration[b]['threshold'],z['valid'][cohort])
            ci=paired_ci(bc,correct,people)
            sensitivity.append({'branch':b,'condition':r['condition'],'level':r['level'],**mm,
                'loss_rank1_pp':100*(base['rank1']-mm['rank1']),'ci_low_pp':ci[0],'ci_high_pp':ci[1]})
    with (OUT/'sensibilidade_referencias_validas.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=sensitivity[0]); w.writeheader(); w.writerows(sensitivity)

    lines=['# Resultado experimental — perda de reconhecimento sob alterações visuais',
        '', '**Data:** 01/10/2026. **Execução completa:** UBIPr, DINOv3 ViT-L/16 congelado, U-Net congelada. Sem rótulos clínicos.',
        '', '## 1. O que foi executado', '',
        f"Validação: {config['counts']['val']['people']} pessoas, {config['counts']['val']['eyes']} olhos, 482 consultas. Teste: 16 pessoas distintas da validação, 32 olhos e 486 consultas; 474 imagens de galeria da sessão 1. Cada identidade é pessoa + lado. Foram avaliadas 13 condições em três entradas, totalizando 39 combinações e 18.954 decisões de identificação de teste. Não houve subamostragem de desenvolvimento.",
        '', 'A galeria é fixa e formada pela média normalizada dos embeddings da sessão 1. Apenas consultas da sessão 2 recebem perturbações. Os limiares de verificação são fixados no original da validação, com FAR empírica de no máximo 1%, tratando empates conservadoramente. A FAR de teste é medida, não presumida.',
        '', 'As alterações são restritas aos pixels anotados como íris: substituição por cinza 128 em 20/40/60% da área, começando por cima ou por baixo; desfoque gaussiano com sigma de 1/3/5% da largura da caixa da íris; mistura com cinza 128 em 25/50/75%. Não há alteração direta de pele ou sobrancelha. Níveis de desfoque e contraste não são percentuais de oclusão nem gravidade de doença.',
        '', 'O recorte manual usa a máscara original fixa (controle com informação privilegiada, não solução de produção). A U-Net segmenta novamente cada consulta alterada, incluindo o efeito da segmentação no reconhecimento. Os dois recortes usam a mesma regra de caixa e margem. Máscara prevista vazia conta como falha de extração, erro de identificação e rejeição. Seis consultas têm referência manual vazia: permanecem no denominador operacional de 486 e não recebem perturbação localizada; a coorte de 480 referências não vazias é avaliada separadamente em `sensibilidade_referencias_validas.csv`, sem excluir falhas causadas pelas perturbações.',
        '', 'A auditoria por SHA-256 não encontrou imagens exatamente duplicadas na população avaliada. Não é uma auditoria de quase-duplicatas ou validação clínica. Os ICs são percentis de 5.000 reamostragens por pessoa, mantendo seus olhos/consultas agrupados e a galeria fixa. São ICs pontuais, sem correção simultânea por múltiplas condições.',
        '', '## 2. Linha de base corrigida para identidade ocular', '',
        '| Entrada | Rank-1 | EER descritivo | TAR | FAR observada | Falhas de extração |',
        '|---|---:|---:|---:|---:|---:|']
    for b in BRANCHES:
        r=baseline[b]
        lines.append(f"| {NAMES[b]} | {fmt(100*float(r['rank1']))}% | {fmt(100*float(r['eer_descriptive']))}% | {fmt(100*float(r['tar']))}% | {fmt(100*float(r['far']))}% | {r['extraction_failures']} |")
    lines+=['','Esses valores não devem ser comparados diretamente aos 74,28% anteriores: a galeria anterior agrupava pessoas e misturava lados; agora são 32 identidades oculares. A máscara manual e a U-Net são entradas de um extrator visual genérico, ainda sem adaptação específica para reconhecimento da textura da íris.',
        '', '## 3. Perda medida nas condições mais intensas predefinidas', '',
        '| Alteração | Entrada | Rank-1 alterado | Queda absoluta | IC 95% da queda | Queda relativa à base | TAR | FAR | Falhas |',
        '|---|---|---:|---:|---|---:|---:|---:|---:|']
    for kind in KINDS:
        max_level=max(int(r['level']) for r in rows if r['condition']==kind)
        for b in BRANCHES:
            r=next(r for r in rows if r['condition']==kind and int(r['level'])==max_level and r['branch']==b)
            rel=float(r['loss_rank1_pp'])/(float(baseline[b]['rank1']) or np.nan)
            lines.append(f"| {KINDS[kind]} {max_level}% | {NAMES[b]} | {fmt(100*float(r['rank1']))}% | {fmt(r['loss_rank1_pp'])} pp | [{fmt(r['ci_low_pp'])}; {fmt(r['ci_high_pp'])}] pp | {fmt(rel)}% | {fmt(100*float(r['tar']))}% | {fmt(100*float(r['far']))}% | {r['extraction_failures']} |")
    lines+=['','Queda negativa significa melhora observada. IC que cruza zero não sustenta direção clara da mudança nesta amostra. Não foram escolhidos os níveis pelo pior resultado: a tabela usa o maior nível previamente definido de cada família. A tabela completa com todos os níveis está em `resumo.csv`.',
        '', '![Curvas de reconhecimento](curvas_rank1.png)', '', '![Perda e incerteza](perda_rank1_ic95.png)',
        '', '## 4. Alterações e qualidade nas imagens originais', '',
        'Foram estratificadas as consultas originais por nitidez (variância do Laplaciano na parte interna da máscara, após padronização da caixa para 128 × 128), contraste (desvio-padrão de intensidade na íris) e proporção de pixels de íris na imagem. Os cortes são os terços da validação. Esses indicadores não são diagnósticos; proporção de íris também depende de distância, escala e olhar, e não mede oclusão anatômica.', '',
        '| Entrada | Indicador | Rank-1 baixo | n baixo | Rank-1 alto | n alto | Alto − baixo | IC 95% |',
        '|---|---|---:|---:|---:|---:|---:|---|']
    for b in BRANCHES:
        for feature in ('sharpness','contrast','occupancy'):
            ns=[r for r in natural if r['branch']==b and r['feature']==feature]
            ci=next(r for r in natural_ci if r['branch']==b and r['feature']==feature)
            lines.append(f"| {NAMES[b]} | {feature} | {fmt(100*float(ns[0]['rank1']))}% | {ns[0]['queries']} | {fmt(100*float(ns[2]['rank1']))}% | {ns[2]['queries']} | {fmt(ci['high_minus_low_pp'])} pp | [{fmt(ci['ci_low_pp'])}; {fmt(ci['ci_high_pp'])}] |")
    lines+=['','Esses grupos contêm composições distintas de pessoas e imagens. Diferenças são associações observacionais, não perda causal por anomalia. O ensaio pareado da seção 3 é o controle que mantém as mesmas consultas e identidades entre condições.',
        '', '### Controle adicional: comparação de qualidade dentro do mesmo olho', '',
        'Incluímos apenas olhos com pelo menos duas consultas em cada extremo de qualidade, conservando os cortes da validação. Calculamos alto − baixo por olho e a média entre olhos, com bootstrap por pessoa. O controle remove a troca de identidade entre grupos, mas posição do olhar, iluminação e outros fatores continuam confundidos. Análise exploratória complementar, sem redefinir o teste principal.', '',
        '| Entrada | Indicador | Olhos | Pessoas | Alto − baixo por olho | IC 95% |',
        '|---|---|---:|---:|---:|---|']
    for r in within:
        lines.append(f"| {NAMES[r['branch']]} | {r['feature']} | {r['eyes']} | {r['people']} | {fmt(r['mean_eye_high_minus_low_pp'])} pp | [{fmt(r['ci_low_pp'])}; {fmt(r['ci_high_pp'])}] |")
    lines+=[
        '', '![Qualidade natural](qualidade_natural.png)',
        '', '![Exemplos originais](exemplos_qualidade_natural.png)',
        '', 'As imagens acima são escolhidas em posições de um e dois terços dentro de cada grupo de qualidade, sem consulta ao resultado de reconhecimento. Não representam rótulos de doença.', '', '## 5. Amostra visual', '',
        f"Exemplo selecionado pela área mediana de íris anotada, sem consultar acerto/erro: `{Path(example['image']).name}`.",
        '', '![Exemplo](exemplos_perturbacoes.png)', '', '## 6. Limites e comparação futura', '',
        'O experimento quantifica a robustez deste sistema a alterações visuais definidas. Não estima efeito clínico de catarata, ceratite ou outra doença. Uma pequena perda na imagem inteira pode ocorrer porque o contexto periocular permanece disponível; não comprova que a textura da íris resistiu. Um baseline baixo nos recortes limita a interpretação de pequenas perdas adicionais (efeito de piso).',
        '', 'Há apenas 16 pessoas no teste e ICs condicionais à galeria fixa. Os resultados são descritivos deste ensaio exploratório: o teste do UBIPr já foi analisado em etapas anteriores. As severidades foram fixadas antes desta execução, mas não se deve apresentar o conjunto como um novo teste externo nunca observado.',
        '', 'Com Warsaw/CMPD: reutilizar definição de identidade, métricas, contagem de falhas e comparação pareada quando os dados permitirem; calibrar em validação própria do novo domínio, sem ajuste no teste. Comparar diferenças dentro de cada base, não subtrair acurácias brutas de bases com galerias, sensores e populações distintos. Pré/pós-cirurgia não isola automaticamente efeito de doença.',
        '', '## 7. Reprodução e artefatos', '',
        'A partir da pasta `pfc1-segmentacao-mmu`:', '', '```powershell',
        '& ../.venv/Scripts/python.exe -m unittest test_robustez_reconhecimento -v',
        '& ../.venv/Scripts/python.exe -u avaliar_robustez_reconhecimento.py',
        '& ../.venv/Scripts/python.exe relatar_robustez_reconhecimento.py', '```', '',
        'Os caches são retomáveis e vinculados ao hash do script. `protocolo.json` registra condições e hashes; `manifesto_auditado.csv` contém imagens e qualidade; `calibracao.json` contém os limiares; `scores_*.npz` preservam escores; `consultas.csv` preserva decisões individuais; `resumo.csv` contém métricas e ICs. Arquivos de imagem e embeddings devem permanecer sujeitos aos termos da base.',
        '', 'Verificação automatizada: cinco testes cobrem identidade ocular, empates de limiar, falhas de extração, preservação do contexto/área perturbada e bootstrap pareado.']
    report='\n'.join(lines)+'\n'; (OUT/'RELATORIO_RESULTADOS.md').write_text(report,encoding='utf-8')

    # Self-contained HTML: raster charts embedded; no browser/network dependency.
    import base64
    cards=''.join(f'<div class="card"><h3>{NAMES[b]}</h3><strong>{fmt(100*float(baseline[b]["rank1"]))}%</strong><p>Rank-1 original · 32 olhos</p></div>' for b in BRANCHES)
    images=''.join('<section><img src="data:image/png;base64,'+base64.b64encode((OUT/name).read_bytes()).decode()+'"></section>' for name in ['curvas_rank1.png','perda_rank1_ic95.png','curvas_tar.png','qualidade_natural.png','exemplos_qualidade_natural.png','exemplos_perturbacoes.png'])
    table='<table><tr><th>Alteração</th><th>Entrada</th><th>Rank-1</th><th>Perda (pp)</th><th>IC 95% (pp)</th></tr>'
    for r in rows:
        if r['condition']=='original': continue
        table+=f'<tr><td>{KINDS[r["condition"]]} {r["level"]}%</td><td>{NAMES[r["branch"]]}</td><td>{fmt(100*float(r["rank1"]))}%</td><td>{fmt(r["loss_rank1_pp"])}</td><td>{fmt(r["ci_low_pp"])} a {fmt(r["ci_high_pp"])}</td></tr>'
    page='<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Perda de reconhecimento · UBIPr</title><style>body{font:16px system-ui;color:#203346;background:#f4f7fa;max-width:1200px;margin:auto;padding:36px}h1{font-size:34px}header p{max-width:900px;line-height:1.6}.cards{display:flex;gap:18px}.card,section{background:white;padding:24px;border-radius:12px;margin:20px 0}.card{flex:1}strong{font-size:34px;color:#146b8c}img{width:100%;height:auto}table{width:100%;border-collapse:collapse;background:white}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}small{line-height:1.6;display:block}@media print{body{padding:0}section{break-inside:avoid}.cards{break-inside:avoid}}</style><header><p>PFC I · 01 OUT 2026 · EXPERIMENTO COMPLETO</p><h1>Quanto o reconhecimento perde?</h1><p>486 consultas · 32 identidades oculares · 16 pessoas de teste · 13 condições · 3 entradas. Galeria fixa entre sessões e limiar definido em validação separada. Alterações sintéticas restritas à íris e análise da qualidade das imagens originais.</p><p><b>Resultado de robustez visual, sem atribuição a doenças.</b> A galeria anterior reunia olhos por pessoa; a linha de base foi recalculada.</p></header><div class="cards">'+cards+'</div>'+images+'<h2>Todos os resultados pareados</h2>'+table+'</table><section><small>IC 95%: 5.000 reamostragens por pessoa, galeria fixa; intervalos pontuais. Queda negativa indica melhora observada. Grupos de qualidade natural são observacionais. Níveis de desfoque representam sigma/largura da íris; níveis de contraste representam mistura com cinza. Não são gravidade clínica. Detalhes, FAR, TAR, falhas e comandos de reprodução: RELATORIO_RESULTADOS.md e arquivos CSV na mesma pasta.</small></section></html>'
    (OUT/'APRESENTACAO_RESULTADOS.html').write_text(page,encoding='utf-8')
    print('Relatorio, HTML e 6 figuras gerados.')


if __name__=='__main__': main()
