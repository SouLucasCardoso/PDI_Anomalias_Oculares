# Liberação dos modelos DINOv3 e SAM 3.1

Os pesos oficiais são *gated*: o aceite é individual e precisa ser feito no
navegador pela mesma conta Hugging Face usada no computador. Não coloque o
token em scripts, commits, prints ou mensagens.

## 1. Solicitar acesso no navegador

1. Crie ou entre em uma conta pessoal em <https://huggingface.co/> e confirme o
   e-mail.
2. Abra o DINOv3 ViT-L/16:
   <https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m>.
3. Clique em **Agree and access repository** ou **Request access**.
4. Leia e aceite a licença. Se houver formulário, use informações acadêmicas
   verdadeiras, por exemplo: UniSatc, estudante/pesquisador, projeto acadêmico
   de segmentação e análise de imagens oculares, sem uso comercial.
5. Repita no SAM 3.1: <https://huggingface.co/facebook/sam3.1>.
6. Aguarde até a página de cada modelo mostrar que o acesso foi concedido.
   Solicitações manuais podem não ser aprovadas imediatamente.

O acesso é concedido ao usuário individual, não automaticamente à organização.

## 2. Criar um token somente de leitura

1. Abra <https://huggingface.co/settings/tokens>.
2. Clique em **Create new token**.
3. Nome sugerido: `pfc-modelos-meta`.
4. Escolha **Read**. Não é necessário token de escrita.
5. Copie o token `hf_...` uma única vez e não o salve no repositório.

## 3. Autenticar este projeto

Abra PowerShell na pasta `pfc1-segmentacao-mmu` e execute:

```powershell
$env:HF_HOME = (Resolve-Path "data/modelos/huggingface").Path
& "C:\Users\Lucas\pfc-sam3-venv\Scripts\python.exe" -c "from huggingface_hub import login; login()"
```

Cole o token quando o programa solicitar. A entrada não aparece na tela. Quando
perguntar sobre Git credentials, responda `n`; isso não é necessário para baixar
modelos.

## 4. Confirmar a liberação sem baixar os pesos grandes

```powershell
$env:HF_HOME = (Resolve-Path "data/modelos/huggingface").Path
& "C:\Users\Lucas\pfc-sam3-venv\Scripts\python.exe" verificar_acesso_meta.py
```

O resultado esperado para os dois modelos é `ACESSO OK`. Um `401` significa que
o login não foi feito nesse `HF_HOME` ou que o acesso ainda não foi concedido.
Um `403` normalmente significa que a conta autenticada não aceitou a licença.

## 5. Primeiro teste SAM 3.1 e imagem de resultados

Comece com quatro imagens para verificar memória e instalação:

```powershell
$env:HF_HOME = (Resolve-Path "data/modelos/huggingface").Path
& "C:\Users\Lucas\pfc-sam3-venv\Scripts\python.exe" avaliar_sam3_1_ubipr.py --limit 4
```

O comando baixa o checkpoint oficial na primeira execução e gera:

- `outputs/modelos_modernos/sam3_1_ubipr/metricas.json`;
- `outputs/modelos_modernos/sam3_1_ubipr/metricas_por_imagem.csv`;
- `outputs/modelos_modernos/sam3_1_ubipr/amostras_visuais.png`.

Depois do smoke test, remova `--limit` para avaliar toda a partição de teste.
O ambiente SAM foi colocado em `C:\Users\Lucas\pfc-sam3-venv` porque as DLLs
CUDA não carregam a partir do caminho longo do projeto no OneDrive. Como o SAM
3 tem 848 milhões de parâmetros e esta máquina possui GPU de 6 GB,
o script tenta CUDA primeiro e informa claramente se for necessário usar CPU.
