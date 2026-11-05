"""Organiza metadados publicos ja conferidos; nao acessa dados biometricos."""
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent

# Notas de leitura, nao trechos copiados dos artigos.
NOTES = {
    'nist7820': ('Qualidade', 'Seções de área utilizável e síntese do relatório técnico',
        'Relaciona qualidade e desempenho em múltiplos comparadores; ajuda a separar utilidade da imagem de decisão biométrica.',
        'Resultados dependem do corpus, sensor e comparador; não estabelece mínimo anatômico universal.'),
    'nist7853': ('Qualidade', 'Resumo institucional e exemplos de falhas',
        'Examina oclusão, desfoque, pose e outras causas de falha de reconhecimento.',
        'Falha operacional pode decorrer de localização ou captura, e não apenas de área insuficiente.'),
    'nist8013': ('Aquisição', 'Seções pertinentes e figuras do relatório técnico',
        'Orienta captura de íris e mitigação de pálpebras, reflexos e aquisição inadequada.',
        'Guia de aquisição; não é ensaio clínico sobre percentual por patologia.'),
    'nist8207': ('Avaliação', 'Escopo e resumo institucional',
        'Avalia algoritmos em verificação 1:1 e identificação 1:N sobre dados operacionais.',
        'Taxas de comparação e taxas por busca são medidas diferentes; a galeria importa.'),
    'du2005': ('Íris parcial', 'Texto integral do artigo de conferência',
        'Compara recortes laterais e anéis internos/externos; o resultado depende da região e do rank considerado.',
        'Os exemplos de 40%/65% são rank-10; dois modelos usam proporção radial e a máscara recebe informação da imagem completa.'),
    'daugman2004': ('Fundamentos', 'Resumo e seções pertinentes do PDF público do autor',
        'Expõe codificação, mascaramento e decisão estatística em reconhecimento de íris.',
        'Área em pixels não equivale diretamente a informação discriminante ou risco de falsa correspondência.'),
    'daugman2007': ('Fundamentos', 'Resumo e seções pertinentes do PDF público do autor',
        'Aborda contornos flexíveis, pose, exclusão de cílios e normalização de escores pela quantidade de dados e escala da busca.',
        'A decisão depende do algoritmo e da informação disponível, não de uma porcentagem isolada.'),
    'hollingsworth2009bits': ('Informação regional', 'Resumo original e PDF público dos autores',
        'Documenta bits mais e menos estáveis; as faixas médias podem ser mais consistentes que as internas.',
        'Não é apropriado assumir que toda região com a mesma área contém a mesma informação.'),
    'hollingsworth2009dilation': ('Dilatação', 'Resumo e trechos do editor',
        'Mostra efeito tanto do grau de dilatação quanto de sua diferença entre cadastro e consulta.',
        'Dilatação altera geometria e escores, mesmo quando não é uma oclusão por tecido externo.'),
    'hofbauer2016': ('Segmentação e reconhecimento', 'Texto integral público, seções pertinentes',
        'Mostra que acurácia de segmentação isolada não prevê confiavelmente o desempenho da cadeia biométrica.',
        'Extração parcial consistente pode funcionar sob centro de normalização estável; não fornece percentual universal.'),
    'hofbauer2019': ('Segmentação e reconhecimento', 'Resumo e conclusão do editor; versão pública dos autores localizada',
        'Integra máscaras CNN à parametrização e ao reconhecimento; o benefício varia com a qualidade da base.',
        'Máscara superior em métrica de pixels não garante ganho em todos os conjuntos ou parametrizações.'),
    'pessaud2026': ('Área visível e qualidade', 'PDF publicado: métodos, resultados e limitações; inspeção visual das páginas 4, 5 e 14',
        'Estuda área visível em pixels, dilatação e oclusão com OpenIRIS em NIR; é o antecedente mais próximo localizado.',
        'Sem limite percentual universal; ausência de alterações irianas/corneanas relevantes no grupo. Não duplicar com o preprint de 2025.'),
    'nguyen2024': ('Revisão', 'Resumo, seções e recursos da revisão publicada',
        'Reúne mais de 200 trabalhos e recursos sobre segmentação, reconhecimento e robustez com aprendizado profundo.',
        'Revisão secundária; útil para contextualizar SAM/CNN, não como ensaio de mínimo de área.'),
    'aslam2009': ('Patologias', 'Resumo original e PDF público da versão publicada',
        'Coorte prospectiva antes/depois do tratamento; encontra resiliência em várias condições e falhas em uveíte anterior.',
        '54 pacientes; não demonstra o mesmo efeito para todas as doenças ou algoritmos.'),
    'roizenblatt2004': ('Cirurgia', 'Texto integral público do editor, métodos e conclusão',
        'Investiga alterações e falhas após cirurgia de catarata em 55 pacientes.',
        'Equipamento e prática cirúrgica específicos; não extrapolar a todas as cirurgias ou sistemas modernos.'),
    'dhir2010': ('Cirurgia e dilatação', 'Resumo original do editor',
        'Em 15 participantes, diferencia o efeito da dilatação daquele da cirurgia no sistema estudado.',
        'Amostra pequena; o resultado favorável após cirurgia não é garantia populacional.'),
    'trokielewicz2015database': ('Base clínica', 'Resumo original dos autores e metadados do evento',
        'Apresenta coleção de 91 olhos e comparação por tipo de comprometimento ocular.',
        'Antecede a expansão da mesma linha de pesquisa; não tratar como população totalmente independente das versões ampliadas.'),
    'trokielewicz2015assessment': ('Patologias', 'Resumo original dos autores e metadados do evento',
        'Avalia 2.996 imagens de 230 olhos, incluindo alterações geométricas, estruturais e obstruções.',
        'Corpus e autoria se sobrepõem à versão de periódico; não contar como replicação clínica independente.'),
    'trokielewicz2016': ('Patologias', 'Resumo e trechos do editor; versão dos autores identificada pelo DOI',
        'Com quatro reconhecedores, destaca falhas de segmentação e menor similaridade genuína em olhos doentes.',
        '230 olhos, 184 afetados por mais de 20 condições. Citar pelo ano do fascículo: 2017, não pelo depósito arXiv de 2018.'),
    'frasca2024': ('Coloboma', 'Resumo, introdução e conclusão disponibilizados pelo editor',
        'Adapta a localização para pupilas deformadas, usando aproximação elíptica no caso de coloboma.',
        'A melhoria de 32% destacada é de erro médio de segmentação; não convertê-la em 32% de identificação.'),
    'nigam2019': ('Cirurgia', 'PDF público: resumo, resultados e métodos pertinentes',
        'Analisa captura, segmentação e reconhecimento antes/depois de cirurgia, com múltiplos sensores.',
        'Desempenho depende de momento pós-operatório, reflexos e captura; não sustenta porcentagem clínica universal.'),
    'seyeddain2014': ('Cirurgia e dilatação', 'Resumo original indexado no PubMed e metadados do editor',
        'Relata falhas pós-operatórias e após dilatação, embora a maioria dos olhos continue reconhecível.',
        '173 olhos na cirurgia e 184 na dilatação; sem ponto mínimo de área estimado.'),
    'kumar2025': ('Cirurgia; leitura crítica', 'Texto integral público no PMC e resumo PubMed',
        'Investiga cirurgia sem complicações em 100 participantes sob aquisição favorável.',
        'Relata 95/100 e também 99% no resumo, além de linguagem de erro zero. Exclui anormalidades e escolhe a melhor tentativa; não usar como estimativa única de acurácia.'),
}


def normalize(value):
    return html.unescape(value).replace('\u2010', '-').replace('\u2011', '-').replace('\u2013', '-').replace('\u2019', "'")


def year_from(row):
    for field in ('published-print', 'issued', 'published'):
        parts = (row.get(field) or {}).get('date-parts', [[None]])
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0])
    return 2005 if row['key'] == 'du2005' else None


def author_bib(author):
    return normalize(author.get('family', '') + ', ' + author.get('given', '')).strip(', ')


def main():
    data = json.loads((HERE / 'metadados_doi.json').read_text(encoding='utf-8'))
    rows = []
    for original in data['records']:
        if 'error' in original:
            raise ValueError(original)
        row = dict(original)
        key = row['key']
        category, access, finding, limitation = NOTES[key]
        row['citation_key'] = 'trokielewicz2017' if key == 'trokielewicz2016' else key
        row['year'] = {'dhir2010': 2010, 'seyeddain2014': 2014, 'trokielewicz2016': 2017}.get(key, year_from(row))
        if key == 'kumar2025':
            row['author'] = [dict(given=g, family=f) for g, f in [('Sonali Vinay', 'Kumar'), ('Vinay', 'Kumar'), ('Natasha Vinay', 'Kumar'), ('Alok', 'Sati'), ('Sanjay Kumar', 'Mishra')]]
            row['page'] = '184-189'
            row['container-title'] = ['Romanian Journal of Ophthalmology']
            row['metadata_correction_source'] = 'https://pubmed.ncbi.nlm.nih.gov/40698095/'
        if key in ('nigam2019', 'roizenblatt2004'):
            row['article-number'] = {'nigam2019': '11139', 'roizenblatt2004': '2'}[key]
        full_reports = {
            'nist7820': ('IREX II - IQCE: Iris Quality Calibration and Evaluation - Performance of Iris Image Quality Assessment Algorithms', '7820'),
            'nist7853': ('IREX III Supplement 1: Failure Analysis', '7853'),
            'nist8013': ('IREX V: Guidance for Iris Image Collection', '8013'),
            'nist8207': ('IREX IX Part One: Performance of Iris Recognition Algorithms', '8207'),
        }
        row['title'] = normalize(row['title'][0])
        row['authors_display'] = '; '.join(author_bib(a) for a in row['author'])
        if key in full_reports:
            row['title'], row['report_number'] = full_reports[key]
            row['bib_type'] = 'techreport'
        else:
            row['bib_type'] = 'inproceedings' if row['type'] == 'proceedings-article' else 'article'
        row['category'], row['access_checked'] = category, access
        row['finding'], row['limitation'] = finding, limitation
        row['supports_universal_minimum'] = False
        row['doi_url'] = 'https://doi.org/' + row['DOI']
        rows.append(row)
    standards = [
        ('iso29794_6_2015', 2015, 'ISO/IEC 29794-6:2015', 'Information technology - Biometric sample quality - Part 6: Iris image data', 'https://www.iso.org/standard/54066.html',
         'Catálogo oficial e prévia pública; cláusula 6.2.1.4 conferida', 'Limiar de qualidade USABLE_IRIS_AREA >=70; não é garantia de reconhecimento individual.', 'Prévia de 12 das 29 páginas; observações geométricas inatas não equivalem a validação clínica por diagnóstico.'),
        ('iso19795_1_2021', 2021, 'ISO/IEC 19795-1:2021', 'Information technology - Biometric performance testing and reporting - Part 1: Principles and framework', 'https://www.iso.org/standard/73515.html',
         'Catálogo oficial e escopo; versão corrigida 2024-09', 'Fundamenta avaliação de desempenho e explicitação de protocolos.', 'Não confundir conformidade de imagem com desempenho de verificação/identificação; revisão DIS não é edição publicada.'),
        ('iso39794_6_2021', 2021, 'ISO/IEC 39794-6:2021', 'Information technology - Extensible biometric data interchange formats - Part 6: Iris image data', 'https://www.iso.org/standard/78017.html',
         'Catálogo oficial e escopo; confirmação 2026', 'Define formatos de intercâmbio, aquisição e testes de conformidade de dados de íris.', 'Uma norma de formato de dados não é demonstração de mínimo biológico para reconhecer alguém.'),
    ]
    for key, year, number, title, url, access, finding, limitation in standards:
        rows.append({'citation_key': key, 'year': year, 'title': title, 'number': number,
                     'authors_display': 'ISO/IEC', 'bib_type': 'manual', 'category': 'Normas',
                     'access_checked': access, 'finding': finding, 'limitation': limitation,
                     'doi_url': url, 'supports_universal_minimum': False})
    assert len(rows) == 26
    assert len({r['citation_key'] for r in rows}) == len(rows)
    assert len({r['DOI'].lower() for r in rows if r.get('DOI')}) == 23
    order = ['iso29794_6_2015', 'iso19795_1_2021', 'iso39794_6_2021', *[r['citation_key'] for r in rows if r['bib_type'] != 'manual']]
    rows.sort(key=lambda r: order.index(r['citation_key']))
    (HERE / 'MATRIZ_EVIDENCIAS.json').write_text(json.dumps({'accessed_date': '2026-11-05', 'review_type': 'Targeted narrative review; not systematic and not a meta-analysis', 'source_count': len(rows), 'articles_and_conference_papers': 19, 'technical_reports': 4, 'standards': 3, 'records': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    bib = []
    md = ['# Referências comentadas para o artigo', '', 'Consulta: 05/11/2026. São 26 referências: 19 artigos/conferências, quatro relatórios NIST e três normas. Não são 26 populações clínicas independentes. Autores/DOIs foram conferidos; os níveis de acesso abaixo distinguem texto, resumo e catálogo.', '']
    for index, row in enumerate(rows, 1):
        key = row['citation_key']
        fields = {'title': '{' + row['title'] + '}', 'year': str(row['year']), 'url': row['doi_url'], 'urldate': '2026-11-05'}
        if row['bib_type'] == 'manual':
            fields.update(author='{ISO/IEC}', organization='International Organization for Standardization', number=row['number'])
        else:
            fields['author'] = ' and '.join(author_bib(a) for a in row['author'])
            fields['doi'] = row['DOI']
            if row['bib_type'] == 'techreport':
                fields.update(institution='National Institute of Standards and Technology', number='NISTIR ' + row['report_number'])
            else:
                fields['booktitle' if row['bib_type'] == 'inproceedings' else 'journal'] = normalize((row.get('container-title') or [''])[0])
                for original, field in (('volume', 'volume'), ('issue', 'number'), ('page', 'pages')):
                    if row.get(original):
                        fields[field] = str(row[original]).replace('-', '--') if field == 'pages' else str(row[original])
                if row.get('article-number'):
                    fields['eid'] = str(row['article-number'])
        bib.append('@' + row['bib_type'] + '{' + key + ',\n' + ',\n'.join('  ' + k + ' = {' + normalize(v).replace('&', '\\&') + '}' for k, v in fields.items()) + '\n}\n')
        venue = 'ISO/IEC' if row['bib_type'] == 'manual' else ('NISTIR ' + row['report_number'] if row['bib_type'] == 'techreport' else normalize((row.get('container-title') or [''])[0]))
        citation = f"{row['authors_display']}. **{row['title']}**. {venue}, {row['year']}."
        if row.get('volume'): citation += f" v. {row['volume']}."
        if row.get('page'): citation += f" p. {row['page']}."
        md += [f'## {index:02}. {key}', '', citation + f" [Fonte/DOI]({row['doi_url']}).", '',
               f"**Uso no artigo:** {row['finding']}", '', f"**Limitação:** {row['limitation']}", '', f"**Conferência:** {row['access_checked']}.", '']
    (HERE / 'referencias.bib').write_text('\n'.join(bib), encoding='utf-8')
    (HERE / 'REFERENCIAS_COMENTADAS.md').write_text('\n'.join(md), encoding='utf-8')
    text = (HERE / 'referencias.bib').read_text(encoding='utf-8')
    assert len(re.findall(r'^@\w+\{', text, re.M)) == 26
    assert text.count('{') == text.count('}')
    print('Generated 26 references, 23 unique DOIs, 3 standards; BibTeX keys and braces checked.')


if __name__ == '__main__':
    main()
