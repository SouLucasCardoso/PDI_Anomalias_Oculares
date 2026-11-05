# Preferências do projeto

- O usuário determinou em 03/11/2026: usar SAM 3 e, nas tecnologias adotadas, sempre a versão mais atual possível.
- Nos novos ensaios SAM, usar a versão oficial mais recente da família SAM 3, verificando repositório, checkpoint e revisão antes de registrar a rodada. SAM 2 e Iris-SAM ficam como referências e controles históricos.
- Preferir versões estáveis recentes e compatíveis entre si, com Windows e com a GPU disponível. Conferir fontes oficiais; registrar versões, revisões, hashes e qualquer restrição concreta que impeça uma atualização. Não presumir que o maior número publicado tenha build CUDA compatível.
- Preparar atualizações em ambiente separado e verificar dependências, CUDA e inferência antes de adotá-las. Não atualizar o ambiente ou as fontes de uma rodada ativa no meio da execução; concluir essa comparação com sua proveniência original e usar o ambiente atualizado nas novas rodadas.
- O objetivo científico permanece estimar a menor fração observada de íris visível que sustenta identificação sob controle de falsas correspondências. Melhora de Dice, recortes visuais ou oclusão sintética não demonstram, isoladamente, esse mínimo ou efeito clínico de anomalias.
