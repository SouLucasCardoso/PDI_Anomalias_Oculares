# Ponderação aprendida de regiões do descritor polar

## Retomada após o bloqueio

Após o usuário permitir os arquivos bloqueados, sem adicionar exceções, o PyTorch 2.14.1+cu126 voltou a carregar. Uma multiplicação de matrizes FP32 na RTX 3050 Laptop de 6 GB terminou corretamente. Na mesma sessão foram concluídos testes, oito épocas de treinamento e auditoria com GPU. Não foram modificadas configurações do Defender pelo agente. Isso confirma esta execução, sem garantir ausência de futuros bloqueios.

## Hipótese

O piloto regional anterior perdia discriminação até na condição limpa. Este piloto preserva o extrator e a projeção global originais e substitui somente a média espacial por uma ponderação aprendida. Na inicialização, os pesos são uniformes, reproduzindo o descritor original. O objetivo é aprender a reduzir contribuições prejudiciais usando apenas a imagem observada, sem receber localização da oclusão ou identidade correta na inferência.

O último bloco original, a projeção e todos os parâmetros/estatísticas BatchNorm ficam congelados. Um módulo Conv1x1 512→32, ReLU, Conv1x1 32→1 produz pesos para as 32 posições do mapa 2×16. A última convolução inicia em zero. Os pesos finais são metade uniformes e metade softmax aprendido, garantindo soma um e um piso de 0,5/32 por posição. São **16.449 parâmetros treináveis**. As posições têm campos receptivos amplos e não representam porcentagens independentes de pixels de íris visível. Atenção não é uma máscara clínica ou explicação validada de anomalias.

## Ajuste e critérios

Protocolo registrado antes do treino; semente 63. Foram reutilizados por hash os 12.160 mapas FP32 de layer3 do piloto espacial, sem repetir segmentação, normalização ou prefixo CNN. Cadastro S1 limpo em todas as condições; consultas S2 com oclusão superior/inferior de 10% aplicada anteriormente na imagem nativa. A anotação só definiu a intervenção; a U-Net original extraiu a máscara do reconhecedor.

O ajuste usa 6.665 fotos de 167 pessoas e cadastro de 4.955 fotos S1/334 olhos. A perda compara o descritor com o descritor limpo da mesma foto durante o treino, pesos limpa/superior/inferior 4/1/1, mais 0,1 da perda top3 contra o impostor mais difícil do mesmo lado e 1e-4 da média quadrática do kernel final de atenção. O cadastro é atualizado no início de cada época e fica sem gradiente na comparação. Somente consultas S2 do ajuste participam da perda de identidade; pessoas do monitor não recebem gradientes.

AdamW 1e-4, decaimento 1e-4, lote de 16 fotos e até oito épocas, com parada após três épocas sem melhora a partir da quarta. Não houve varredura de arquitetura, piso de atenção, perdas ou taxa. O monitor tem 480 consultas de 16 pessoas separadas do ajuste, já vistas pelos encoders e reutilizadas em experimentos anteriores. Portanto, é monitor de desenvolvimento, não avaliação independente.

Cada época recebe um único limiar a partir da condição limpa, aplicado sem mudança às duas oclusões. Seleção e bloqueio seguem os critérios dos pilotos anteriores: preservar Rank-1/TAR limpos, FMR ≤1% e, para avançar, melhorar Rank-1/TAR em ambas as oclusões sem exceder FMR de 1%. Uma consulta usa uma única imagem observada e lado informado; o cadastro pode conter várias imagens limpas. A foto limpa correspondente não é usada na identificação da consulta ocluída.

## Resultado do componente no monitor de treino

As oito épocas terminaram e a época 8 foi selecionada pelo critério registrado.

| Condição | Rank-1 original | Rank-1 atenção | TAR original | TAR atenção | FMR original | FMR atenção |
|---|---:|---:|---:|---:|---:|---:|
| Limpa | 479/480 (99,79%) | 479/480 (99,79%) | 99,79% | 99,79% | 0,9861% | 0,9861% |
| Superior 10% | 396/480 (82,50%) | 402/480 (83,75%) | 77,50% | 79,58% | 1,5694% | 1,7083% |
| Inferior 10% | 291/480 (60,63%) | 295/480 (61,46%) | 55,83% | 59,17% | 1,6528% | 1,8056% |

O módulo trouxe seis e quatro identificações corretas adicionais, com dez e 16 aceitações genuínas adicionais, mas elevou falsas aceitações para 123 e 130 em 7.200 comparações por condição; o máximo permitido é 72. O limiar selecionado foi 0,28339456518491113, calibrado somente no limpo. Permaneceram uma falha limpa/superior e duas inferiores. Não houve superioridade conjunta nem avanço à validação. A adaptação top3 e a correção espacial anteriores ainda têm melhor Rank-1 inferior que este piloto; não foi feita seleção entre métodos após este resultado para promover qualquer um.

**Decisão: não substituir o reconhecedor.** A inicialização resolveu a perda limpa do comparador local anterior, mas esta atenção limitada não resolveu a robustez sob oclusão nem a FMR. O resultado não prova que qualquer atenção seja inútil, nem identifica causalmente quais regiões causam o erro. Não será ajustado um limiar nas oclusões do monitor para promover o candidato rejeitado.

## Verificação e preservação

Dois testes passaram, cobrindo equivalência inicial com o descritor original, escopo dos parâmetros treináveis, invariância dos pesos congelados após atualização, restauração dos pesos de atenção, soma um e piso dos pesos regionais. O treino conferiu hashes dos pesos e buffers congelados antes/depois: permaneceram iguais.

A auditoria reconstruiu os descritores selecionados/finais sobre o encoder original e os mapas armazenados, reproduzindo exatamente escores, cossenos, seleção e bloqueio. Conferiu também a origem dos cadastros nas pessoas de ajuste. Não refez as oito épocas. Foram preservados 28 arquivos em 12 partes base64, ZIP de 550.588 bytes, incluindo pesos selecionados/finais, escores, cadastro, protocolo e código. O cache de 1,59 GB e os pesos originais não foram duplicados; são dependências identificadas por hash. A recuperação confere os hashes e permite reauditar decisões sem refazer as imagens. O envio ao OneDrive não foi verificado.

```powershell
.\executar.ps1 preservar_atencao_polar.py
.\executar.ps1 auditar_atencao_polar.py --root "$env:TEMP/pfc-atencao-restaurado-20261023"
```

Os 444/486 (91,36%) do teste principal e a fronteira de área anterior permanecem inalterados. Nenhum treino ou inferência foi feito na validação/teste neste piloto; não houve novo mínimo aprovado.
