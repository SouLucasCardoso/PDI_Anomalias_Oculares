"""Atualiza o texto cientifico e prepara evidencias do modelo, sem inferencia."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,zipfile
from docx import Document
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();out=a.output_dir;out.mkdir(parents=True,exist_ok=True)
    ref=next(ROOT.parent.parent.glob('Modelo_artigo_Computacao*.docx'));d=Document(ref)
    with zipfile.ZipFile(ref) as z:parts={n:dict(bytes=len(z.read(n)),sha256=hashlib.sha256(z.read(n)).hexdigest()) for n in z.namelist()}
    (out/'template_parts.json').write_text(json.dumps(parts,indent=2),encoding='utf-8');shutil.copyfile(ref,out/'MODELO_REFERENCIA.docx')
    contract=f'''# Contrato do artigo UniSatc 27/10/2026
Referencia original: {ref}
SHA256: {hashlib.sha256(ref.read_bytes()).hexdigest()}
Referencia local imutavel: MODELO_REFERENCIA.docx; 11 paginas renderizadas e inspecionadas.
Inventario de componentes e hashes: template_parts.json.
Uma secao A4 retrato; 21,0009 x29,7004cm; margens superior/esquerda3,0004cm,inferior/direita2,0003cm.
Cabecalho/logotipo e campo PAGE superior direito preservados; comportamento de pagina inicial igual ao modelo.
Corpo estilo1Texto,Arial12,1,5linhas,justificado,recuo2cm; titulos primarios Heading1 maiusculo/negrito,secundarios Heading2 maiusculo semnegrito,terciarios Heading3 negrito.
Title centralizado/negrito; autores Assinaturas a direita com notas1/2 reais.
Resumo e palavras-chave estilos Resumo/Textodoresumo; notas Arial10.
Tabelas Arial10,largurasfixas em16cm,semgradevertical como exemplos do modelo,cabecalhorepetido,linhasnaoseparadas.
Legendas12 centralizadas acima; fontes10 abaixo; imagens derivadas dos resultados comcreditos; tres figuras planejadas.
Referencias4Referncias,Arial12,alinhamentoesquerda,simples,espaco24ptentreentradas; secao nao numerada fecha o documento,em variaspaginas se necessario.
Slots: corpo instrucional inteiro e tabelas/figuras de exemplo substituidos; title/body/authorfootnotes/settingsupdatefields e metadadoscore(editados para os autores do artigo) editaveis.
Preservarsomente:estilos,numeracao,tema,fontes,cabecalhos,rodapes,logotipo,sectPr e demais componentes opacos; inventariobinario conferido.
Edicoes permitidas no pacote:document.xml,document.xml.rels,ContentTypes,footnotes,settings,docProps/core.xml; novas imagens e suas relacoes.
Sem controlesdeconteudo ricos a preencher; exemplosinstrucionais/listadesimbolos removidos do corpo por nao integrarem o artigo.
Seções: Resumo,Introducao,ProcedimentosExperimentais comMateriais/Metodos,ResultadosDiscussao,ConsideracoesFinais,Referencias.
Formato 15a30paginas. Conteudo nativo editavel em paragrafos/tabelas/equacao; figuras raster representam evidencia e graficos.
Sem nova titulacao atribuida ao orientador; curso/emails informados pelo autor.
Nenhuma alegacao de minimo clinico universal; separar benchmark,monitor reutilizado e casos clinicos.
'''
    (out/'artifact.md').write_text(contract,encoding='utf-8')
    text=(ROOT/'artigo/ARTIGO_CONSOLIDADO_2026-10-23.md').read_text(encoding='utf-8')
    before,oldrefs=text.split('## REFERÊNCIAS',1)
    oldabstract=re.search(r'\*\*Resumo:\*\* (.+)',before).group(1)
    abstract='Este estudo investigou a menor fração nominal da região visível da íris que manteve critérios de identificação ocular sob oclusões digitais superiores e inferiores. Utilizou-se o UBIPr segmentado, com partições por pessoa, extração automática e fusão de representações RGB e polares. A avaliação entre sessões manteve uma fotografia por consulta, lateralidade informada e 16 candidatos do mesmo lado. Modelo, cadastro e limiar permaneceram congelados nas intervenções. Todas as 486 consultas de teste foram mantidas, incluindo falhas e seis referências sem área definida. Exigiram-se Rank-1 e aceitação genuína de pelo menos 90%, com falsa correspondência empírica de até 1%. Sem perda adicional, obtiveram-se 91,36%, 92,39% e 0,88%, respectivamente. Na grade irregular estudada, as menores áreas nominais aprovadas foram 99,5% na orientação superior e 99% na inferior. A perda de 10% produziu diferença de Rank-1 de 24,07 pontos percentuais entre orientações. Pilotos posteriores não superaram conjuntamente os critérios. Em extensão exploratória, nove imagens clínicas com alterações explícitas da íris foram examinadas; dois olhos permitiram quatro consultas. O sistema original não identificou corretamente nenhuma, enquanto um controle de escala recuperou uma consulta e prejudicou outro cadastro. A evidência delimita a tolerância do processamento completo e identifica falhas de transferência de captura, sem estabelecer mínimo anatômico universal ou efeito causal de doenças. A reutilização dos conjuntos e a pequena amostra clínica impedem confirmação independente.'
    before=before.replace(oldabstract,abstract)
    before=before.replace('Os objetivos específicos compreenderam organizar partições por pessoa e lateralidade, reconstruir a segmentação automática, definir e congelar o reconhecedor, aplicar intervenções de área conhecida e comparar as respostas das duas orientações.','Os objetivos específicos compreenderam organizar partições por pessoa e lateralidade, reconstruir a segmentação automática, congelar o reconhecedor, aplicar intervenções de área conhecida, comparar as orientações e examinar a extração e a identificação em um pequeno conjunto clínico complementar.')
    materials='''#### 2.1.3 Bases complementares e fontes técnicas

A preparação também contemplou o MMU e suas máscaras públicas, como etapa inicial de segmentação, sem diagnósticos por imagem no protocolo (Mohammad, s.d.; Kozlova, s.d.). Para dados clínicos, consultaram-se CatScreen, SLID, Nuclear Cataract e SLP-VLD, mantendo suas modalidades, licenças e identificadores separados (Khurshid et al., 2026; Xu et al., 2026; Cruz-Vega; Morales, 2023; Ignatowicz; Marciniak; Marciniak, 2025; Qian, 2026). A auditoria local encontrou 400 imagens na amostra CatScreen, 2.617 no SLID e 1.320 no Nuclear, das quais 335 tiveram rótulos recuperados da seleção secundária de 2025. As contagens são da cópia adquirida e não substituem as descrições dos depósitos. Nenhuma dessas fontes foi misturada ao UBIPr para fabricar controles saudáveis.

O SLP-VLD v3 contém 2.228 registros de fotografias de lâmpada de fenda e diagnósticos; a auditoria encontrou uma duplicata exata, preservada no inventário e removida das divisões que exigiam deduplicação. Os diagnósticos vieram das planilhas do depósito, não de respostas geradas por modelos de linguagem. A triagem literal de termos relacionados à íris selecionou nove imagens distintas de oito olhos codificados. Seis olhos só possuíam uma captura disponível; dois tinham capturas repetidas elegíveis no manifesto clínico anterior. As imagens e descrições são dados públicos com licença CC BY 4.0 registrada pelos autores (Qian, 2026); não se realizou novo diagnóstico ou exame médico.

Na triagem de ferramentas, foram consultados SAM, SAM 2, SAM 3 e OpenIRIS, além do Iris-SAM para segmentação especializada (Kirillov et al., 2023; Meta AI, s.d.a; Meta AI, s.d.b; Worldcoin, s.d.; Farmanifard; Ross, 2024). Esses recursos não substituíram a U-Net no sistema de referência. Seus testes locais de execução ou viabilidade não equivalem a validação biométrica clínica. Os repositórios foram tratados como fontes de implementação e pesos, e não como garantia de desempenho transferível ao UBIPr ou ao SLP-VLD.

'''
    before=before.replace('### 2.2 MÉTODOS',materials+'### 2.2 MÉTODOS')
    methods='''#### 2.2.6 Pilotos posteriores e separação da calibração

Os ajustes posteriores usaram 151 pessoas do treino para gradientes ou estimação de parâmetros, 16 para calibração interna e 16 do monitor antigo para avaliação após congelamento. Os encoders anteriores já haviam visto essas pessoas; a separação desta etapa não transforma o monitor reutilizado em teste independente. No reteste com oclusões diversas, mantiveram-se 6.067 fotografias e 3.222 intervenções superiores/inferiores sorteadas de 1% a 20%, com níveis de cinza fixados antes do treino. Dez vistas com falha de extração tiveram sua contribuição nas perdas de identidade zerada; o peso das demais e os denominadores de avaliação foram preservados. Executaram-se oito épocas, selecionadas pela perda de ajuste com preservação do limpo interno.

O piloto estrutural aprendeu oito regressões regionais ridge, uma por setor angular do mapa polar intermediário, para aproximar o descritor global limpo da mesma foto de ajuste. A regularização de 0,01 e a fusão de 75% global e 25% regional foram fixadas previamente. Compararam-se seis das oito maiores concordâncias por par, com controle usando todos os setores. A comparação por regiões possui precedentes, mas este piloto não reproduz o método de saliência humana estudado em imagens pós-morte por Boyd et al. (2023). Os setores têm campos receptivos sobrepostos e não representam porcentagens isoladas da área física da íris.

Cada método recebeu um único limiar a partir do grupo interno limpo, visando FMR empírica de 0,5%, aplicado sem alteração ao monitor. A barreira de avanço exigiu preservar a condição limpa e melhorar Rank-1 e TAR nas duas oclusões, mantendo FMR de até 1%. Os controles foram reportados sem escolher retrospectivamente o melhor resultado e sem calibrar sobre os casos ocluídos do monitor. Essas rodadas são desenvolvimento complementar e não entram na estimação da fronteira principal.

#### 2.2.7 Estudo complementar de casos clínicos

Dos oito olhos com diagnóstico explícito da íris, dois possuíam capturas repetidas no manifesto clínico previamente preparado: um olho com cisto de íris e alterações corneanas, e um com laceração da íris e acompanhamentos após tratamento. A primeira captura de cada olho foi cadastro e as quatro capturas posteriores foram consultas. Datas e identidade provêm dos códigos distribuídos; não foram confirmadas por prontuário independente. O cadastro de cada lado incluiu o olho alvo e os primeiros 15 outros olhos elegíveis, ordenados por código e nome de arquivo, sem seleção por qualidade ou escore. Ao todo, processaram-se 42 fotografias: 32 de cadastro, quatro consultas e seis casos adicionais sem cadastro elegível.

A fusão principal e o limiar UBIPr foram transportados sem ajuste, mantendo as falhas no denominador. A avaliação clínica anterior já havia exposto esse domínio e as capturas; não se considera esta extensão um teste cego. Após inspecionar as falhas originais, registrou-se um controle posterior de escala: a foto clínica foi reduzida para 106 × 80 pixels dentro de uma entrada 320 × 240 preenchida com cinza 128. A máscara foi mapeada de volta ao original, de onde vieram os pixels do recorte. Não houve reconstrução de textura, treino ou busca entre escalas. O controle alterou somente a apresentação à U-Net e foi executado também sobre os cadastros.

Registraram-se pixels previstos como íris, razão entre máscara e fotografia e fração de suporte da grade polar estimada. Nenhuma dessas medidas foi tratada como porcentagem anatômica preservada. Sem máscara clínica de referência, não se calculou Dice clínico. Duas imagens com rótulo exato Normal eye foram selecionadas por ordem de arquivo e pessoas distintas para ilustração, sem medir seu reconhecimento nessa prancha. A ausência de diagnóstico no UBIPr não foi interpretada como ausência de anomalias.

'''
    before=before.replace('## 3 RESULTADOS E DISCUSSÃO',methods+'## 3 RESULTADOS E DISCUSSÃO')
    later='''Além dos controles geométricos, o reteste de oito épocas com vistas inválidas corrigidas preservou 479/480 identificações e aceitações no monitor limpo. Sob perda superior/inferior de 10%, o Rank-1 foi 82,71%/65,42%, o TAR foi 79,38%/57,92% e a FMR foi 1,3333%/1,2639%. A correção eliminou um alvo de treinamento inadequado, mas não produziu superioridade conjunta e não recebeu nova avaliação no teste principal.

Na destilação regional, a fusão primária preservou os mesmos acertos limpos e reduziu a FMR ocluída para 0,9167%/0,8472%. O Rank-1 foi 82,71%/61,88%, porém o TAR caiu para 75,63%/51,46%, contra 76,88%/53,96% do componente global original nessa rodada. O controle com todos os setores teve Rank-1 idêntico, impedindo atribuir a redução de FMR exclusivamente ao descarte regional. Portanto, atingir FMR abaixo de 1% em um monitor não resolveu a meta de identificação e aceitação genuína. Nenhum desses pilotos foi promovido.

### 3.6 CASOS CLÍNICOS E TRANSFERÊNCIA DE CAPTURA

A Tab. 6 resume as quatro consultas de dois olhos, com 16 candidatos nominais por lado e o limiar da referência. O sistema original não produziu identificação correta ou aceitação genuína. Uma comparação genuína estava indisponível porque a máscara do cadastro do olho com cisto ficou vazia. No outro olho, o cadastro era computacionalmente disponível, mas as máscaras extraíam fragmentos pequenos. O resultado não mede exclusivamente discriminação da textura e não demonstra efeito causal da condição ocular.

Tabela 6 — Extensão clínica com pesos e limiar congelados

| Processamento | Identificações corretas | Aceitações genuínas | Falsas correspondências | Genuínos indisponíveis |
|---|---:|---:|---:|---:|
| Original | 0/4 | 0/4 | 1/60 (1,67%) | 1/4 |
| Controle de escala 1/3 | 1/4 | 1/4 | 2/60 (3,33%) | 3/4 |

Fonte: do autor (2026), dados SLP-VLD. Controle definido após a falha original; mesmas consultas, cadastros e limiar. As quatro consultas não são quatro pessoas independentes.

O controle de escala recuperou o cadastro do olho com cisto e sua consulta foi identificada e aceita, com escore genuíno de 0,87538, superior ao limiar 0,85817. Entretanto, a máscara de cadastro do olho com laceração tornou-se vazia, indisponibilizando as outras três comparações genuínas. Não se escolheu a melhor escala por olho nem se excluíram falhas para reportar ganho. Uma falsa correspondência já representa 1,67% em 60 pares; a amostra não sustenta uma garantia populacional de FMR de até 1%.

A Fig. 3 apresenta controles com rótulo Normal eye e casos com alterações da íris na mesma base. A U-Net original produz recortes fragmentados também nos exemplos normais. Isso evidencia um confundidor de domínio de captura, sem provar que a escala explique todas as falhas. A melhora visual de alguns recortes não foi convertida em Dice ou percentual anatômico, pois falta anotação independente. O cadastro com laceração ilustra a falha do controle, preservando resultados favoráveis e desfavoráveis.

Figura 3 — Recortes de olhos rotulados como normais e com alterações da íris

![Recortes clínicos](figuras/recortes_clinicos.png)

Fonte: adaptação do autor (2026) de Qian (2026), SLP-VLD v3, CC BY 4.0. De cima para baixo: dois rótulos Normal eye, cisto de íris com comorbidades e laceração da íris. Colunas: fotografia, recorte original e controle de escala 1/3. Não se realizou novo diagnóstico médico.

O estudo de patologias de Trokielewicz, Czajka e Maciejewicz (2015) destaca a importância da segmentação para a confiabilidade do reconhecimento. Os casos presentes são compatíveis com a necessidade de examinar essa etapa, mas não reproduzem a população, a modalidade ou os reconhecedores daquele trabalho. As condições clínicas coexistem com diferenças de dilatação, iluminação, enquadramento, tratamento e qualidade; não se atribui toda discrepância de reconhecimento à doença.

Também se reaproveitaram as 482 consultas UBIPr de validação para descrever suporte polar natural, sem nova inferência de reconhecimento. Houve um acerto e aceitação em uma consulta com suporte de 47,36%; abaixo de 75%, porém, eram apenas cinco consultas, das quais três identificadas. Esses casos não estabelecem um mínimo global: suporte da grade polar, área nominal de intervenção e área anatômica são grandezas distintas. A seleção ilustrativa por suporte não substitui a análise de todas as consultas.

'''
    before=before.replace('### 3.6 LIMITAÇÕES E RELAÇÃO COM ANOMALIAS OCULARES',later+'### 3.7 LIMITAÇÕES E RELAÇÃO COM ANOMALIAS OCULARES')
    before=before.replace('A relação com anomalias oculares deve ser interpretada como motivação e hipótese de aplicação.','A relação com anomalias oculares permanece exploratória, apesar da extensão com casos rotulados. O número de olhos repetidos e as falhas de cadastro impedem uma estimativa clínica geral.')
    before=before.replace('Como continuidade, recomenda-se avaliar participantes e capturas novos, com referência anatômica independente, e separar a perda de informação da instabilidade geométrica.','A extensão clínica mostrou um cadastro recuperado por controle de escala e outro prejudicado, sem aprovação de uma variante geral. Assim, a máscara predita não pode servir como denominador de tecido preservado antes de sua validação clínica. Como continuidade, recomenda-se avaliar participantes e capturas novos, com referência anatômica independente, e separar a perda de informação da instabilidade geométrica.')
    refs=[x.strip() for x in oldrefs.strip().split('\n\n') if x.strip()]
    refs.extend([
      'BOYD, Aidan et al. Human Saliency-Driven Patch-Based Matching for Interpretable Post-Mortem Iris Recognition. In: IEEE/CVF Winter Conference on Applications of Computer Vision Workshops, 2023. p. 701–710. Disponível em: https://openaccess.thecvf.com/content/WACV2023W/XAI4B/html/Boyd_Human_Saliency-Driven_Patch-Based_Matching_for_Interpretable_Post-Mortem_Iris_Recognition_WACVW_2023_paper.html. Acesso em: 27 out. 2026.',
      'CRUZ-VEGA, Israel; MORALES, Hans Israel. Nuclear Cataract Database for Biomedical and Machine Learning Applications. Mendeley Data, versão 2, 2023. Conjunto de dados. DOI: 10.17632/6wv33nbcvv.2. Disponível em: https://data.mendeley.com/datasets/6wv33nbcvv/2. Acesso em: 27 out. 2026.',
      'FARMANIFARD, Parisa; ROSS, Arun. Iris-SAM: Iris Segmentation Using a Foundation Model. arXiv:2402.06497, 2024. Código e pesos dos autores. Disponível em: https://arxiv.org/abs/2402.06497. Repositório: https://github.com/ParisaFarmanifard/Iris-SAM. Acesso em: 27 out. 2026.',
      'IGNATOWICZ, Alicja Anna; MARCINIAK, Tomasz; MARCINIAK, Ewa. AI-Powered Mobile App for Nuclear Cataract Detection. Sensors, v. 25, n. 13, artigo 3954, 2025. DOI: 10.3390/s25133954. Disponível em: https://doi.org/10.3390/s25133954. Acesso em: 27 out. 2026.',
      'KHURSHID, Mahapara et al. CatScreen: A Large MultiModal Benchmark Dataset for Cataract Screening. Transactions on Machine Learning Research, 2026. Página e amostra dos autores. Disponível em: https://www.iab-rubric.org/resources/healthcare-datasets/catscreen. Acesso em: 27 out. 2026.',
      'KIRILLOV, Alexander et al. Segment Anything. In: IEEE/CVF International Conference on Computer Vision, 2023. Disponível em: https://arxiv.org/abs/2304.02643. Código: https://github.com/facebookresearch/segment-anything. Acesso em: 27 out. 2026.',
      'KOZLOVA, Julia. Masks for MMU Iris dataset. Repositório de máscaras, [s.d.]. Disponível em: https://github.com/jkozlova/Masks-for-MMU-Iris-dataset. Acesso em: 27 out. 2026.',
      'META AI. SAM 2. Repositório oficial de código e modelos, [s.d.a]. Disponível em: https://github.com/facebookresearch/sam2. Acesso em: 27 out. 2026.',
      'META AI. SAM 3. Repositório oficial de código e modelos, [s.d.b]. Revisão local registrada: 7f473cfd983d5eb43040ff608f66bff0d7bdcb53. Disponível em: https://github.com/facebookresearch/sam3. Acesso em: 27 out. 2026.',
      'MOHAMMAD, Naureen. MMU Iris Dataset. Kaggle, [s.d.]. Cópia de aquisição utilizada no projeto. Disponível em: https://www.kaggle.com/datasets/naureenmohammad/mmu-iris-dataset. Acesso em: 20 out. 2026.',
      'QIAN, Hulei. SLP-VLD: An Anonymized Slit-Lamp Image Dataset with Expert Clinical Reports for Vision-Language Modeling of Anterior Segment Diseases. Figshare, versão 3, 2026. Conjunto de dados. DOI: 10.6084/m9.figshare.32576697.v3. Disponível em: https://doi.org/10.6084/m9.figshare.32576697.v3. Acesso em: 20 out. 2026.',
      'WORLDCOIN. Open Iris Recognition Inference System. Repositório oficial OpenIRIS, [s.d.]. Disponível em: https://github.com/worldcoin/open-iris. Acesso em: 27 out. 2026.',
      'XU, Mingyu et al. SLID: a slit-lamp image dataset for deep learning-based anterior eye anatomical segmentation and multi-lesion detection. Frontiers in Digital Health, v. 7, artigo 1716501, 2026. DOI: 10.3389/fdgth.2025.1716501. Disponível em: https://doi.org/10.3389/fdgth.2025.1716501. Dados: https://github.com/xumingyu-hub/SLID. Acesso em: 27 out. 2026.'
    ])
    before=before.replace('Os roteiros registraram configurações, partições, históricos e hashes de arquivos.','Os roteiros registraram configurações, partições, históricos e hashes de arquivos. O relato explicita partições, seleção de modelos, falhas e limitações de generalização, aspectos recomendados para transparência em estudos de inteligência artificial com imagens médicas (Tejani et al., 2024), sem declarar aderência integral ou validação clínica pelo checklist.')
    refs=[r.replace('KOZLOVA, Julia.','KOZLOVA, J.').replace('MARCINIAK, Ewa.','MARCINIAK, E.') for r in refs]
    refs.append('TEJANI, Ali S. et al. Checklist for Artificial Intelligence in Medical Imaging (CLAIM): 2024 Update. Radiology: Artificial Intelligence, v. 6, n. 4, artigo e240300, 2024. DOI: 10.1148/ryai.240300. Disponível em: https://doi.org/10.1148/ryai.240300. Acesso em: 27 out. 2026.')
    refs.sort(key=lambda s:s.upper())
    final=before.rstrip()+'\n\n## REFERÊNCIAS\n\n'+'\n\n'.join(refs)+'\n'
    (out/'ARTIGO_CONSOLIDADO_2026-10-27.md').write_text(final,encoding='utf-8')
    # Article-sized figure: three columns, four rows, readable at16cm.
    figure=ROOT.parent/'Relatórios-de-Avanço/COMPARACAO_RECORTES_NORMAL_ANOMALIA_2026-10-27.png';src=Image.open(figure).convert('RGB');canvas=Image.new('RGB',(1200,1160),'white');draw=ImageDraw.Draw(canvas);font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
    for x,title in zip([20,420,820],['Fotografia','Recorte original','Controle de escala']):draw.text((x,8),title,font=font(30),fill='black')
    labels=['a) Normal eye','b) Normal eye','c) Cisto de íris e comorbidades','d) Laceração da íris e comorbidades']
    for k,label in enumerate(labels):
        y=155+260*k;target_y=60+275*k;draw.text((20,target_y),label,font=font(26),fill='black')
        for tx,sx,sw in [(20,25,395),(420,795,235),(820,1405,365)]:
            crop=src.crop((sx,y+32,sx+sw,y+32+195));canvas.paste(ImageOps.pad(crop,(365,230),color='white'),(tx,target_y+35))
    (out/'figuras').mkdir(exist_ok=True);canvas.save(out/'figuras/recortes_clinicos.png')
    (out/'atualizacao_texto.json').write_text(json.dumps(dict(references=len(refs),words=len(final.split()),source_sha256=hashlib.sha256((ROOT/'artigo/ARTIGO_CONSOLIDADO_2026-10-23.md').read_bytes()).hexdigest(),no_new_experiments=True),indent=2),encoding='utf-8')
    print(json.dumps(dict(references=len(refs),words=len(final.split()),manuscript=str(out/'ARTIGO_CONSOLIDADO_2026-10-27.md'))))

if __name__=='__main__':main()
