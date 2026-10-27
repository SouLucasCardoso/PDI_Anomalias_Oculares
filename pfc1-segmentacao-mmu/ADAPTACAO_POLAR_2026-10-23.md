# Adaptação do descritor polar — 23/10/2026

Foi concluído um piloto de adaptação à normalização com contorno externo corrigido. Houve melhora sob oclusão no monitor interno, mas nenhuma época preservou o desempenho limpo original. O candidato foi rejeitado antes de qualquer inferência de identidade na validação ou no teste. A referência principal permanece inalterada.

## Método e alcance

A U-Net, o corretor externo e o ResNet18 polar permaneceram congelados. Um adaptador residual de aproximadamente 99 mil parâmetros transforma as características de 512 dimensões e acrescenta uma correção limitada ao descritor de 256 dimensões. A padronização usa somente as fotos limpas do ajuste. O alvo é o descritor original da mesma foto limpa; a perda pondera as condições limpa/superior/inferior em 4/1/1. O treinamento usa FP32, AdamW, semente 63 e parada antecipada registrada.

Das 7.716 fotos do treino original, 6.665 de 167 pessoas foram elegíveis para ajuste; 91 foram excluídas apenas desse ajuste por indisponibilidade dos pares necessários. O monitor contém 960 fotos de 16 pessoas distintas, com 480 consultas da segunda sessão. Todas as consultas, inclusive falhas, permanecem nos denominadores. O cadastro da primeira sessão é sempre limpo, com comparação restrita ao lado informado. O limiar é calibrado na condição limpa de cada modelo e reaplicado às suas condições ocluídas.

O monitor é reutilizado e seus participantes já foram vistos pelos encoders congelados. Seus números descrevem desenvolvimento interno de **um único descritor polar**, não a fusão completa nem generalização independente.

## Resultados no monitor — 480 consultas

Os valores abaixo comparam o contorno corrigido sem adaptação à última época treinada (época 5), que foi **rejeitada**. Não representam um novo modelo aprovado.

| Condição | Rank-1 sem adaptação | Rank-1 época 5 rejeitada | TAR sem adaptação | TAR época 5 rejeitada | FMR época 5 |
|---|---:|---:|---:|---:|---:|
| Limpa | 471/480 (98,13%) | 476/480 (99,17%) | 477/480 (99,38%) | 477/480 (99,38%) | 0,9861% |
| Perda superior de 10% | 310/480 (64,58%) | 367/480 (76,46%) | 294/480 (61,25%) | 333/480 (69,38%) | 0,9861% |
| Perda inferior de 10% | 217/480 (45,21%) | 307/480 (63,96%) | 201/480 (41,88%) | 227/480 (47,29%) | 0,8056% |

O descritor original, antes da correção de contorno, obtém **479/480 tanto em Rank-1 como em TAR limpos (99,79%)** nesse monitor. A época 5 ainda perde três identificações e duas aceitações genuínas frente a esse controle. Portanto, os ganhos de 57 e 90 identificações nas oclusões não compensam a reprovação do controle limpo. Nenhuma das cinco épocas foi elegível; o checkpoint selecionado permanece na época zero, como controle, sem autorização de avanço à validação.

## Correção técnica e reprodução

Foi detectado um erro na primeira montagem do monitor: as condições ocluídas também modificavam o cadastro. Esses resultados foram invalidados antes de qualquer validação. A extração de características continuava válida e foi reaproveitada; o ajuste foi refeito com cadastro explicitamente limpo, sem mudança de hiperparâmetros. Um teste de regressão verifica essa condição. A execução válida é `adaptador_polar_cadastro_fixo_2026-10-23`; os registros anteriores ficam identificados como `technical_invalid_monitor` no pacote.

Passaram 13 testes direcionados. A auditoria reproduziu a separação entre pessoas, a padronização, os escores selecionados e a reprovação do critério. As cinco épocas foram reproduzidas com diferença máxima **zero** nas perdas registradas. Os pesos da última época rejeitada foram preservados com identificação explícita de rejeição, além do checkpoint da época zero.

## Preservação e recuperação

O pacote em `backups/adaptador_polar_2026-10-23` contém **40 arquivos em 24 partes**, ZIP de 1.124.760 bytes. O registro contém os hashes de cada arquivo e do ZIP. A restauração conferiu todos os hashes, os escores e as decisões do monitor, incluindo a época rejeitada. Os caches de características foram excluídos do pacote e registrados por hash; a recuperação compacta não recalcula características nem imagens.

```powershell
.\executar.ps1 preservar_adaptador_polar.py
.\executar.ps1 verificar_recuperacao_adaptador.py --restored-root "$env:TEMP/pfc-adaptador-restaurado-20261023"
```

Os registros legíveis estão em `outputs/adaptador_polar_cadastro_fixo_2026-10-23` e `outputs/adaptador_polar_cadastro_fixo_val_2026-10-23`. A preservação não exigiu alterar exceções do Defender. A conclusão do envio pelo OneDrive não foi verificada.

## Consequência para o estudo

Não há novo percentual mínimo. O teste original continua em **444/486 (91,36%) sem oclusão**; as fronteiras nominais anteriormente observadas permanecem 99,5% de área retida na perda superior e 99% na inferior, dentro da grade e dos critérios daquele protocolo. Esses números não medem a extensão clínica de uma anomalia ocular.

A hipótese de manter o descritor original e acrescentar a normalização corrigida foi posteriormente executada como combinação fixa, sem utilizar os pesos deste adaptador. Preservou o controle limpo, mas reprovou os critérios sob oclusão. Ver [piloto complementar](COMPLEMENTO_GEOMETRICO_2026-10-23.md). Não se deve relaxar o critério nem abrir o teste para promover este adaptador rejeitado.
