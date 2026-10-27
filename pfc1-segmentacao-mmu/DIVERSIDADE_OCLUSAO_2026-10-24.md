# Diversidade de intervenções nativas no ajuste polar

## Hipótese

O controle anterior foi ajustado com perda superior/inferior fixa de 10% e cinza 128. Este piloto testa se variar essas intervenções no ajuste melhora a transferência. O protocolo e o plano de 3.222 intervenções foram registrados antes da preparação dos mapas e do treino. Não foram pesquisados percentuais, preenchimentos ou sementes após observar os escores.

Para cada uma das 1.611 consultas S2 elegíveis do ajuste, foram sorteadas uma intervenção superior e uma inferior: perda nominal inteira entre 1% e 20%, uniforme, e preenchimento entre 32, 64, 128, 192 e 224. Semente 20261024. A intervenção ocorre na foto nativa antes da U-Net e da normalização polar originais. A anotação só define os pixels da simulação; não entra na segmentação ou no reconhecedor. O sorteio vale por foto, fixo durante as oito épocas, não é uma nova intervenção a cada época. Diferentes áreas e preenchimentos são estudados conjuntamente como uma hipótese de diversidade; este desenho não separa seus efeitos causais.

Mantiveram-se arquitetura, perda, divisão de pessoas, otimização e seleção do controle fixo de 10%: cinco kernels originais de layer4, 8.388.608 pesos treináveis, prefixo/projeção/BatchNorm congelados, AdamW 1e-5, lote de 16 fotos, oito épocas e alinhamento ao descritor limpo + margem top3 + penalização de impostores + ancoragem nos kernels originais. O modelo parte do encoder original, não de pesos rejeitados. As pessoas são 151 de ajuste (6.067 fotos), 16 de calibração interna (120 consultas) e 16 do monitor antigo (480 consultas), sem sobreposição entre esses três grupos. Os encoders anteriores já viram essas pessoas; o monitor é reutilizado e não é confirmação independente.

O cadastro S1 permanece limpo em todas as condições. Calibração e monitor mantêm as intervenções fixas de 10%, sem receber as novas simulações. A seleção usa somente a menor perda de ajuste entre épocas que preservam Rank-1/TAR internos limpos; o monitor e as oclusões internas são calculados depois de congelar os pesos. O limiar vem somente do grupo interno limpo, com alvo de FMR de 0,5%, e é o mesmo em todas as condições e pessoas. Não se ajusta nas oclusões do monitor. Uma consulta é uma única foto observada, com lado informado e 16 olhos candidatos do mesmo lado.

## Preparação e resultado

Foram preparados 3.222 mapas FP32 adicionais, 422.314.112 bytes, em aproximadamente 84 segundos. O cache original de 1,59 GB foi reutilizado, sem cópia; o carregador combina os índices dos dois caches. Houve dez falhas de extração nas novas simulações, mantidas no ajuste com textura neutra. Nenhuma foto elegível original foi removida. Como essas vistas neutras não contêm informação individual suficiente, a manutenção de suas perdas de identidade é uma limitação desta formulação; os resultados não isolam o efeito de diversidade da dificuldade de extração introduzida por ela.

A época 8 foi selecionada após as oito épocas previstas. Os kernels/buffers congelados permaneceram com o mesmo hash.

| Condição do monitor | Controle fixo 10%: Rank-1 | Variado: Rank-1 | Controle: TAR | Variado: TAR | Controle: FMR | Variado: FMR |
|---|---:|---:|---:|---:|---:|---:|
| Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 99,79% | 99,79% | 0,5278% | 0,6806% |
| Superior 10% | 399/480 (83,13%) | 398/480 (82,92%) | 77,92% | 78,96% | 1,0556% | 1,4028% |
| Inferior 10% | 330/480 (68,75%) | 315/480 (65,63%) | 57,08% | 57,92% | 1,0000% | 1,2917% |

O controle é o ajuste de kernels com penalização e calibração separada, não a fusão principal ou um resultado de teste. Cada método tem seu próprio limiar interno limpo, pelo mesmo procedimento. O limiar novo foi 0,2900834977626801. As pequenas altas de TAR acompanharam mais falsas aceitações; não constituem superioridade conjunta. O Rank-1 caiu uma consulta na superior e 15 na inferior. As falsas aceitações foram 101 e 93 em 7.200 comparações, contra o máximo de 72. Permaneceram uma falha limpa/superior e duas inferiores na avaliação.

O piloto melhora alguns números em relação ao componente original sem ajuste, mas **não supera o controle direto de perda fixa**. Foi barrado antes da validação; nenhum teste final ou novo mínimo foi executado. Os 444/486 (91,36%) do teste principal e a fronteira de área anterior continuam inalterados.

## Verificação

Passaram três testes de contagem/sentido da intervenção, referência vazia e índice híbrido com ordem/repetições. A auditoria reproduziu o sorteio, confirmou que todos os índices das novas simulações pertencem exclusivamente às consultas S2 de ajuste e conferiu as contagens exatas de pixels das 3.222 intervenções.

A auditoria dos pesos reconstruiu os descritores selecionados e os escores dos grupos interno/monitor sobre os mapas originais, reproduzindo exatamente métricas, limiar, seleção e bloqueio. Verificou a origem dos cadastros limpos e os hashes dos dois caches. Não refez as oito épocas.

Em uma conferência adicional, foi reprocessado o primeiro lote de 32 simulações na ordem do plano, sem seleção por escore. Foram refeitos preenchimento nativo, U-Net, normalização e prefixo. Os pixels afetados e flags de validade coincidiram; a diferença máxima nos mapas foi zero. Isso é uma auditoria amostral do cache, não a regeneração de todos os 3.222 mapas.

## Preservação e recuperação

O ZIP contém 40 arquivos, com 32.765.878 bytes, em 44 partes base64. Preserva pesos, escores, protocolo, plano, contagens, índices, auditorias e código. O checkpoint final é preservado por delta XOR reversível sobre o selecionado; ambos voltam aos bytes originais com SHA-256 conferido, sem quantização. Os caches foram excluídos do pacote e identificados por hash; a recuperação compacta não depende de regenerar as novas imagens.

```powershell
.\executar.ps1 preservar_diversidade_oclusao.py
.\executar.ps1 auditar_diversidade_oclusao.py --root "$env:TEMP/pfc-diversidade-restaurado-20261024"
```

A auditoria completa requer também os caches originais e o novo cache no diretório do experimento. O encoder original é uma dependência já existente, identificada no protocolo. A gravação local e a recuperação não verificam upload ao OneDrive. Não houve commit ou push.

## Decisão

Não promover o modelo nem ampliar épocas ou pesquisar preenchimentos olhando o monitor. Manter o protocolo atual de Rank-1 e FMR por pares. Uma decisão que aceita só o maior candidato pode ser estudada separadamente se o escopo for esclarecido, mas não deve ser apresentada como ganho equivalente de verificação: nesse caso, a FMR passa a depender por construção do número de candidatos e das decisões permitidas por consulta.
