"""Integra apenas os dados concluidos e auditados, preservando a fonte anterior."""
from pathlib import Path
import argparse,json,re
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-source',type=Path,required=True);a=p.parse_args()
    run=ROOT/'outputs/ensaio_oclusoes_2026-11-08'
    records=json.loads((run/'CONCLUIDO.json').read_text())['records']
    audit=json.loads((run/'analise_final/AUDITORIA_FINAL.json').read_text())
    assert len(audit['counts_recomputed'])==13
    records=[r for r in records if r['model']=='historico']
    get=lambda side,loss:next(r for r in records if r['condition']==('original' if loss==0 else side) and r['loss_percent']==loss)
    percent=lambda x: f'{100*x:.2f}'.replace('.',',')
    number=lambda x:f'{x:.2f}'.replace('.',',')
    text=(ROOT/'artigo/ARTIGO_CONSOLIDADO_2026-11-05.md').read_text(encoding='utf-8')
    original=get('original',0)['rates'];s30=get('oclusao_superior',30)['rates'];s31=get('oclusao_superior',31)['rates']
    i30=get('oclusao_inferior',30)['rates'];i31=get('oclusao_inferior',31)['rates']
    abstract=f'''**Resumo:** Este estudo avaliou a influência da quantidade e da posição da área visível de íris na identificação ocular sob oclusões controladas. Utilizou-se o UBIPr segmentado, com partições por pessoa, extração automática e fusão de nove representações. O protocolo entre sessões manteve uma fotografia por consulta, lateralidade informada e dezesseis candidatos do mesmo lado. A grade completa incluiu perdas de 0%, 1%, 5%, 10%, 20%, 30% e 31%, nas orientações superior e inferior, com cadastro e limiar fixos. Nas 486 consultas da execução final, o controle sem oclusão obteve Rank-1 de {percent(original['rank1'])}%, aceitação genuína de {percent(original['tar'])}% e falsa correspondência de {percent(original['far'])}%. Com 30% de oclusão, o Rank-1 foi de {percent(s30['rank1'])}% na orientação superior e {percent(i30['rank1'])}% na inferior; com 31%, foi de {percent(s31['rank1'])}% e {percent(i31['rank1'])}%, respectivamente. A tentativa de reajuste da fusão não superou o controle na validação fora das dobras e preservou os pesos históricos. Ensaios com SAM3.1 e imagens clínicas complementaram a investigação das falhas de transferência. A revisão da literatura distinguiu o requisito normativo de área utilizável de 70% de uma garantia universal de identificação. Concluiu-se que a área e a localização da perda influenciam o sistema avaliado, sem estabelecer mínimo anatômico universal ou equivalência entre oclusão e patologia. Os percentuais experimentais usam a região originalmente anotada como denominador. A reutilização dos conjuntos no desenvolvimento restringe a independência das conclusões.'''
    text=re.sub(r'\*\*Resumo:\*\* .*?(?=\n\n)',lambda _:abstract,text,count=1,flags=re.S)
    anchor='<!-- pagina:16 -->'
    method='''A rodada final de 08/11/2026 registrou, antes da nova inferência de teste, a grade de perdas de 0%, 1%, 5%, 10%, 20%, 30% e 31%, executada integralmente nas duas orientações. Foram preservados os checkpoints e o ambiente; nenhum parâmetro foi escolhido pelos resultados dessas novas oclusões. Tentou-se ajustar uma fusão não negativa dos nove componentes, regularizada em direção aos pesos históricos. Quatro dobras por pessoa da validação, nas condições original e perdas superior e inferior de 10%, compararam quatro intensidades de regularização. A regra exigia ganho fora das dobras na condição original e na média das três condições. Como nenhum ajuste cumpriu a regra, conservaram-se os pesos históricos. O limiar histórico foi mantido na curva principal. Os níveis completos foram medidos mesmo após a primeira reprovação, para caracterizar a degradação e comparar diretamente os dois últimos níveis.\n\n'''
    text=text.replace(anchor,method+anchor)
    table=['Tabela 7 - Grade completa de oclusão na execução de 08/11/2026','',
           '| Perda | Área | Rank-1 superior | Rank-1 inferior | FMR superior | FMR inferior |',
           '|---|---|---|---|---|---|']
    for loss in (0,1,5,10,20,30,31):
        u=get('oclusao_superior',loss)['rates'];l=get('oclusao_inferior',loss)['rates']
        table.append(f"| {loss}% | {100-loss}% | {percent(u['rank1'])}% | {percent(l['rank1'])}% | {percent(u['far'])}% | {percent(l['far'])}% |")
    table+=['','Fonte: do autor (2026). 486 consultas e 7.290 pares impostores por condição.','']
    body='''### 3.2 GRADE COMPLETA DE OCLUSÃO

A execução final avaliou todos os níveis solicitados, incluindo 30% e 31% de perda do suporte originalmente anotado. O cadastro permaneceu intacto e cada consulta foi processada novamente após a alteração. A Tab. 7 apresenta a identificação e a FMR; o suporte de 70% e 69% corresponde ao denominador experimental, sem medição normativa do anel anatômico.

'''+ '\n'.join(table)+f'''
A condição sem oclusão apresentou Rank-1 de {percent(original['rank1'])}%, TAR de {percent(original['tar'])}% e FMR de {percent(original['far'])}%, passando os três critérios separados. O sucesso conjunto foi de {percent(original['joint'])}%, informado sem ser confundido com as medidas marginais. O Rank-1 difere do controle histórico de 91,36%; a análise pareada utiliza exclusivamente o controle recalculado desta mesma rodada, com seu ambiente registrado.

Com 30% de oclusão, a TAR foi de {percent(s30['tar'])}% na orientação superior e {percent(i30['tar'])}% na inferior. Com 31%, foi de {percent(s31['tar'])}% e {percent(i31['tar'])}%. As falsas correspondências também foram medidas com o mesmo limiar, sem recalibração favorável em cada nível. Assim, a curva descreve a resposta de uma configuração fixa, e não uma sucessão de sistemas escolhidos para cada quantidade de perda.

O refinamento histórico encontrou 99,5% de suporte nominal aprovado na orientação superior e 99% na inferior, em uma grade diferente. Esses resultados foram preservados como histórico. A grade completa atual não interpolou níveis ausentes nem anunciou uma transição biológica entre fotografias próximas da fronteira. Referências vazias permaneceram nos denominadores biométricos, com área indefinida.

'''
    text=re.sub(r'### 3\.2 .*?(?=<!-- pagina:18 -->)',lambda _:body,text,flags=re.S)
    delta=audit['orientation_difference_at10'];lo,hi=delta['interval95_cluster_person_pp']
    body=f'''### 3.3 POSIÇÃO DA PERDA E COMPARAÇÃO ENTRE 30% E 31%

A Figura 2 reúne as curvas completas de identificação e falsas correspondências. Na perda de 10%, a diferença de Rank-1 entre as orientações superior e inferior foi de {number(delta['upper_minus_lower_rank1_pp'])} pontos percentuais, com intervalo descritivo de 95% de {number(lo)} a {number(hi)} pontos. A mesma quantidade nominal removida produziu respostas diferentes no sistema.

Figura 2 - Influência da área ocluída na identificação e nas falsas correspondências

![Curva completa com cadastro e limiar fixos](../outputs/ensaio_oclusoes_2026-11-08/analise_final/curva_area_identificacao.png)

Fonte: do autor (2026). Faixas de 95% por pessoa, com galeria fixa; linha vertical em 30%.

'''
    for c in audit['contrast_30_to_31']:
        side=c['condition'].removeprefix('oclusao_');lo,hi=c['interval95_cluster_person_pp']
        body+=f"Na orientação {side}, aumentar a oclusão de 30% para 31% modificou o Rank-1 em {number(-c['rank1_drop_pp'])} pontos percentuais. O intervalo de 95% da perda foi de {number(lo)} a {number(hi)} pontos. Houve {c['lost_correct']} consultas que perderam acerto e {c['gained_correct']} que ganharam acerto.\n\n"
    body+='''A comparação mede diretamente os dois níveis, mas não demonstra um limiar universal em 70%. Os intervalos são descritivos, com 5.000 reamostragens por pessoa e semente 20261108, condicionadas à galeria fixa. Não corrigem a seleção histórica nem certificam toda a curva simultaneamente. A resposta inclui perda de pixels, segmentação e geometria recalculadas, sem separar causalmente esses mecanismos.

'''
    text=re.sub(r'### 3\.3 .*?(?=<!-- pagina:19 -->)',lambda _:body,text,flags=re.S)
    old='O objetivo de estimar a menor fração observada do suporte visível de íris foi atendido de maneira condicionada ao protocolo histórico de oclusão digital.'
    text=text.replace(old,'O estudo quantificou a sensibilidade do sistema à quantidade e à posição da perda de suporte visível, com uma grade completa até 31% de oclusão. O refinamento histórico forneceu uma fronteira condicionada a seu próprio protocolo.')
    text=text.replace('Sob remoção nominal de 10%, a diferença de Rank-1 entre as orientações foi de 24,07 pontos percentuais.',f"Na rodada final, sob remoção nominal de 10%, a diferença de Rank-1 entre as orientações foi de {number(delta['upper_minus_lower_rank1_pp'])} pontos percentuais.")
    text=text.replace('A posição da perda modificou substancialmente o desempenho.',f"Com 30% e 31% de oclusão, o sistema continuou a produzir decisões mensuráveis, mas não satisfez os critérios nominais. A posição da perda também modificou o desempenho.")
    # Condensar detalhes operacionais e repeticoes para abrir espaco ao ensaio completo.
    replacements={
      'Esse resultado foi registrado como ausência de melhora, não como um novo segmentador. A alteração de metadados em um checkpoint não equivale a uma nova função de inferência. O fluxo também recebeu proteção para que uma falha de escrita do relatório de acompanhamento não encerrasse o trabalhador científico. A mudança operacional preservou dados, perda, seleção e fontes da rodada em curso.':'A continuação com negativos internos não produziu um novo modelo elegível: os pesos selecionados permaneceram iguais aos do controle.',
      'A auditoria recalculou métricas a partir das contagens de pixels e reproduziu a regra de seleção. Também investigou uma divergência de hash entre duas cópias serializadas do checkpoint. A igualdade dos 258 tensores e dos demais estados foi confirmada antes da reconciliação da cópia. A evidência evitou interpretar uma diferença de contêiner ou nome de arquivo como mudança real do modelo aprendido.':'A auditoria recalculou as métricas por contagens de pixels e reproduziu a seleção. Uma divergência entre arquivos serializados foi reconciliada após confirmar a igualdade dos 258 tensores e dos demais estados.',
      'Esses resultados são da validação e não podem ser apresentados como melhora sobre os 91,36% do teste histórico. Além das populações diferentes, há particularidades de execução e preparação registradas por rodada. As comparações pareadas foram mantidas em seus próprios contextos. Não se combinaram a melhor identificação de um ensaio com a menor FMR de outro para construir um resultado que nenhum sistema efetivamente produziu.':'Esses resultados pertencem à validação da rodada diversa. A comparação pareada preservou população e preparação, sem combinar métricas favoráveis obtidas por configurações distintas.',
      'O rótulo normal é o informado no depósito; não houve nova avaliação médica dos participantes. A seleção foi feita para ilustração da qualidade disponível e não para calcular uma média favorável. O reconhecimento desses controles não foi medido nesta composição. Assim, as figuras atendem à apresentação dos recortes sem criar uma taxa de acerto nem uma conclusão clínica que os dados não fornecem.':'O rótulo normal é o informado no depósito, sem nova avaliação médica. A seleção ilustra recortes disponíveis; o reconhecimento desses controles não foi medido nesta composição.',
      'Esses dois olhos não forneceram cadastro longitudinal elegível no estudo de quatro consultas. Sua inclusão é documental e não acrescenta sucessos ao reconhecimento clínico. A distinção evita uma conclusão baseada apenas nas fotografias mais bem apresentadas. Os casos com falha também permanecem discutidos, e os resultados quantitativos continuam sendo aqueles obtidos no protocolo de identificação preservado.':'Esses olhos não forneceram cadastro longitudinal elegível no estudo de quatro consultas. Sua inclusão é documental e não acrescenta sucessos ao reconhecimento clínico. Os casos com falha permanecem apresentados na Figura 5.',
    }
    for old,new in replacements.items():
        assert old in text
        text=text.replace(old,new)
    first='Também foram examinados ajustes de normalização de escores e adaptações de representação polar.'
    last='As análises mostram que uma máscara mais extensa'
    concise='''Ajustes de normalização e representação polar também foram avaliados. Um limiar conservador manteve Rank-1 de 90,46% na validação, mas reduziu a TAR a 64,32%, com FMR de 0,2075%. A troca da representação polar, preservando a fusão anterior, produziu Rank-1 de 89,83%, TAR de 90,25% e FMR de 1,0235%. Ambos os pilotos reprovaram os critérios e não alteraram a fronteira histórica.\n\n'''
    text=re.sub(re.escape(first)+r'.*?(?='+re.escape(last)+')',lambda _:concise,text,flags=re.S)
    mobile='''### 3.13 DEMONSTRADOR EM CÂMERA DE CELULAR

Foi implementado um demonstrador privado para Samsung Galaxy S23 base, Android 15, com processamento no Dell G15. O navegador recebe a fotografia e o PC executa a cadeia biométrica. O encaminhamento local por USB permite comunicação sem internet após a preparação dos recursos.

O cadastro é independente dos bancos acadêmicos. Cada registro recebe nome e lado do olho, e fotos adicionais são vinculadas explicitamente. A máscara é apresentada antes de salvar. O nome pode ser corrigido preservando imagens e descritores. Uma imagem idêntica à cadastrada é recusada como teste independente; essa proteção não constitui detecção de vivacidade.

O motor utiliza o segmento visual SAM3.1 residual e nove componentes de identidade. Mantém pesos relativos e padronização histórica, mas não transfere a etapa dependente de candidatos fixos à galeria móvel variável. A saída é uma ordenação experimental, sem limiar validado. Os testes funcionais verificaram nove descritores finitos e uma ordenação esperada entre dois candidatos, sem estimar acurácia do S23. Capturas do telefone não foram incorporadas às métricas deste artigo.

'''
    text=re.sub(r'### 3\.13 .*?(?=<!-- pagina:29 -->)',lambda _:mobile,text,flags=re.S)
    conclusion=f'''## 4 CONSIDERAÇÕES FINAIS

O estudo quantificou a influência da extensão e da posição da oclusão em uma cadeia de identificação ocular entre sessões. Na execução final, o controle sem perda apresentou Rank-1 de {percent(original['rank1'])}%, TAR de {percent(original['tar'])}% e FMR de {percent(original['far'])}%. A grade completa manteve cadastro, limiar e população fixos até 31% de oclusão, permitindo comparar o efeito das intervenções sem recalibração por nível.

Com 30% de perda, o Rank-1 foi de {percent(s30['rank1'])}% na orientação superior e {percent(i30['rank1'])}% na inferior. Com 31%, foi de {percent(s31['rank1'])}% e {percent(i31['rank1'])}%. A diferença entre essas duas perdas foi pequena diante dos intervalos descritivos e não demonstrou uma ruptura justamente em 70% de suporte nominal. O requisito normativo de qualidade utiliza outro denominador e não foi diretamente testado.

O refinamento histórico encontrou fronteiras nominais de 99,5% na orientação superior e 99% na inferior, condicionadas à grade e ao sistema daquela etapa. A grade completa acrescentou evidência da degradação além desses pontos. Como segmentação e geometria foram recalculadas, as diferenças reúnem perda de textura e instabilidade de processamento, sem isolar a contribuição anatômica de cada região.

Os ensaios de segmentação diversa, adaptação SAM3.1 e reajuste da fusão não produziram melhora conjunta suficiente para substituir o controle. A extensão clínica recuperou uma consulta com mudança de escala, mas prejudicou outro cadastro. Os poucos olhos disponíveis e as figuras selecionadas não permitem estimar efeito causal de patologias.

A contribuição é uma avaliação rastreável da sensibilidade à área, com falsas correspondências e falhas preservadas. A reutilização dos conjuntos limita a independência das conclusões. A continuidade exige pessoas e capturas independentes, referências clínicas revisadas e pares longitudinais comparáveis antes de relacionar percentuais de área a doença ou autenticação móvel.
'''
    text=re.sub(r'## 4 CONSIDERAÇÕES FINAIS.*',lambda _:conclusion,text,flags=re.S)
    text=text.replace('| Execução | Rank-1 correto | Genuínos aceitos | Falsas correspondências | Genuíno indisponível |',
                      '| Execução | Rank-1 correto | Genuínos aceitos | Falsos pares | Indisponível |')
    a.output_source.parent.mkdir(parents=True,exist_ok=True);a.output_source.write_text(text,encoding='utf-8')
    print(a.output_source)

if __name__=='__main__':main()
