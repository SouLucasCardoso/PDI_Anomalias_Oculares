"""Atualiza artigo a partir do modelo UniSatc preservando o pacote institucional."""
from __future__ import annotations
import argparse,copy,hashlib,io,json,re,zipfile
from pathlib import Path
from lxml import etree
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT=Path(__file__).resolve().parents[1]
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
TITLE='INFLUÊNCIA DA ÁREA PRESERVADA DA ÍRIS NA IDENTIFICAÇÃO OCULAR SOB OCLUSÕES CONTROLADAS'


def bibliography():
    source=(ROOT/'artigo/revisao_bibliografica_2026-11-05/referencias.bib').read_text(encoding='utf-8')
    keep={'iso29794_6_2015','iso19795_1_2021','nist7820','nist8013','nist8207','du2005','daugman2004','daugman2007',
          'hollingsworth2009bits','hofbauer2016','hofbauer2019','pessaud2026','nguyen2024','aslam2009','roizenblatt2004',
          'dhir2010','trokielewicz2015assessment','trokielewicz2017','frasca2024','nigam2019','seyeddain2014'}
    refs=[]
    for typ,key,body in re.findall(r'@(\w+)\{([^,]+),\s*(.*?)\n\}',source,re.S):
        if key not in keep:continue
        fields={k:re.sub(r'[{}]','',v).strip() for k,v in re.findall(r'^\s*(\w+)\s*=\s*\{(.*)\},?\s*$',body,re.M)}
        authors=fields.get('author','').split(' and ')
        def name(author):
            surname,sep,first=author.partition(',')
            if not sep and ' ' in author:
                first,surname=author.rsplit(' ',1);sep=','
            return surname.upper()+(', '+first.strip() if sep else '')
        names='; '.join(map(name,authors)) if len(authors)<=3 else name(authors[0])+' et al.'
        journal=fields.get('journal',fields.get('booktitle',fields.get('institution',fields.get('organization',''))))
        details=''
        for field,prefix in [('volume','v.'),('number','n.'),('pages','p.')]:
            if fields.get(field):details+=f", {prefix} {fields[field].replace('--','-')}"
        year=fields.get('year','[s.d.]')
        url=fields.get('url','https://doi.org/'+fields.get('doi',''))
        refs.append(f"{names.rstrip('.')}. {fields.get('title','')}. {journal}{details}, {year}. Disponível em: {url}. Acesso em: 5 nov. 2026.")
    old=(ROOT/'artigo/ARTIGO_CONSOLIDADO_2026-10-27.md').read_text(encoding='utf-8')
    oldrefs=old.split('## REFERÊNCIAS',1)[1]
    prefixes=('CVRL.','DENG,','HE,','KIRILLOV,','LIU,','PADOLE,','QIAN,','RONNEBERGER,','SIMÉONI,')
    refs += [p.strip() for p in oldrefs.split('\n\n') if p.strip().startswith(prefixes)]
    refs.append('META AI. SAM 3. Código oficial, revisão f1647e8d0c1d280991f4d1b7d974c2704537fe66; checkpoint SAM3.1, revisão daa63191845a41281374e725f4c9e51c7a824460. 2026. Disponível em: https://github.com/facebookresearch/sam3. Acesso em: 5 nov. 2026.')
    return sorted(refs,key=lambda x:x.casefold())


def reference_emphasis():
    source=(ROOT/'artigo/revisao_bibliografica_2026-11-05/referencias.bib').read_text(encoding='utf-8')
    terms=[]
    for _,_,body in re.findall(r'@(\w+)\{([^,]+),\s*(.*?)\n\}',source,re.S):
        fields={k:re.sub(r'[{}]','',v).strip() for k,v in re.findall(r'^\s*(\w+)\s*=\s*\{(.*)\},?\s*$',body,re.M)}
        terms.append(fields.get('journal') or fields.get('booktitle') or fields.get('title',''))
    terms += ['Notre Dame Open-Source Iris Recognition','IEEE/CVF Conference on Computer Vision and Pattern Recognition',
              'IEEE Conference on Computer Vision and Pattern Recognition','SLP-VLD','DINOv3','SAM 3',
              'Advances in Neural Information Processing Systems','Medical Image Computing and Computer-Assisted Intervention']
    return sorted({t for t in terms if t},key=len,reverse=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--continuous',action='store_true',default=True,help='Fluxo contínuo do corpo; os marcadores não forçam páginas.')
    parser.add_argument('--source-file',type=Path,default=ROOT/'artigo/ARTIGO_CONSOLIDADO_2026-11-05.md')
    parser.add_argument('--output-name',default='ARTIGO_AREA_IRIS_UNISATC_2026-11-05.docx')
    args=parser.parse_args()
    out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
    evidence=json.loads((ROOT/'artigo/verificacao_2026-10-27/template-style-evidence.json').read_text())
    reference=Path(evidence['input']);raw=reference.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='e8d9f33821f15443b4c27d3289a4d65cc110385dcbdca790a3766030257ac2eb'
    original=zipfile.ZipFile(io.BytesIO(raw));doc=Document(reference)
    first=copy.deepcopy(doc.paragraphs[0]._p)
    authors=[copy.deepcopy(doc.paragraphs[i]._p) for i in (3,4)]
    section=copy.deepcopy(doc._element.body.sectPr)
    for child in list(doc._element.body):doc._element.body.remove(child)
    doc._element.body.append(first);doc._element.body.append(section)
    pending_break=False;pending_bookmark=None
    def fmt(run,size=12,bold=None):
        run.font.name='Arial';run.font.size=Pt(size);run.font.color.rgb=RGBColor(0,0,0)
        if bold is not None:run.bold=bold
        return run
    def p(text='',style='1Texto',size=12,align=None,keep=False):
        nonlocal pending_break,pending_bookmark
        par=doc.add_paragraph(style=style)
        fmt(par.add_run(text),size)
        if align is not None:par.alignment=align
        par.paragraph_format.keep_with_next=keep
        par.paragraph_format.widow_control=True
        if style=='1Texto':
            par.paragraph_format.first_line_indent=Cm(2);par.paragraph_format.line_spacing=1.5
            par.paragraph_format.space_after=Pt(0)
        if pending_break:par.paragraph_format.page_break_before=True;pending_break=False
        if pending_bookmark:
            start=OxmlElement('w:bookmarkStart');start.set(qn('w:id'),str(100+pending_bookmark));start.set(qn('w:name'),f'PFC_PAGINA_{pending_bookmark:02}')
            end=OxmlElement('w:bookmarkEnd');end.set(qn('w:id'),str(100+pending_bookmark))
            par._p.insert(1 if par._p.pPr is not None else 0,start);par._p.append(end);pending_bookmark=None
        return par
    lines=args.source_file.read_text(encoding='utf-8').splitlines()
    page_words={};current_page=0;i=0;author_index=0
    while i<len(lines):
        s=lines[i].strip();i+=1
        if not s:continue
        marker=re.fullmatch(r'<!-- pagina:(\d+) -->',s)
        if marker:
            current_page=int(marker[1]);page_words[current_page]=0
            pending_break=current_page>1 and not args.continuous;pending_bookmark=current_page;continue
        page_words[current_page]+=len(s.split())
        if s.startswith('# '):p(s[2:],'Title',align=WD_ALIGN_PARAGRAPH.CENTER);continue
        if s in ('Lucas Cardoso Rodrigues','Rodrigo Ramos Silva'):
            elem=authors[author_index];author_index+=1
            anchor=copy.deepcopy(next(elem.iter(W+'footnoteReference')))
            for child in list(elem):
                if child.tag!=W+'pPr':elem.remove(child)
            doc._element.body.insert(len(doc._element.body)-1,elem)
            from docx.text.paragraph import Paragraph
            par=Paragraph(elem,doc._body);fmt(par.add_run(s),12,True)
            r=par.add_run();r.font.superscript=True;r._r.append(anchor);continue
        if s.startswith('**Resumo:**') or s.startswith('**Palavras-chave:**'):
            abstract=s.startswith('**Resumo:');label='Resumo: ' if abstract else 'Palavras-chave: '
            par=p('', 'Resumo' if abstract else 'Textodoresumo');fmt(par.add_run(label),12,True)
            fmt(par.add_run(s.split('**',2)[2].strip()),12);continue
        if s.startswith('#'):
            depth=len(s)-len(s.lstrip('#'));text=re.sub(r'^\d+(?:\.\d+)*\s+','',s.lstrip('# ').strip())
            p(text,{2:'Heading 1',3:'Heading 2',4:'Heading 3'}[depth],keep=True);continue
        if s.startswith('|'):
            rows=[s]
            while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i].strip());i+=1
            matrix=[[c.strip() for c in row.strip('|').split('|')] for row in rows if not re.fullmatch(r'[|:\-\s]+',row)]
            n=len(matrix[0]);widths={3:[4.0,5.8,6.2],4:[5.7,3.2,3.2,3.9],5:[5.4,2.4,2.6,2.8,2.8],6:[1.5,1.7,3.2,3.2,3.2,3.2]}[n]
            table=doc.add_table(rows=0,cols=n);table.autofit=False
            for col,w in zip(table.columns,widths):col.width=Cm(w)
            borders=OxmlElement('w:tblBorders')
            for edge in ('top','bottom'):
                el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'6');el.set(qn('w:color'),'808080');borders.append(el)
            table._tbl.tblPr.append(borders)
            for j,row in enumerate(matrix):
                cells=table.add_row().cells;props=table.rows[-1]._tr.get_or_add_trPr();props.append(OxmlElement('w:cantSplit'))
                if j==0:props.append(OxmlElement('w:tblHeader'))
                for k,(cell,text) in enumerate(zip(cells,row)):
                    cell.width=Cm(widths[k]);par=cell.paragraphs[0];par.style=doc.styles['Normal']
                    par.paragraph_format.first_line_indent=Cm(0);par.paragraph_format.line_spacing=1
                    par.paragraph_format.space_before=Pt(3);par.paragraph_format.space_after=Pt(3)
                    if matrix[0][:2] in (['Perda','Área'],['Condição','Dice médio']):
                        par.paragraph_format.keep_with_next=j<len(matrix)-1
                    par.alignment=WD_ALIGN_PARAGRAPH.LEFT if k==0 else WD_ALIGN_PARAGRAPH.CENTER
                    fmt(par.add_run(text),10,j==0)
            continue
        if s.startswith('!['):
            alt,path=re.match(r'!\[(.*?)\]\((.*?)\)',s).groups()
            par=p('','Normal',align=WD_ALIGN_PARAGRAPH.CENTER,keep=True)
            par.paragraph_format.space_before=Pt(5);par.paragraph_format.space_after=Pt(5)
            shape=par.add_run().add_picture(str(ROOT/'artigo'/path),width=Cm(16))
            shape._inline.docPr.set('descr',alt);continue
        if s.startswith(('Figura ','Tabela ')):p(s,'Normal',align=WD_ALIGN_PARAGRAPH.CENTER,keep=True);continue
        if s.startswith('Fonte:'):
            par=p(s,'Normal',10);par.paragraph_format.space_after=Pt(8);continue
        if s.startswith('Eq. '):
            par=p(s,'Normal',align=WD_ALIGN_PARAGRAPH.CENTER)
            par.paragraph_format.space_before=Pt(7);par.paragraph_format.space_after=Pt(7);continue
        p(s)
    refs=bibliography()
    bold_terms=reference_emphasis()
    bold_pattern='('+'|'.join(re.escape(t) for t in bold_terms)+')'
    pending_break=True;pending_bookmark=31
    p('REFERÊNCIAS','Ttulononumerado',keep=True)
    for text in refs:
        par=p('','4Referncias');par.paragraph_format.first_line_indent=Cm(0)
        for token in re.split(r'(https?://\S+)',text):
            if not token.startswith(('http://','https://')):
                for fragment in re.split(bold_pattern,token):
                    if fragment:fmt(par.add_run(fragment),bold=fragment in bold_terms)
                continue
            url=token.rstrip('.,;')
            link=OxmlElement('w:hyperlink');link.set(qn('r:id'),doc.part.relate_to(url,RT.HYPERLINK,is_external=True))
            run=OxmlElement('w:r');props=OxmlElement('w:rPr')
            font=OxmlElement('w:rFonts');font.set(qn('w:ascii'),'Arial');font.set(qn('w:hAnsi'),'Arial');props.append(font)
            size=OxmlElement('w:sz');size.set(qn('w:val'),'24');props.append(size)
            run.append(props);node=OxmlElement('w:t');node.text=url;run.append(node);link.append(run);par._p.append(link)
            if token[len(url):]:fmt(par.add_run(token[len(url):]))
        par.paragraph_format.line_spacing=1;par.paragraph_format.space_after=Pt(24)
        par.paragraph_format.keep_together=True;par.alignment=WD_ALIGN_PARAGRAPH.LEFT
    doc.core_properties.title=TITLE;doc.core_properties.author='Lucas Cardoso Rodrigues; Rodrigo Ramos Silva'
    doc.core_properties.subject='Area visivel da iris, identificacao e limites da transferencia clinica'
    doc.core_properties.language='pt-BR'
    memory=io.BytesIO();doc.save(memory);generated=zipfile.ZipFile(memory)
    changed={'word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml','docProps/core.xml','word/footnotes.xml','word/settings.xml'}
    foot=etree.fromstring(original.read('word/footnotes.xml'))
    for ident,text in [('1','Graduando em Engenharia de Computação. E-mail: lucaazartys@gmail.com'),('2','Professor do Centro Universitário UniSATC. E-mail: rodrigo.1974@satc.edu.br')]:
        note=next(e for e in foot if e.get(W+'id')==ident);par=note.find(W+'p')
        for child in list(par):
            if child.tag!=W+'pPr':par.remove(child)
        run=etree.SubElement(par,W+'r');props=etree.SubElement(run,W+'rPr')
        etree.SubElement(props,W+'rStyle').set(W+'val','Refdenotaderodap')
        etree.SubElement(props,W+'vertAlign').set(W+'val','baseline')
        etree.SubElement(run,W+'footnoteRef')
        run=etree.SubElement(par,W+'r');props=etree.SubElement(run,W+'rPr')
        font=etree.SubElement(props,W+'rFonts');font.set(W+'ascii','Arial');font.set(W+'hAnsi','Arial')
        etree.SubElement(props,W+'sz').set(W+'val','20')
        node=etree.SubElement(run,W+'t');node.set('{http://www.w3.org/XML/1998/namespace}space','preserve');node.text=' '+text
        for extra in note.findall(W+'p')[1:]:note.remove(extra)
    settings=etree.fromstring(original.read('word/settings.xml'))
    for el in settings.findall(W+'updateFields'):settings.remove(el)
    etree.SubElement(settings,W+'updateFields').set(W+'val','true')
    final=out/args.output_name
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
    preserved=[name for name in original.namelist() if name not in changed]
    assert all(original.read(name)==finalzip.read(name) for name in preserved)
    assert etree.tostring(section)==etree.tostring(etree.fromstring(finalzip.read('word/document.xml')).find(W+'body').find(W+'sectPr'))
    (out/'verificacao_pacote.json').write_text(json.dumps(dict(template_sha256=hashlib.sha256(raw).hexdigest(),
        output_sha256=hashlib.sha256(final.read_bytes()).hexdigest(),preserved_parts=preserved,changed_parts=sorted(changed),
        page_markers=30,words_per_planned_page=page_words,references=len(refs),images=5,
        no_template_modification=True,source_file=str(args.source_file),source_sha256=hashlib.sha256(args.source_file.read_bytes()).hexdigest()),indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'REFERENCIAS_FORMATADAS.md').write_text('\n\n'.join(refs),encoding='utf-8')
    print(json.dumps(dict(output=str(final),words_per_page=page_words,references=len(refs)),ensure_ascii=False))


if __name__=='__main__':main()
