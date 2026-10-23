# Avaliação da configuração congelada — 21/10/2026

## Objetivo

Verificar a execução integrada do candidato que atingiu 90,04% de Rank-1 e 90,66% de TAR na validação e avaliar sua transferência ao subconjunto de teste UBIPr. Esta é uma avaliação adicional com configuração congelada, não um teste cego novo: o conjunto de teste já foi examinado por estratégias anteriores. A população de pré-treinamento dos pesos públicos ArcIris é desconhecida; não se pode excluir sobreposição com a base.

## Parâmetros fixos antes da avaliação

- Uma foto original por consulta; lado do olho informado corretamente.
- Cadastro com todas as capturas válidas da sessão 1; consultas da sessão 2, incluindo falhas.
- Dezesseis candidatos do mesmo lado e quinze comparações impostoras por consulta.
- Segmentação U-Net congelada e recortes RGB diretamente dos originais; faixa polar com geometria automática.
- Sete componentes com peso 1/8 cada; ArcIris com peso 1/8, dividido igualmente entre entrada com contraste local e entrada pelo canal vermelho. As duas entradas derivam da mesma foto.
- Médias e desvios de cada componente copiados de `outputs/candidato_congelado_2026-10-21/CONGELADO.json`, sem estimá-los novamente na avaliação.
- Normalização por consulta calculada apenas sobre seus dezesseis candidatos, sem rótulo de identidade e sem utilizar outras consultas.
- Limiar **0,8581747485460748**, sem recalibração no teste.
- Critério: Rank-1 ≥90%, TAR ≥90% e FMR ≤1%. A taxa conjunta de identificação correta e aceitação é relatada separadamente.

## Ordem e auditoria

1. Reexecutar a validação original a partir dos arquivos de imagem e dos checkpoints; comparar escores e decisões com o candidato salvo. Não selecionar parâmetros usando diferenças numéricas dessa repetição.
2. Após conferir a execução integrada, executar o teste com a mesma configuração. Registrar hashes dos checkpoints, implementação, quantidade de consultas, falhas e decisões.
3. Relatar diferenças entre desenvolvimento e teste. Não ajustar pesos, limiar ou filtros com base no teste para recuperar a meta.
4. O mínimo global de área só pode ser afirmado se a condição original satisfizer o critério e as condições de maior área também passarem na curva correspondente. O resultado de desenvolvimento sem oclusão não estabelece um mínimo.

O comparador usa rótulos de cadastro para formar os templates. Os rótulos das consultas participam apenas das métricas; não escolhem recortes, transformações, pesos, candidatos além do lado informado, ou limiar.

## Particularidade dos arquivos RGB

A primeira tentativa foi interrompida antes de inferir imagens por uma conferência de hash que confundiu o arquivo original de treino com a cópia do checkpoint da etapa automática. Os arquivos `.pt` têm hashes diferentes, mas todas as chaves e tensores do estado do modelo foram comparados e são exatamente iguais (zero tensores diferentes). A conferência foi corrigida para o hash do arquivo efetivamente usado na validação. Não houve alteração dos pesos.
