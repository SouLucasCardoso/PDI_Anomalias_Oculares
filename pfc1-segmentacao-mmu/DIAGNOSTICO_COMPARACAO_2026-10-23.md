# Limites dos escores polares sob oclusão

## Pergunta e alcance

Após os pilotos de adaptação, verificamos se o gargalo observado poderia ser resolvido apenas alterando o limiar. Foram reutilizados os escores salvos de 480 consultas de 16 pessoas do monitor interno de TREINO, com 16 olhos candidatos do mesmo lado. Esses participantes foram vistos pelos encoders e reutilizados no desenvolvimento: não se trata de generalização independente. Não houve novo treino, inferência de imagens, uso da validação/teste ou alteração do sistema principal.

O diagnóstico calcula o menor limiar que permite FMR empírica de até 1% em cada condição, mantendo as falhas no denominador. Como usa os rótulos das próprias consultas ocluídas, esse limiar é privilegiado e **não pode ser adotado em produção nem promover candidatos**. Ele fornece o maior TAR empírico possível por um único limiar aplicado aos escores salvos dessa condição. Não estabelece limite para outros comparadores, normalizações, modelos ou dados.

## Resultados

| Componente | Rank-1 superior 10% | Rank-1 inferior 10% | TAR diagnóstico máximo superior, FMR ≤1% | TAR diagnóstico máximo inferior, FMR ≤1% |
|---|---:|---:|---:|---:|
| Polar original | 82,50% | 60,63% | 76,04% | 51,88% |
| Adaptação top3 | 84,17% | 68,33% | 77,08% | 57,29% |
| Penalização absoluta | 83,54% | 66,67% | 76,67% | 56,04% |
| Correção espacial | 83,13% | 68,13% | 78,13% | 58,13% |

Para a correção espacial, o diagnóstico aceita 375/480 consultas superiores e 279/480 inferiores, contra as 432 necessárias para TAR de 90%. São déficits de 57 e 153 consultas. Os valores com o limiar limpo original eram TAR de 80,63%/60,21%, porém com FMR acima de 1%; impor o limite de falsas aceitações reduz o TAR. A calibração escalar, sozinha, não resolve estes escores. O Rank-1 também não muda ao ajustar um limiar comum.

Na comparação entre top3 e espacial:

| Condição | Ambos acertam | Só top3 acerta | Só espacial acerta | Ambos erram |
|---|---:|---:|---:|---:|
| Limpa | 479 | 0 | 0 | 1 |
| Superior 10% | 393 | 11 | 6 | 70 |
| Inferior 10% | 308 | 20 | 19 | 133 |

Mesmo um seletor privilegiado que soubesse escolher o acerto de um desses dois métodos por consulta alcançaria somente 410/480 (85,42%) e 347/480 (72,29%). Isso limita apenas a seleção entre as duas decisões finais; **não é limite superior para fusão de escores**, que poderia corrigir consultas em que ambos erram. Também não prova que toda fusão seja inútil. A análise não treinou nem avaliou uma fusão.

## Decisão para a próxima etapa

Encerrar por enquanto os pequenos ajustes globais e a busca de limiar sobre estes candidatos rejeitados. A próxima hipótese deve atuar na comparação da textura disponível, com suporte espacial explícito, e ser ajustada somente nas pessoas de treino antes do monitor. Não selecionar setores pela anotação, por identidade correta ou pelo resultado do teste. Cadastrar imagens limpas, manter uma única foto de consulta e lado informado. Uma alteração só poderá avançar se preservar o controle limpo e melhorar as oclusões respeitando a FMR definida, sem recalibrar no monitor ocluído.

O diagnóstico não representa ganho novo de reconhecimento, não altera os 444/486 (91,36%) do teste principal e não estabelece novo mínimo de área. Ele elimina uma hipótese insuficiente para orientar o próximo experimento e economizar novas rodadas de treino.

## Reprodutibilidade

`diagnosticar_limites_comparacao.py` confere alinhamento das consultas/rótulos, reproduz Rank-1/TAR/FMR publicados com os limiares originais e registra SHA-256 dos 12 arquivos de escores utilizados. Dois testes passaram, incluindo empates e falhas de extração. Os escores de entrada já estão preservados nos pacotes dos pilotos top3, penalização e espacial. Resultado legível: `outputs/diagnostico_comparacao_treino_2026-10-23/CONCLUIDO.json`.

```powershell
.\executar.ps1 diagnosticar_limites_comparacao.py --root "$env:TEMP/pfc-tcc-resultados"
```

Para repetir, os três diretórios de experimentos de entrada devem estar recuperados sob o mesmo `--root`. O diretório de saída deve ser novo; não há sobrescrita de uma execução concluída.
