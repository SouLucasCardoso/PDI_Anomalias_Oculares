# Controle da segmentação e geometria — 21/10/2026

## Questão

Quanto da queda observada sob oclusão está associado à resposta da segmentação, caixa de recorte e normalização polar, além da mudança da textura e do contraste?

## Comparação fixa

Comparar as condições de oclusão superior e inferior de10% já avaliadas no teste com a mesma intervenção, mesmos checkpoints, médias, desvios, normalização por consulta e limiar, fixando a máscara prevista sobre a foto original não ocluída. A caixa RGB, as elipses e o suporte polar dependem dessa máscara original. Os pixels da foto alterada continuam sendo usados no reconhecimento; a CLAHE é recalculada sobre eles.

As condições foram escolhidas por simetria da perda nominal de área, não para selecionar um modelo. Nenhuma combinação, checkpoint ou limiar será escolhido usando o resultado deste diagnóstico. As diferenças são pareadas por consulta e relatadas com bootstrap de pessoas, sem atribuir causalmente tudo à geometria das elipses: também muda o suporte de máscara e a caixa RGB.

## Limites

- É um controle posterior aos resultados do teste, não uma nova confirmação independente.
- A máscara original prevista exige acesso à versão não ocluída da mesma foto. Portanto, não é uma melhoria utilizável na identificação com uma foto ocluída única e não substitui o resultado operacional do candidato.
- Todas as486 consultas são preservadas; seis referências de área vazias permanecem sem intervenção.
- A anotação define somente os pixels cinza da intervenção, nunca a máscara ou a geometria do extrator.
- O efeito da textura, CLAHE, interação com os descritores e segmentação não é totalmente isolado por dois braços.
- O pré-treinamento externo permanece de população desconhecida.

O protocolo JSON de cada execução fixa hashes e parâmetros antes da inferência. O primeiro registro de geometria fixa contém uma descrição genérica de intervenção herdada da avaliação operacional; o campo explícito `geometry_scope` e a opção `fixed_geometry_diagnostic` especificam a exceção correta: a U-Net recebe a imagem original, e o reconhecedor recebe a imagem alterada. A implementação preservada em `source.py` registra esse comportamento. Uma errata separada esclarecerá a descrição genérica sem modificar o registro original.

## Uso posterior

Se fixar a segmentação/geometria recuperar desempenho, investigar sua estabilização com treino e validação. Se não recuperar, priorizar descritores locais e aprendizado com oclusão, também usando apenas treino e validação. Não retreinar ou recalibrar com base nos rótulos do teste deste diagnóstico.
