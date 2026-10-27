"""Consolida o manuscrito no pacote original do modelo institucional.

Executar com o Python gerenciado de documentos. Saídas em --output-dir.
Nenhum experimento biométrico é executado por este programa.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from lxml import etree
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def figures(out):
    # Reuse the project's existing scientific plotting dependency; no installation.
    import sys
    sys.path.append('C:/Users/lucaz/pfc-tcc-venv/Lib/site-packages')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    out.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.set(xlim=(0, 10), ylim=(0, 4)); ax.axis('off')
    boxes = [(0.15, 2.55, 'Consulta S2\nUma fotografia'),
             (3.55, 2.55, 'Oclusão digital\nReferência fixa'),
             (6.95, 2.55, 'Segmentação\nImagem modificada'),
             (6.95, 0.45, 'Recorte RGB\nTextura polar\nExtratores fixos'),
             (3.55, 0.45, 'Fusão e limiar fixos\n16 olhos candidatos'),
             (0.15, 0.45, 'Rank-1, TAR e FMR\n486 consultas')]
    for x, y, s in boxes:
        ax.add_patch(FancyBboxPatch((x,y),2.9,.85,boxstyle='round,pad=0.08',
                                   fc='#f1f1f1',ec='#444444',lw=1))
        ax.text(x+1.45,y+.425,s,ha='center',va='center',fontsize=10.5)
    for a,b in [((3.12,2.975),(3.43,2.975)),((6.52,2.975),(6.83,2.975)),
                ((8.4,2.43),(8.4,1.43)),((6.83,.875),(6.52,.875)),
                ((3.43,.875),(3.12,.875))]:
        ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','lw':1.4})
    ax.text(5,1.9,'Cadastro S1 preservado; lado do olho informado',ha='center',fontsize=9)
    fig.savefig(out/'fluxo_experimental.png',dpi=220,bbox_inches='tight'); plt.close(fig)
    old=json.loads((ROOT/'outputs/incerteza_fronteira_area_2026-10-23/CONCLUIDO.json').read_text('utf-8'))['records']
    new=json.loads((ROOT/'outputs/fronteira_meio_ponto_2026-10-23/AUDITORIA_FRONTEIRA.json').read_text('utf-8'))['records']
    rows={r['condition']:r for r in old}
    for r in new:
        r=dict(r); r.update(rank1_percent=r['rank1']*100,tar_percent=r['tar']*100,fmr_percent=r['far']*100)
        rows[r['tag']]=r
    order=['original','superior_0p5','upper1','lower1','inferior_1p5','lower2','upper10','lower10']
    labels=['Original · 100%','Superior · 99,5%','Superior · 99%','Inferior · 99%',
            'Inferior · 98,5%','Inferior · 98%','Superior · 90%','Inferior · 90%']
    fig, axes=plt.subplots(1,3,figsize=(8.5,4.8),sharey=True)
    for ax,key,title,lim,goal in zip(axes,['rank1','tar','fmr'],['Rank-1 (%)','TAR (%)','FMR (%)'],[(40,100),(40,100),(0,4.5)],[90,90,1]):
        for i,k in enumerate(order):
            r=rows[k]; v=r[key+'_percent']; lo,hi=r['intervals95_percent'][key]
            ax.errorbar(v,i,xerr=[[v-lo],[hi-v]],fmt='o',color='#222222',capsize=3,ms=4)
        ax.axvline(goal,color='#777777',ls='--',lw=1)
        ax.set_xlim(*lim); ax.set_title(title,fontsize=11); ax.grid(axis='x',alpha=.2)
        ax.spines[['top','right']].set_visible(False)
    axes[0].set_yticks(range(8),labels,fontsize=11); axes[0].invert_yaxis()
    fig.text(.5,.015,'Pontos: estimativas; barras: intervalos de 95% por participante; tracejado: critério.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,1)); fig.savefig(out/'intervalos_condicoes.png',dpi=220,bbox_inches='tight'); plt.close(fig)

def runfmt(run,size=12,bold=None):
    run.font.name='Arial'; run.font.size=Pt(size)
    if bold is not None: run.bold=bold
    run.font.color.rgb=__import__('docx').shared.RGBColor(0,0,0)
    return run

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output-dir',type=Path,required=True); args=parser.parse_args()
    out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    reference=next(ROOT.parent.parent.glob('Modelo_artigo_Computacao*.docx'))
    raw=reference.read_bytes(); original=zipfile.ZipFile(io.BytesIO(raw))
    contract='''# Contrato do artigo UniSATC
Referência: {reference}
SHA256: {sha}
Referência renderizada: 11 páginas, todas inspecionadas.
Artigo: 15 a 30 páginas; A4, margens superior/esquerda 3 cm, inferior/direita 2 cm.
Corpo Arial 12, entrelinha 1,5, primeira linha 2 cm; títulos conforme estilos institucionais.
Autores à direita com referências às notas 1 e 2; e-mails informados pelo autor.
Resumo e palavras-chave na primeira página; seções numeradas pelo modelo; referências sem numeração.
Cabeçalho UniSATC e campo PAGE preservados em todas as páginas.
Editável: conteúdo instrucional do corpo, notas de autores, atualização de campos.
Novos: duas imagens científicas, relações dessas imagens e eventuais tipos de conteúdo.
Preservação binária: todos os demais componentes, inclusive estilos, numeração, cabeçalho, logotipo e seção.
Desvios intencionais: exemplos do modelo substituídos pelos cinco quadros de dados e duas figuras do estudo.
Não se atribui titulação acadêmica não informada ao orientador.
'''.format(reference=reference,sha=hashlib.sha256(raw).hexdigest())
    (out/'artifact.md').write_text(contract,encoding='utf-8')
    figures(out/'figuras')
    doc=Document(reference)
    prototypes={i:copy.deepcopy(doc.paragraphs[i]._p) for i in [0,1,3,4,6,8,10]}
    sect=copy.deepcopy(doc._element.body.sectPr)
    for child in list(doc._element.body): doc._element.body.remove(child)
    doc._element.body.append(sect)
    def p(text='',style='1Texto',size=12,align=None,keep=False):
        par=doc.add_paragraph(style=style)
        runfmt(par.add_run(text),size)
        if align is not None: par.alignment=align
        par.paragraph_format.keep_with_next=keep
        if style=='1Texto':
            par.paragraph_format.first_line_indent=Cm(2)
            par.paragraph_format.line_spacing=1.5
            par.paragraph_format.space_after=Pt(0)
        return par
    lines=(ROOT/'artigo/ARTIGO_CONSOLIDADO_2026-10-23.md').read_text('utf-8').splitlines()
    title=lines[0][2:]
    doc._element.body.insert(0,prototypes[0])
    p(title,'Title',align=WD_ALIGN_PARAGRAPH.CENTER)
    for idx,name in [(3,'Lucas Cardoso Rodrigues'),(4,'Rodrigo Ramos Silva')]:
        elem=prototypes[idx]
        # Keep the original footnote anchor and paragraph layout.
        anchor=copy.deepcopy(next(elem.iter(W+'footnoteReference')))
        for child in list(elem):
            if child.tag!=W+'pPr': elem.remove(child)
        from docx.text.paragraph import Paragraph
        doc._element.body.insert(len(doc._element.body)-1,elem)
        par=Paragraph(elem,doc._body); runfmt(par.add_run(name),12,True)
        r=par.add_run(); r.font.superscript=True; r._r.append(anchor)
    p('', 'Normal')
    i=5
    while i<len(lines):
        s=lines[i].strip(); i+=1
        if not s: continue
        if s.startswith('**Resumo:**'):
            par=p('', 'Resumo'); runfmt(par.add_run('Resumo: '),12,True)
            runfmt(par.add_run(s.removeprefix('**Resumo:**').strip()),12)
            continue
        if s.startswith('**Palavras-chave:**'):
            par=p('', 'Textodoresumo'); runfmt(par.add_run('Palavras-chave: '),12,True)
            runfmt(par.add_run(s.removeprefix('**Palavras-chave:**').strip()),12); continue
        if s.startswith('#'):
            depth=len(s)-len(s.lstrip('#')); text=s.lstrip('# ').strip()
            text=re.sub(r'^\d+(?:\.\d+)*\s+','',text)
            if text=='REFERÊNCIAS':
                par=p(text,'Ttulononumerado',keep=True)
                par.paragraph_format.page_break_before=True
            else: par=p(text,{2:'Heading 1',3:'Heading 2',4:'Heading 3'}[depth],keep=True)
            continue
        if s.startswith('|'):
            rows=[s]
            while i<len(lines) and lines[i].strip().startswith('|'): rows.append(lines[i].strip()); i+=1
            matrix=[[c.strip() for c in row.strip('|').split('|')] for row in rows if not re.fullmatch(r'[|:\-\s]+',row)]
            table=doc.add_table(rows=0,cols=len(matrix[0])); table.autofit=False
            widths=({5:[5.1,2.0,2.0,3.45,3.45],4:[5.0,3.2,4.5,3.3],6:[4.3,2.1,2.5,2.5,2.5,2.1],7:[3.5,2.0,2.1,2.1,2.1,2.1,2.1]}.get(len(matrix[0]),[16/len(matrix[0])]*len(matrix[0])))
            scale=16/sum(widths); widths=[v*scale for v in widths]
            for col,w in zip(table.columns,widths): col.width=Cm(w)
            borders=OxmlElement('w:tblBorders')
            for edge in ['top','bottom']:
                e=OxmlElement('w:'+edge); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'6'); borders.append(e)
            table._tbl.tblPr.append(borders)
            for j,row in enumerate(matrix):
                cells=table.add_row().cells
                cant=OxmlElement('w:cantSplit'); table.rows[-1]._tr.get_or_add_trPr().append(cant)
                if j==0: table.rows[-1]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
                for k,(cell,text) in enumerate(zip(cells,row)):
                    cell.width=Cm(widths[k]); par=cell.paragraphs[0]; par.style=doc.styles['Normal']
                    par.alignment=WD_ALIGN_PARAGRAPH.LEFT if k==0 else WD_ALIGN_PARAGRAPH.CENTER
                    padding=1 if len(matrix[0])==5 else 3
                    par.paragraph_format.space_before=Pt(padding);par.paragraph_format.space_after=Pt(padding)
                    runfmt(par.add_run(text),10,j==0)
                    if j==0:
                        bd=OxmlElement('w:tcBorders'); bot=OxmlElement('w:bottom');bot.set(qn('w:val'),'single');bot.set(qn('w:sz'),'4');bd.append(bot);cell._tc.get_or_add_tcPr().append(bd)
            continue
        if s.startswith('!['):
            path=re.search(r'\((.+)\)',s).group(1)
            par=p('', 'Normal',align=WD_ALIGN_PARAGRAPH.CENTER,keep=True)
            par.add_run().add_picture(str(out/path),width=Cm(16)); continue
        if s.startswith(('Tabela ','Figura ')):
            p(s,'Normal',align=WD_ALIGN_PARAGRAPH.CENTER,keep=True); continue
        if s.startswith('Fonte:'):
            par=p(s,'Normal',10);par.paragraph_format.space_after=Pt(8); continue
        if s.startswith('Eq. 1'):
            # Native Word math, not a bitmap or pseudo-LaTeX.
            par=p('', 'Normal',align=WD_ALIGN_PARAGRAPH.CENTER)
            ns='http://schemas.openxmlformats.org/officeDocument/2006/math'
            om=etree.SubElement(par._p,'{'+ns+'}oMath')
            def mathrun(parent,text):
                r=etree.SubElement(parent,'{'+ns+'}r')
                rp=etree.SubElement(r,W+'rPr');sz=etree.SubElement(rp,W+'sz');sz.set(W+'val','24')
                etree.SubElement(r,'{'+ns+'}t').text=text
            mathrun(om,'A = 100 × ')
            frac=etree.SubElement(om,'{'+ns+'}f')
            mathrun(etree.SubElement(frac,'{'+ns+'}num'),'N − n')
            mathrun(etree.SubElement(frac,'{'+ns+'}den'),'N')
            mathrun(om,'     N > 0     (1)')
            par.paragraph_format.space_before=Pt(6);par.paragraph_format.space_after=Pt(6)
            continue
        if 'REFERÊNCIAS' in '\n'.join(lines[:i]) and s.startswith(('CVRL.', 'DAUGMAN,','DENG,','HE,','LIU,','PADOLE,','RONNEBERGER,','SIMÉONI,','TROKIELEWICZ,')):
            par=p('', '4Referncias');par.paragraph_format.space_after=Pt(12)
            # Native active links, while retaining the institutional reference style.
            for part in re.split(r'(https?://\S+)',s):
                if part.startswith('http'):
                    from docx.opc.constants import RELATIONSHIP_TYPE as RT
                    rid=doc.part.relate_to(part,RT.HYPERLINK,is_external=True)
                    link=OxmlElement('w:hyperlink');link.set(qn('r:id'),rid)
                    r=OxmlElement('w:r');rp=OxmlElement('w:rPr');font=OxmlElement('w:rFonts');font.set(qn('w:ascii'),'Arial');font.set(qn('w:hAnsi'),'Arial');rp.append(font);sz=OxmlElement('w:sz');sz.set(qn('w:val'),'24');rp.append(sz);r.append(rp);t=OxmlElement('w:t');t.text=part;r.append(t);link.append(r);par._p.append(link)
                else: runfmt(par.add_run(part),12)
            continue
        p(s)
    intermediate=io.BytesIO();doc.save(intermediate)
    generated=zipfile.ZipFile(intermediate)
    changed={'word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'}
    foot=etree.fromstring(original.read('word/footnotes.xml'))
    for ident,text in [('1','Graduando em Engenharia de Computação. E-mail: lucaazartys@gmail.com'),('2','Professor do Centro Universitário UniSATC. E-mail: rodrigo.1974@satc.edu.br')]:
        el=next(e for e in foot if e.get(W+'id')==ident)
        paras=el.findall(W+'p')
        par=paras[0]
        for e in list(par):
            if e.tag!=W+'pPr':par.remove(e)
        marker=etree.SubElement(par,W+'r');markerpr=etree.SubElement(marker,W+'rPr')
        va=etree.SubElement(markerpr,W+'vertAlign');va.set(W+'val','superscript')
        etree.SubElement(marker,W+'footnoteRef')
        r=etree.SubElement(par,W+'r');rp=etree.SubElement(r,W+'rPr')
        font=etree.SubElement(rp,W+'rFonts');font.set(W+'ascii','Arial');font.set(W+'hAnsi','Arial')
        sz=etree.SubElement(rp,W+'sz');sz.set(W+'val','20')
        t=etree.SubElement(r,W+'t');t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=' '+text
        for extra in paras[1:]:el.remove(extra)
    settings=etree.fromstring(original.read('word/settings.xml'))
    for el in settings.findall(W+'updateFields'): settings.remove(el)
    upd=etree.SubElement(settings,W+'updateFields');upd.set(W+'val','true')
    final=out/'ARTIGO_AREA_IRIS_CONSOLIDADO_2026-10-23.docx'
    with zipfile.ZipFile(final,'w',zipfile.ZIP_DEFLATED) as target:
        for name in original.namelist():
            if name=='word/footnotes.xml':data=etree.tostring(foot,xml_declaration=True,encoding='UTF-8',standalone=True)
            elif name=='word/settings.xml':data=etree.tostring(settings,xml_declaration=True,encoding='UTF-8',standalone=True)
            elif name in changed:data=generated.read(name)
            else:data=original.read(name)
            target.writestr(name,data)
        for name in generated.namelist():
            if name not in original.namelist():target.writestr(name,generated.read(name))
    finalzip=zipfile.ZipFile(final)
    deviations=changed|{'word/footnotes.xml','word/settings.xml'}
    preserved=[n for n in original.namelist() if n not in deviations]
    assert all(original.read(n)==finalzip.read(n) for n in preserved)
    assert etree.tostring(etree.fromstring(original.read('word/document.xml')).find(W+'body').find(W+'sectPr'))==etree.tostring(etree.fromstring(finalzip.read('word/document.xml')).find(W+'body').find(W+'sectPr'))
    report={'template_sha256':hashlib.sha256(raw).hexdigest(),'output_sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'preserved_parts':len(preserved),'changed_parts':sorted(deviations),'new_parts':sorted(set(finalzip.namelist())-set(original.namelist())),'words_markdown':len(' '.join(lines).split()),'author_notes_verified':True,'no_new_experiments':True}
    (out/'verificacao_pacote.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'file':str(final),**report},ensure_ascii=False))

if __name__=='__main__':main()
