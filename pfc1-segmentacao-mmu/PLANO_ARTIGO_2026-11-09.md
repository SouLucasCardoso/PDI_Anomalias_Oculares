# Produção do artigo até 9 de novembro de 2026

> **Atualização de escopo em 20/10, após esclarecimento do autor:** o objetivo ativo é estudar área preservada da íris e reconhecimento de identidade ocular, com extensão a condições clínicas. O plano de classificação abaixo fica preservado como histórico e não deve orientar a execução atual. Consultar `PROTOCOLO_AREA_IRIS_2026-10-20.md` e o rascunho ativo `artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md`.

## Cronograma ativo

**Concluído em 20/10:** segmentação retreinada e testada, curva DINOv3 completa,
validação e teste clínico HDBIF, treinamento de identidade, curva exploratória
do novo encoder e diagnóstico condicional por consulta. O texto científico tem
resumo, métodos, resultados, discussão, conclusões e referências de trabalho.
A tentativa Nuclear foi interrompida por qualidade antes de reconhecimento.
Os próximos marcos são revisão científica com o orientador, diagramação no
modelo institucional, normalização de referências e conferência final.

- 20–21/10: concluir retreinamento, piloto e início das curvas de oclusão; auditar capturas clínicas e preservar pesos.
- 22–24/10: conferir resultados originais e qualidade das máscaras; avaliar reconhecedor específico de íris se o extrator genérico for insuficiente; congelar protocolo clínico após inspeção.
- 25–27/10: concluir reconhecimento, intervalos e análises de sensibilidade. Fechar escopo e registrar mínimos não determinados quando aplicável.
- 28–30/10: fechar primeira versão integral do artigo com resultados reais.
- 31/10–03/11: revisão com orientador e ajustes de texto e análises necessários.
- 04–06/11: aplicar modelo institucional, revisar referências e conferir paginação.
- 07/11: versão pronta; 08/11: reserva; 09/11: entrega.

As datas dependem da conclusão e da qualidade das execuções. Não ampliar indefinidamente bases ou modelos. O piloto concluído serve somente à verificação técnica.

## Histórico anterior à correção do objetivo

Data de organização: 20/10/2026. Restam 20 dias. A prioridade é concluir uma
comparação clínica reproduzível que responda ao pré-projeto, com escopo limitado,
em vez de ampliar indefinidamente modelos e bases.

## Entrega científica mínima

**Pergunta:** em que medida a segmentação da íris altera a classificação entre
imagens Normal e imagens com condições oculares anotadas?

**Desenho principal preparado:** U-Net treinada no UBIPr e congelada; SLP-VLD
com grupos conservadores separados; mesma CNN com transferência de aprendizado para
imagem original, caixa de íris com contexto e máscara de íris na mesma caixa.
Três sementes fixas. Diferença pareada de AUROC como desfecho principal,
acurácia balanceada, sensibilidade, especificidade e macro-F1 como secundários.

O SLP-VLD auditado permite 1.520/304/304 imagens, com 911 grupos conservadores
sem sobreposição. O teste interno tem somente 27 imagens Normal, exigindo
incerteza e avaliação do desequilíbrio. Sementes não contam como indivíduos.
A melhoria da classificação com recorte não é pressuposta; piora ou ausência
de diferença também respondem à pergunta.

**Decisão concluída em 20/10:** SLP-VLD adquirido e auditado, com uma duplicata
removida e grupos conectados por IDs compartilhados. O mapa original de
pacientes não está disponível; documentar a limitação dos grupos publicados.
CatScreen é contingência e avaliação externa complementar; não misturar
controles entre bases para aumentar N.

**Avaliação externa principal:** 99 imagens Bijie, sem ajuste dos modelos;
CatScreen Clean como domínio adicional. **Extensão opcional:** SLID. O CSV
adquirido não contém vínculo por paciente; não usá-lo para divisão interna
aleatória nem para bootstrap de pessoas. Revisar condições de uso antes de
publicar exemplos. A extensão não deve impedir o fechamento do artigo principal.

## O que já está em execução ou preparado

- Retreinamento UBIPr iniciado em `outputs/cnn/ubipr_retreino_2026-10-20`:
  30 épocas máximas, lote 32, base 8, entrada 320 × 240, semente 42 e paciência
  10. Checkpoint escolhido exclusivamente por Dice de validação UBIPr.
- Log em `outputs/retreino_2026-10-20.log`; histórico gravado a cada época;
  pesos gravados por substituição atômica; configuração e ambiente registrados.
- Backup local ZIP verificável do checkpoint parcial criado em `backups/`.
  Manter também cópia externa para proteção contra falha de disco.
- SLP-VLD: 2.228 registros auditados, uma duplicata removida; protocolo ativo
  em `outputs/clinico_slpvld_2026-10-20`. CatScreen auditado como alternativa
  e domínio externo, sem executar o protocolo interno inicialmente preparado.
- SLID baixado por Git LFS, extraído e auditado: 2.617 imagens válidas.
- Nuclear Cataract v2 baixado e auditado: 1.320 imagens, 115 pacientes, seleção
  secundária de 335 imagens com graus NC de 69 pacientes. Sem controles saudáveis
  estabelecidos nos arquivos adquiridos; não é o substituto binário principal.
- ResNet18 ImageNet oficial baixada e hash verificado; ainda não treinada na tarefa clínica.
- SAM 2, SAM 3.1, OpenIRIS e DINOv3 têm pesos locais e testes de inferência.
  Fine-tuning de foundation models não integra o caminho crítico.

## Cronograma com datas de corte

| Prazo | Trabalho | Critério de conclusão |
|---|---|---|
| 20–21/10 | Fechar auditoria de dados públicos e retreinamento UBIPr | Checkpoint final, hashes, manifesto e decisão de base clínica |
| 22–24/10 | Gerar entradas clínicas e verificar máscaras; implementar classificador pareado | Três entradas com mesmas amostras; falhas contabilizadas; treino/validação executáveis |
| 25–27/10 | Rodar sementes predefinidas, avaliar teste uma vez e calcular incerteza | Escores individuais, tabelas finais e gráficos reproduzíveis |
| 28–30/10 | Redigir primeira versão completa no modelo da UniSatc | Introdução, método, resultados reais, discussão e conclusão; enviar ao orientador pelo próprio autor |
| 31/10–03/11 | Incorporar revisão de conteúdo e conferir referências | Pergunta respondida, inferências proporcionais aos dados e figuras verificadas |
| 04–06/11 | Normalização, formatação e revisão final | Artigo entre 15 e 30 páginas, referências e citações consistentes |
| 07/11 | Fechar DOCX/PDF e pacote de reprodução | Arquivos revisados visualmente, cópias local e externa |
| 08/11 | Reserva para correções e conferência de submissão | Nenhum experimento novo obrigatório |
| 09/11 | Entregar o artigo | Arquivo final e evidência de entrega |

Não introduzir uma nova base principal depois de 22/10. Não retunar modelos ou
limiares a partir do resultado de teste. Reexecutar após essa data somente por
erro de implementação identificado e documentado, preservando a execução anterior.

## Estrutura exigida pelo modelo localizado no PFC I

O modelo institucional contém as seguintes instruções, aqui transcritas em
forma de planejamento, sem substituir a conferência final do arquivo fonte:

- 15–30 páginas; A4; Arial 12; espaçamento 1,5 no corpo.
- Margens superior/esquerda de 3 cm e inferior/direita de 2 cm.
- Primeira linha de parágrafo com recuo de 2 cm; paginação superior direita.
- Resumo informativo em parágrafo único e espaço simples, seguido de palavras-chave.
- Introdução; Procedimento Experimental, com Materiais e Métodos; Resultados e
  Discussões; Considerações Finais; Referências; agradecimentos opcionais.
- Texto em terceira pessoa; título em maiúsculas, centralizado e negrito.
- Autores à direita, com titulação/e-mail em nota; não inventar dados faltantes.
- Figuras e tabelas numeradas, citadas no texto, título acima e fonte abaixo;
  conteúdo de tabelas em tamanho 10. Citações e referências conforme orientação
  institucional e revisão de normalização.

Distribuição de trabalho sugerida, para aproximadamente 18–22 páginas: resumo
1, introdução 3–4, procedimento experimental 5–6, resultados/discussão 6–7,
considerações finais 1, referências 2–3. Ajustar a distribuição ao conteúdo real;
não preencher páginas com revisão genérica ou resultados históricos não reproduzidos.

## Conteúdo que não deve ser anunciado como resultado final

- Dice/Rank-1 históricos sem o checkpoint que os produziu.
- Métricas dos testes de instalação com duas/oito imagens.
- Reconhecimento de identidade como se fosse diagnóstico de doença.
- Catarata leve como sinônimo de olho saudável.
- Valores altos de acurácia sem separar pessoas ou sem informar prevalência.
- Máscaras previstas como padrão de referência de segmentação clínica.
- Dados sintéticos ou perturbações artificiais apresentados como doença real.

## Acompanhar e preservar a execução

Na pasta `pfc1-segmentacao-mmu`:

```powershell
.\executar.ps1 status_producao.py
Get-Content outputs/retreino_2026-10-20.log -Tail 10
Get-Content outputs/cnn/ubipr_retreino_2026-10-20/historico.csv -Tail 5
.\executar.ps1 backup_experimento.py outputs/cnn/ubipr_retreino_2026-10-20
```

O treinamento somente estará concluído quando houver `metricas.json` nesse
diretório e o processo terminar sem erro. Histórico e checkpoint parcial não
equivalem a conclusão. Não executar o mesmo treinamento em paralelo na GPU.
No fim, registrar SHA-256 do checkpoint e copiar o ZIP para outro dispositivo
ou armazenamento externo autorizado.
