# Adaptação à oclusão com normalização original — 23/10/2026

## Resultado

Foi concluído o treino do adaptador residual mantendo a normalização polar original. A época 12 foi selecionada pelo critério registrado. O desempenho limpo do componente polar foi preservado, e Rank-1 e TAR melhoraram nas duas oclusões. Entretanto, a FMR permaneceu acima de 1%, reprovando o critério de avanço. **Não houve inferência na validação ou no teste nem substituição da referência principal.**

## Método e população

Foram preparadas as 7.716 fotos do treino original nas condições limpa e oclusão superior/inferior de 10%, aplicada na fotografia nativa antes da segmentação. A anotação define somente a intervenção experimental. Na inferência, a U-Net predita a máscara da foto observada e a normalização original extrai a textura, sem corretor geométrico, SAM ou foto limpa correspondente.

A U-Net, o ResNet18 e sua projeção ficaram congelados. O mesmo adaptador residual de aproximadamente 99 mil parâmetros recebeu características de 512 dimensões, padronizadas somente no ajuste, e corrigiu os descritores de 256 dimensões com residual limitado por 0,05 tanh e normalização L2. Usaram-se semente 63, FP32, AdamW 3e-4, decaimento 1e-4 e lotes de 128 fotos. A perda de alinhamento ao descritor limpo da mesma foto ponderou as condições em 4/1/1, mais regularização residual de 0,01. Foram executadas 12 épocas, conforme o limite registrado, sem varredura de parâmetros.

O ajuste utilizou **6.665 fotos de 167 pessoas**; 91 fotos foram excluídas somente do ajuste por indisponibilidade de extrações válidas nas três condições. O monitor manteve todas as **960 fotos de 16 pessoas distintas, com 480 consultas S2**, inclusive falhas. Os encoders já viram essas pessoas e o monitor é reutilizado; não é uma avaliação independente de generalização. O cadastro S1 permanece limpo em todas as condições. Cada consulta usa uma foto e lado informado, com 16 olhos candidatos.

A elegibilidade exige preservar Rank-1 e TAR limpos e FMR limpa de até 1%. Entre épocas elegíveis, seleciona-se o maior TAR da pior oclusão, seguido do Rank-1 da pior oclusão e do alinhamento médio ao professor nas oclusões. O cosseno limpo é diagnóstico: entradas originais idênticas já têm cosseno aproximadamente um na época zero, portanto não foi exigido aumentá-lo. Cada época recebe um limiar na condição limpa, reutilizado sem ajuste nas duas oclusões.

## Resultados do componente polar no monitor — 480 consultas

| Condição | Rank-1 inicial | Rank-1 selecionado | TAR inicial | TAR selecionado | FMR inicial | FMR selecionada |
|---|---:|---:|---:|---:|---:|---:|
| Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 479/480 (99,79%) | 0,9861% | 0,9861% |
| Perda superior de 10% | 396/480 (82,50%) | 405/480 (84,38%) | 372/480 (77,50%) | 380/480 (79,17%) | 1,5694% | 1,5139% |
| Perda inferior de 10% | 291/480 (60,63%) | 328/480 (68,33%) | 268/480 (55,83%) | 288/480 (60,00%) | 1,6528% | 1,4861% |

Foram nove identificações corretas adicionais na oclusão superior e 37 na inferior, com oito e vinte aceitações genuínas adicionais. As aceitações impostoras passaram de 113 para 109 e de 119 para 107, sobre 7.200 comparações por condição. Ainda excedem o limite de 1%. Uma falha de extração permaneceu na condição limpa e na superior, e duas na inferior. O limiar da época selecionada foi 0,2877560953299205; não é o limiar do reconhecedor principal.

O critério exige **simultaneamente** preservação limpa, melhora de Rank-1/TAR nas duas oclusões e FMR de até 1% em ambas. O candidato cumpre as duas primeiras partes, mas falha na terceira e também permanece abaixo de 90% em Rank-1/TAR ocluídos. A seleção da época não significa aprovação do candidato.

## Verificação e preservação

Passaram cinco testes direcionados: o novo teste de critérios e os quatro do adaptador/monitor, incluindo cadastro limpo e contabilização de falhas. A preparação reproduziu exatamente os descritores limpos do professor: diferença máxima zero. A auditoria refez o adaptador nos descritores armazenados e reproduziu exatamente os escores selecionados e finais, a escolha da época 12 e a reprovação. A validação condicional foi encerrada sem inferência por esse bloqueio.

Os pesos selecionados e da última época, seus escores e registros estão preservados em `backups/adaptador_polar_original_2026-10-23`; os arquivos legíveis estão em `outputs/adaptador_polar_original_2026-10-23` e `outputs/adaptador_polar_original_val_2026-10-23`. O cache de características foi excluído do pacote e registrado por hash. A recuperação compacta verifica os hashes, a seleção e as decisões sem repetir a extração das redes ou o treinamento. Não foram alteradas exceções do Defender, e o envio pelo OneDrive não foi verificado.

```powershell
.\executar.ps1 preservar_adaptador_original.py
.\executar.ps1 verificar_adaptador_original.py --root "$env:TEMP/pfc-adaptador-original-restaurado-20261023"
```

## Consequência para a pesquisa

Este piloto oferece evidência interna mais favorável à adaptação mantendo a normalização original do que à troca de geometria, mas não autoriza uma afirmação de superioridade independente entre as tentativas reutilizadas. O resultado pertence a um componente no monitor de treino, não à fusão principal ou ao teste. Os **444/486 (91,36%)** do teste principal e as fronteiras nominais de área permanecem inalterados; não há novo mínimo de área aceito.

A hipótese de incluir separação entre identidades foi posteriormente executada com protocolo próprio, ajuste somente nas pessoas do treino e o mesmo controle limpo. Houve pequeno ganho de identificação, mas a FMR piorou ligeiramente e o avanço foi novamente barrado. Ver [perda de identidade e resultados](ADAPTACAO_IDENTIDADE_POLAR_2026-10-23.md). Não será alterado o limiar com os exemplos ocluídos para promover este candidato reprovado.
