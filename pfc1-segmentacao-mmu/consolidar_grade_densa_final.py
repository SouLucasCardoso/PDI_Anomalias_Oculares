"""Fechamento verificável do artigo, recortes e comparação em todos os inteiros."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
fmt=lambda x,n=2:f'{100*x:.{n}f}'.replace('.',',')
support=lambda x:f'{x}%' if x is not None else 'nenhum nível aprovado'


def main():
    files={
        'analysis':'outputs/grade_densa_analise_2026-11-08/AUDITORIA_FINAL.json',
        'reference':'outputs/grade_densa_1a31_2026-11-08/CONCLUIDO.json',
        'candidate':'outputs/grade_densa_contorno_misto_2026-11-08/CONCLUIDO.json',
        'candidate_results':'outputs/grade_densa_contorno_misto_2026-11-08/resultados.json',
        'selection':'outputs/contorno_componentes_misto_2026-11-08/CANDIDATO_IDENTIDADE.json',
        'components':'outputs/contorno_fragmentos_entrega_2026-11-08/CONCLUIDO.json',
        'sam_prompts':'outputs/sam31_prompts_exteriores_2026-11-08/CONCLUIDO.json',
        'matte':'outputs/sam31_matte_subpixel_2026-11-08/CONCLUIDO.json',
        'article':'artigo/verificacao_2026-11-08/VERIFICACAO_FINAL.json',
        'versions':'outputs/tecnologias_grade_densa_2026-11-08.json'}
    data={k:json.loads((ROOT/v).read_text(encoding='utf-8-sig')) for k,v in files.items()}
    audit=data['analysis'];reference=data['reference'];candidate=data['candidate'];records=data['candidate_results'];article=data['article']
    assert audit['status']=='verified' and audit['conditions']==reference['conditions']==candidate['conditions']==len(records)==63
    assert article['status']=='verified' and article['content_pages']==30 and article['reference_pages']==4
    assert article['scientific_conditions_recounted_and_replayed']==63 and sha(article['docx'])==article['docx_sha256']
    assert candidate['comparison_gate_passed']==audit['comparison_gate_passed']
    gate=candidate['comparison_gate_passed'];worse=sum(r['candidate']['counts']['false_accepts']>r['baseline']['counts']['false_accepts'] for r in records)
    mean_base=sum(r['baseline']['counts']['joint'] for r in records)/(63*486)
    mean_candidate=sum(r['candidate']['counts']['joint'] for r in records)/(63*486)
    validation_joint=data['selection']['validation']['original']['joint_success']
    lines=['# Fechamento dos testes de 1% a 31% e do recorte','',
        f'**Concluído: 63 condições da referência e 63 do candidato**, com auditoria independente das contagens. A regra relativa completa de comparação do candidato foi {"aprovada" if gate else "reprovada"}. Nenhum modelo do aplicativo foi substituído automaticamente.','',
        'A grade contém o controle e cada percentual inteiro de 1% a 31%, nas posições superior e inferior. As 13 condições anteriores foram reutilizadas após conferência; 50 foram calculadas nesta rodada. Em cada condição foram preservadas as mesmas 486 consultas e 7.290 comparações impostoras, inclusive falhas. As repetições das mesmas fotografias não constituem pessoas ou observações independentes adicionais.','',
        '## Comparação com o contorno selecionado','',
        'O candidato mistura, em proporção fixa de 50%, o escore polar original e o obtido com o contorno contínuo sem pequenos fragmentos. Os outros oito componentes, pesos de fusão, calibração e limiar permanecem fixos. A escolha ocorreu na validação, antes da comparação densa do candidato.','',
        '| Perda e posição | Versão | Rank-1 | TAR | FMR | Correto e aceito |','|---|---|---:|---:|---:|---:|']
    for condition,level,title in (('original',0,'Sem perda'),('oclusao_superior',1,'1% superior'),('oclusao_inferior',1,'1% inferior'),
            ('oclusao_superior',10,'10% superior'),('oclusao_inferior',10,'10% inferior'),('oclusao_superior',31,'31% superior'),('oclusao_inferior',31,'31% inferior')):
        r=next(r for r in records if r['condition']==condition and r['level']==level)
        for name,label in (('baseline','Referência'),('candidate','Candidato')):
            m=r[name]['metrics'];lines.append(f"| {title} | {label} | {fmt(m['rank1'])}% | {fmt(m['tar'])}% | {fmt(m['far'],3)}% | {fmt(m['joint_success'])}% |")
    lines+=['',f'A média do evento correto e aceito nas 63 condições foi de {fmt(mean_base)}% na referência e {fmt(mean_candidate)}% no candidato. A FMR aumentou em {worse} condições. A regra exigia preservar Rank-1 e TAR limpos, FMR limpa de até 1%, melhorar a média conjunta e não elevar a FMR em nenhum cenário. A aprovação relativa e o atendimento absoluto dos alvos 90/90/1 são questões diferentes.','',
        '[Tabela completa de todos os níveis](outputs/grade_densa_analise_2026-11-08/tabela_completa.csv). [Curva, auditoria e fronteiras condicionadas](outputs/grade_densa_analise_2026-11-08/RESULTADO_PARA_DEFESA.md).','',
        f'Embora o evento conjunto tenha alcançado 90,12% no teste limpo, na validação limpa ficou em {fmt(validation_joint)}%. Esse resultado não representa aprovação de prontidão clínica nem garantia de desempenho populacional.','',
        '## O que mudou no recorte','',
        'O filtro remove somente componentes menores que 0,5% do maior componente, sem acrescentar pixels ou fechar oclusões. Nas 78 imagens em três situações, a variação de Dice foi inferior a 0,01 ponto percentual: uma melhora pequena, que não foi confundida com grande ganho anatômico ou de reconhecimento. A filtragem guiada pelas bordas e as combinações de resoluções não superaram o controle nas três situações.','',
        'O novo ensaio SAM3.1 com até 24 pontos positivos e negativos exteriores alcançou Dice de 84,19%, incluindo 40 retornos à máscara inicial entre 78 imagens. É um procedimento híbrido; o ganho não é atribuído apenas ao SAM. Ficou acima do refino anterior de 76,70%, mas abaixo dos 88,46% do controle contínuo, que foi preservado.','',
        'Nos seis exemplos clínicos fixos, a cobertura subpixel suaviza a apresentação da borda mantendo RGB e máscaras binárias idênticos aos anteriores. Cinco recortes contêm suporte; o caso sem localização permanece indisponível e requer revisão. Nenhuma textura foi gerada ou retocada, e as imagens não receberam nova validação anatômica clínica.','',
        '[Recortes em resolução nativa, comparações e comando de exportação](RECORTES_NATIVOS_2026-11-08.md).','',
        '## Como interpretar o percentual','']
    for name,description in (('reference','Referência'),('candidate','Candidato')):
        for direction,label in (('oclusao_superior','superior'),('oclusao_inferior','inferior')):
            values=audit['minimum'][name][direction]
            lines.append(f"- {description}, {label}: suporte nominal mínimo no prefixo com critérios marginais = {support(values['marginal']['minimum_nominal_support_on_registered_prefix'])}; incluindo correto e aceito≥90% = {support(values['joint90']['minimum_nominal_support_on_registered_prefix'])}.")
    lines+=['','Esses percentuais são condicionados à grade, ao sistema, à galeria e ao suporte originalmente anotado. Não medem o anel anatômico normativo ou a extensão de doença. A posição da perda importa; não foi demonstrado mínimo universal nem efeito causal de patologias. Os intervalos por pessoa permanecem descritivos, com dados reutilizados no desenvolvimento e galeria fixa.','',
        '## Entrega','',
        '- [Artigo atualizado](artigo/ARTIGO_AREA_IRIS_UNISATC_2026-11-08.docx): 30 páginas de conteúdo e 4 de referências, 31 referências, 12 tabelas e 5 figuras.',
        '- [Verificação do documento](artigo/verificacao_2026-11-08/VERIFICACAO_FINAL.json).',
        '- [Grade e resultados completos](outputs/grade_densa_analise_2026-11-08/RESULTADO_PARA_DEFESA.md).',
        '- [Protocolo do candidato congelado](outputs/grade_densa_contorno_misto_2026-11-08/protocolo.json).','']
    report=ROOT/'RESULTADO_GRADE_DENSA_2026-11-08.md';report.write_text('\n'.join(lines),encoding='utf-8')
    final={'status':'concluido','utc':datetime.now(timezone.utc).isoformat(),'reference_conditions':63,'candidate_conditions':63,
        'comparison_gate_passed':gate,'candidate_fmr_worse_conditions':worse,'recognizer_replaced':False,
        'article_docx_sha256':article['docx_sha256'],'report_sha256':sha(report),
        'inputs_sha256':{v:sha(ROOT/v) for v in files.values()},'compiler_sha256':sha(__file__)}
    (ROOT/'outputs/FECHAMENTO_GRADE_DENSA_2026-11-08.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final))


if __name__=='__main__':main()
