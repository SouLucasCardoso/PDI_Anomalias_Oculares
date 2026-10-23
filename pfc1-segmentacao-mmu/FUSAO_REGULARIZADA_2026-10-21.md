# Fusao regularizada aprendida no treino — 21/10/2026

## Objetivo e desenho

Aprender uma combinacao compartilhada dos reconhecedores, sem ajustar pesos aos erros conhecidos da validacao. Os encoders e o segmentador original permanecem congelados. Nenhuma nova inferencia no teste e nenhuma substituicao automatica do candidato aprovado.

O manifesto de treino possui 183 participantes. Para esta aprendizagem por sessao, sao elegiveis 74 participantes com ambos os lados representados nas sessoes 1 e 2:148 olhos,4.442 imagens e 2.222 consultas da sessao 2. As identidades da validacao nao participam da perda. Os encoders ja foram treinados nessas pessoas do treino; portanto suas representacoes sao internas ao treino, nao uma simulacao de generalizacao para pessoas novas. Essa e uma limitacao a conferir na validacao com identidades distintas.

As tres condicoes sao limpa, oclusao superior 10% e inferior 10%. A alteracao e aplicada a pixels da iris anotada na foto original; depois a segmentacao automatica e a geometria sao recalculadas. As anotacoes definem somente a intervencao. Os cadastros da sessao 1 nao sao alterados.

Cada consulta gera quatro episodios com 16 candidatos do mesmo lado: o genuino e 15 impostores sorteados sem reposicao, semente 54. Cada componente e padronizado sobre os candidatos daquela unica consulta. As duas vistas ArcIris formam um grupo; os outros sete componentes ficam separados. Aprende-se um unico vetor de oito pesos nao negativos, de soma 1, para todas as identidades e condicoes.

O treinamento tem 300 passos fixos de Adam, taxa 0,05, perda de entropia cruzada entre candidatos e penalidade 0,1 vezes a distancia quadratica dos pesos uniformes. Nao ha busca de epocas, regularizacao ou pesos na validacao. Falhas de extracao do treino sao contabilizadas e excluidas apenas da perda; todas as 482 consultas da validacao ficam no denominador.

## Controles e verificacao

Comparar pesos aprendidos com pesos uniformes sobre a MESMA nova representacao por consulta. Manter tambem a fusao congelada original como referencia, pois mudar a normalizacao dos componentes pode alterar resultados independentemente do aprendizado.

Cada estrategia recebe um unico limiar estimado nas comparacoes impostoras da validacao limpa, com FMR empirica no maximo 1%; o limiar permanece fixo nas duas oclusoes. A validacao foi reutilizada no desenvolvimento e nao e confirmacao independente. O arquivoJSON dos pesos deve ser recarregado, os escores reproduzidos e as diferencas calculadas por consulta e por bootstrap de pessoas, sem mudar modelos apos observar os resultados.

## Execucao

Treinamento concluido em aproximadamente 15 minutos. Foram usados 26.512 episodios:11 consultas limpas,13 superiores e 14 inferiores nao puderam contribuir para a perda por falhas de extracao/disponibilidade. Essas exclusoes sao apenas do treino; nenhuma consulta foi retirada da validacao. A perda regularizada passou de 0,90436 para 0,62072; a entropia cruzada passou de 0,90436 para 0,60374.

## Resultados de validacao

| Estrategia | Limpa: Rank-1 / TAR / FMR | Superior 10%: Rank-1 / TAR / FMR | Inferior 10%: Rank-1 / TAR / FMR |
|---|---|---|---|
| Fusao congelada original |90,04 /90,66 /0,98%|80,71 /78,01 /1,30%|59,96 /57,88 /2,41%|
| Nova normalizacao, pesos uniformes |89,42 /90,25 /0,98%|79,05 /77,59 /1,33%|59,13 /57,05 /2,59%|
| Nova normalizacao, pesos aprendidos |84,65 /81,54 /0,98%|76,97 /70,12 /1,20%|65,35 /58,71 /1,41%|

Todos os valores sao percentuais. O limiar aprendido na condicao limpa foi 0,8768514375656272 para os pesos aprendidos e 0,8558778210857256 para os uniformes; cada um ficou fixo nas oclusoes. As falhas de extracao na validacao foram 4,4 e 7, respectivamente, mantidas entre as 482 consultas.

Os pesos aprendidos foram: RGB 22,97%, polar 0,42%, espacial 0,09%, ResNet50-12832,76%, ConvNeXt 35,87%, ResNet50-2247,71%, Transformer 0,08% e ArcIris medio 0,09%. Sao parametros de uma combinacao de modelos correlacionados e nao medidas de importancia anatomica da iris.

Comparada ao controle uniforme equivalente, a aprendizagem perdeu 23 identificacoes limpas (431 para 408) e ganhou 30 na oclusao inferior (285 para 315). Comparada ao candidato congelado, perdeu 26 limpas (434 para 408), perdeu 18 superiores (389 para 371) e ganhou 26 inferiores (289 para 315). Na inferior, recuperou 46 casos do candidato congelado, mas perdeu 20 outros casos.

O ganho inferior de Rank-1 sobre o congelado foi 5,39 pontos percentuais, IC 95% descritivo pareado por pessoa de 1,46 a 9,67; o ganho de TAR foi 0,83 ponto, IC 95% de-3,33 a 5,17. A perda limpa de Rank-1 foi 5,39 pontos, IC 95% da diferenca de-9,13 a-2,08. Esses intervalos usam 5.000 reamostragens de pessoas com galeria e limiares fixos, sem correcao por selecao de estrategias ou garantia populacional.

## Conclusao e proxima etapa

A fusao aprendida nao passou e nao substitui o candidato aprovado. A melhora da perda no treino nao se generalizou ao reconhecimento limpo de pessoas distintas. Isso e compativel com sobreajuste ou diferenca entre as distribuicoes; esta rodada nao isola uma causa unica. Nao houve mudanca nos resultados anteriores de teste, nos limiares congelados ou nas fronteiras nominais de area.

O proximo desenho justificavel e separar pessoas dentro do treino para ajustar encoders e aprender fusao, ou gerar predicoes por validacao cruzada de pessoas fora do ajuste de cada encoder. Isso exige novo treinamento dos modelos-base: os atuais ja viram as pessoas usadas na aprendizagem da fusao. Nao basta aumentar os 300 passos nem escolher outros pesos apos olhar a validacao. Esse novo treinamento ainda nao foi iniciado.

## Verificacao e preservacao

O modeloJSON foi recarregado e reproduziu todos os escores uniformes/aprendidos nas tres condicoes com diferenca maxima zero. As contagens publicadas, os limiares limpos, as decisoes e os rotulos foram conferidos. Os hashes dos encoders permaneceram iguais e todas as entradas e validades do cadastro foram verificadas como identicas nas tres condicoes. Foram aprovados 79 testes automatizados, incluindo recuperacao integral e deteccao de corrupcao do pacote textual.

Devido ao bloqueio da copia binaria direta para o OneDrive, foi preservado no projeto um ZIP em 45 partes base 64, total 366.677 bytes antes da codificacao, com 12 arquivos: modelo, escores de validacao, protocolo, conclusao, verificacao e copias dos dois scripts. SHA256 do ZIP: `fe3b8e59491c6898cbd9b1e3f11d82a4be03435bd9b55281e763b772703c403f`.

O pacote em `backups/fusao_regularizada_textual_2026-10-21` foi restaurado de fato e os escores foram novamente reproduzidos com diferenca zero. As partes base 64 sao backup local e ficam fora do Git, assim como os NPZ. O manifesto e o modeloJSON legivel permanecem no projeto. As copias legiveis dos JSON podem mudar terminadores de linha; os hashes originais de bytes correspondem aos arquivos exatos dentro do pacote.

```powershell
.\executar.ps1 restaurar_pacote_textual.py backups/fusao_regularizada_textual_2026-10-21 --destination "$env:TEMP/pfc-fusao-restaurada"
.\executar.ps1 verificar_fusao_regularizada.py --folder "$env:TEMP/pfc-fusao-restaurada/resultados" --validation-only
```

Escolher um destino novo. O pacote nao inclui imagens, pesos dos encoders, arrays de entradas nem matrizes de escores do treino; eles sao necessarios para refazer a aprendizagem, mas nao para recarregar os pesos da fusao e reproduzir a validacao com os componentes ja existentes no projeto. As matrizes de treino continuam em `%TEMP%/pfc-tcc-resultados/fusao_regularizada_treino_2026-10-21/{clean,upper10,lower10}`. Este pacote pequeno nao substitui o backup integral anterior dos modelos-base.
