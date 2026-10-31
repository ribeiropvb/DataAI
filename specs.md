# DataAI — Especificação consolidada da aplicação

**Arquivo:** `specs.md`  
**Versão do documento:** 1.4  
**Data da consolidação:** 24/10/2026 (revisões 1.2, 1.3 e 1.4 em 31/10/2026)  
**Idioma:** português  
**Base:** decisões e artefatos discutidos nesta conversa até a solicitação desta especificação.

## 1. Como interpretar esta especificação

Este documento é referência para implementação e validação do DataAI. Os identificadores servem para localizar requisitos, regras, critérios e pendências; não representam tabelas, campos de banco ou códigos de funções a criar.

### 1.1. Situação das decisões

| Situação | Significado | Consequência para a implementação |
|---|---|---|
| **Confirmado** | Decisão explicitamente estabelecida pelo usuário, incluindo suas correções mais recentes. | Compõe a base obrigatória do produto. |
| **Referência existente** | Comportamento ou contrato documentado nos arquivos de skills produzidos, sem ratificação individual de todos os detalhes técnicos. | Deve ser considerado para aproveitar os artefatos existentes; não significa escolha definitiva de arquitetura ou aprovação de uma sugestão de produto. |
| **Proposto, não confirmado** | Sugestão apresentada pelo assistente que não recebeu decisão expressa. | Não deve ser tratada como requisito aprovado. |
| **Em aberto** | Não há informação suficiente para definir o comportamento. | Resolver a pendência antes de implementar a parte afetada ou documentar uma decisão posterior. |

Requisitos RF, regras RN e critérios CA das seções 6, 7 e 15 representam a base **confirmada**. Detalhes provenientes apenas das skills ou de propostas estão separados e identificados.

### 1.2. Precedência e fontes

1. Instruções mais recentes do usuário prevalecem sobre decisões anteriores incompatíveis.
2. Exemplos de análise não criam regras universais da aplicação.
3. O conteúdo gerado pelo assistente não equivale, por si só, a aprovação do usuário.
4. Lacunas são registradas na seção 16, sem decisões presumidas.

Fontes utilizadas na consolidação e documentos de apoio:

| Fonte | Uso neste documento |
|---|---|
| Histórico desta conversa | Escopo, público, formatos, modos de análise, revisão crítica e conservação do histórico. |
| `DatAI_Definicao_MVP.pdf`, versão 0.2, de 24/10/2026 | Documento complementar atualizado com CSV/Excel, múltiplos temas, dois modos de análise, histórico e revisão crítica. Substitui a versão 0.1, de 02/10/2026, consultada na consolidação original. O PDF sintetiza esta especificação e não acrescenta requisitos. |
| `DataAI_Skills_MVP.zip`, pacote `dataai-skills` versão `3.0.0` | Nomes de skills, perfis, contratos e critérios técnicos existentes. Não constitui aplicação implantada. |
| Demonstração com `ecommerce.rar` | Exemplo de uso com múltiplos CSVs relacionados. Não define o domínio nem fixa métricas do produto. |
| Revisão recente do negócio | Inclusão de Excel, caráter multidomínio, público inicial e futuro, dois modos de análise e histórico expressamente aprovado. |

O `specs.md` é a referência detalhada de requisitos e decisões. O PDF atualizado é um documento de apresentação do MVP; não é necessário consultá-lo para interpretar os requisitos abaixo. O pacote de skills contém procedimentos operacionais completos para quem optar por reaproveitá-los. A base `ecommerce.rar` é opcional para reproduzir aquele teste.

## 2. Visão geral

O DataAI é uma aplicação de análise de dados assistida por IA, organizada com agentes especializados e skills. O usuário envia um ou mais arquivos tabulares, informa uma pergunta ou solicita exploração geral e recebe relatório PDF, dashboard HTML ou as duas modalidades de entrega.

O problema atendido é permitir que uma pessoa obtenha análises descritivas, visualizações e achados sobre seus dados sem precisar programar. O público inicial conhece seu negócio ou seus dados, mas não necessariamente as ferramentas de análise. A intenção de evolução é atender também analistas que desejam acelerar seu trabalho.

O produto é multidomínio: não está limitado a e-commerce. O assunto das análises depende dos arquivos e do contexto do pedido. Educação, operações e outros temas citados servem como exemplos, não como módulos verticais já especificados.

O sistema deve considerar relações entre tabelas quando elas fizerem parte da análise. A existência de vários arquivos não determina, sozinha, uma união entre eles.

**Revisão 1.3 (confirmado pelo usuário):** as métricas não se limitam a posição e dispersão. Elas devem ser abrangentes o suficiente para apoiar tomadas de decisão e aceitar insumos de origens e fontes diferentes. As tabelas nem sempre estarão em um único arquivo: uma mesma tabela pode vir dividida em vários arquivos e várias tabelas podem estar relacionadas entre arquivos. O sistema deve descobrir essas ligações a partir dos próprios dados, com evidência (seções 12.7 e 12.8).

## 3. Escopo

### 3.1. Funcionalidades confirmadas para a primeira versão

- Recebimento de um ou mais arquivos CSV ou Excel.
- Análise direcionada por pergunta do usuário.
- Exploração geral dos dados sem exigir uma pergunta específica.
- Análises descritivas e identificação de achados sobre os dados.
- Métricas abrangentes e orientadas à decisão, além de posição e dispersão (RF-022, seção 12.7).
- Tabelas distribuídas em vários arquivos ou abas, com descoberta automática das ligações entre eles (RF-023, RF-024, seção 12.8).
- Insumos de origens diferentes, com rastreabilidade e reconciliação (RF-025).
- Análise de conjuntos de arquivos relacionados, sem restringir o produto a um arquivo ou a uma tabela.
- Geração de relatório PDF com interpretação dos resultados.
- Geração de dashboard HTML sem narrativa interpretativa.
- Uso de gráficos e atenção explícita à apresentação visual.
- Revisão crítica das entregas por agente responsável por localizar problemas e direcionar correções.
- Conservação dos arquivos utilizados, do pedido, dos esclarecimentos, das definições das métricas, dos tratamentos e das versões dos resultados e das entregas.
- Organização de skills temáticas com `SKILL.md`.

### 3.2. Evolução pretendida, ainda sem detalhamento funcional

Atendimento também a analistas. Não foram aprovadas funcionalidades específicas de modo avançado, edição de código, parametrização estatística detalhada ou configuração manual de agentes para esse público. Ver P-015.

### 3.3. Funcionalidades não especificadas ou propostas para fora do MVP

O documento inicial propôs deixar de fora treinamento de modelos preditivos, testes de hipóteses, inferência causal, conexões diretas a bancos e sistemas externos, atualização recorrente e criação de aplicação independente para cada dashboard. Essa lista foi apresentada como **escopo proposto**, não como conjunto de exclusões individualmente aprovado.

A base implementável consolidada nesta versão cobre análise descritiva. Não há requisito confirmado que obrigue implementar essas capacidades adicionais, nem decisão que as proíba em toda evolução futura. Ver P-014.

Também não estão definidos: cobrança, assinatura, compartilhamento público, colaboração entre usuários, edição manual das entregas, agendamentos e publicação automática de dashboards.

## 4. Perfis de usuário e permissões

| Perfil | Situação | Comportamento definido |
|---|---|---|
| Pessoa de negócio que conhece seus dados e não programa | Confirmado como público inicial | Deve conseguir apresentar arquivos e sua intenção sem escrever código. |
| Analista que deseja acelerar análises | Confirmado como público futuro | Sua inclusão deve ser considerada na evolução; controles específicos não foram definidos. |

Esses perfis descrevem públicos, não papéis de autorização. Não foram estabelecidos administrador, gestor, organização, empresa, níveis de acesso, autenticação ou regras de compartilhamento.

Agentes especializados e orquestrador são componentes do processamento, não perfis de usuários humanos. A aprovação de qualidade pelo orquestrador não equivale a uma permissão de acesso ao arquivo.

**Lacuna que afeta a produção:** a aplicação não tem modelo de identidade e autorização acordado. Ver P-006.

## 5. Conceitos e glossário

| Termo | Definição neste projeto |
|---|---|
| Solicitação de análise | Pedido do usuário associado aos arquivos e à intenção de análise. Não é o nome de uma tabela já aprovada. |
| Análise direcionada | Execução orientada por uma pergunta específica fornecida pelo usuário. |
| Exploração geral ou varredura | Exame dos dados para identificar achados pertinentes, mesmo sem pergunta específica inicial. |
| Análise descritiva | Resumo e organização de observações, distribuições, frequências, medidas e agrupamentos. Não estabelece, por si só, causalidade ou previsão. |
| Achado ou insight | Observação identificada a partir dos resultados da análise, acompanhada de sua interpretação quando houver entrega textual. Não é uma conclusão inventada para preencher o relatório. |
| Arquivo | Unidade enviada pelo usuário, como CSV ou planilha Excel. |
| Aba | Divisão de uma planilha Excel. A regra de seleção e identificação de tabelas por aba ainda está em aberto. |
| Dataset ou tabela de trabalho | Conjunto tabular usado pelo processamento. No pacote de skills, possui identificação e referência à origem. Não é sinônimo obrigatório de arquivo. |
| Unidade de observação | O que uma linha representa: por exemplo, uma pessoa, um evento, um item ou um agregado. |
| Relação entre tabelas | Vínculo usado para combinar informações, cuja interpretação depende das chaves e da unidade de observação. |
| Cardinalidade | Quantidade de correspondências entre chaves de duas tabelas, como um para um ou um para muitos. |
| Chave composta | Combinação de duas ou mais colunas que, juntas, identificam uma linha (por exemplo, pedido + item). |
| Integridade referencial | Grau em que os valores de uma chave estrangeira encontram correspondência na tabela referenciada. Valores sem correspondência são **órfãos**. |
| Partição | Parte de uma mesma tabela entregue em arquivo ou aba separada (por exemplo, um arquivo por mês ou por filial). Partições são **empilhadas**, não juntadas. |
| Empilhamento (união) | Concatenação de linhas de partições com o mesmo esquema, mantendo a identificação do arquivo de origem de cada linha. |
| Junção | Combinação de colunas de tabelas diferentes por meio de uma chave. |
| Papel da tabela | Classificação descritiva de uma tabela no conjunto: fato (eventos com medidas), dimensão (cadastro), ponte (liga duas tabelas em muitos para muitos), agregada (granularidade mais grossa), referência ou isolada. |
| Grão | Nível de detalhe de uma tabela, equivalente à sua unidade de observação. Juntar tabelas de grãos diferentes exige agregar antes. |
| Fan-out (multiplicação) | Aumento indevido de linhas ao juntar tabelas, que faz medidas serem somadas mais de uma vez. |
| Linhagem (origem) | Registro de quais arquivos, abas, colunas e tratamentos produziram um dataset ou resultado. |
| Reconciliação | Comparação de uma mesma medida ou entidade presente em fontes diferentes para medir cobertura e divergência. |
| Família de métricas | Grupo do catálogo da seção 12.7 (qualidade, composição, concentração, tendência etc.). |
| Referência (benchmark) | Valor contra o qual um resultado é comparado: meta, período anterior, média geral, outro grupo ou outra fonte. |
| Métrica | Medida definida para uma análise. Seu significado, cálculo e tratamentos devem ser conservados no histórico. |
| Tratamento | Conversão ou transformação aplicada aos dados para uma análise. As condições para execução autônoma ainda não foram aprovadas. |
| Resultado | Valor, tabela ou estrutura produzida pelo processamento dos dados. |
| Entrega ou artefato final | Arquivo efetivamente produzido para o usuário: relatório PDF ou dashboard HTML. |
| Relatório | PDF que apresenta interpretação, resultados e encadeamento analítico; pode incluir gráficos e tabelas. |
| Dashboard | HTML para apresentar e explorar indicadores e visualizações, sem narrativa interpretativa. |
| Skill | Instruções especializadas, recursos e critérios usados para orientar uma tarefa; não é uma função executável nem um agente automaticamente instalado. |
| Agente | Papel especializado que utiliza instruções e ferramentas para executar tarefas. |
| Orquestrador de qualidade | Agente que examina entregas finais, identifica defeitos, encaminha correções aos responsáveis e verifica o resultado corrigido. |
| Storytelling analítico | Organização coerente de pergunta ou objetivo, evidências, interpretação e limites, permitindo acompanhar o raciocínio do relatório. Não autoriza alterar números para compor uma narrativa. |
| Versão | Registro de uma determinada forma de um resultado ou entrega. Sua representação técnica ainda não está definida. |

## 6. Funcionalidades e requisitos funcionais confirmados

### RF-001 — Receber arquivos CSV

A aplicação deve aceitar um ou mais arquivos CSV como entrada de uma análise. A interface e o processamento não podem limitar o caso de uso a um único CSV. Limites quantitativos e convenções de leitura estão em P-002.

### RF-002 — Receber arquivos Excel

A aplicação deve aceitar arquivos Excel como entrada de análise. Extensões, versões e estruturas de planilha suportadas não foram definidas; não se deve presumir suporte já implementado a `.xls`, `.xlsx` ou `.xlsm`. Ver P-001.

### RF-003 — Trabalhar com diferentes temas

As funções centrais devem operar sobre arquivos de temas diferentes. Regras e métricas próprias de e-commerce não podem ser impostas a todos os arquivos. Relaciona-se a RN-001.

### RF-004 — Receber uma pergunta específica

A aplicação deve permitir que o usuário descreva, em linguagem natural, uma pergunta sobre os dados enviados e solicite uma análise voltada a respondê-la.

### RF-005 — Receber pedido de exploração geral

A aplicação deve permitir que o usuário solicite uma varredura dos dados e obtenha achados sem precisar formular uma pergunta específica. A ausência de pergunta específica não é motivo suficiente para rejeitar esse modo.

### RF-006 — Executar análises descritivas

A aplicação deve produzir análises descritivas compatíveis com os dados e o objetivo. Não foi exigido gerar todas as estatísticas em toda solicitação. A seleção detalhada e as convenções estatísticas existentes nas skills estão na seção 12.4.

### RF-007 — Considerar relações entre tabelas

Quando a análise depender de informações distribuídas entre arquivos, o processamento deve considerar as relações entre eles. O resultado não pode ser reduzido à análise isolada do primeiro arquivo. As regras técnicas existentes para cardinalidade estão na seção 12.4; os limites de relações suportadas estão em P-003.

### RF-008 — Disponibilizar as modalidades de entrega

Deve ser possível solicitar relatório, dashboard ou ambos. A seleção de entregas é independente do modo de análise: tanto análise direcionada quanto exploração geral podem utilizar essas modalidades. Formatos seguem RN-004 a RN-006.

### RF-009 — Gerar relatório PDF

Quando solicitado, a aplicação deve gerar um PDF real contendo a análise textual e a interpretação dos resultados. A entrega não é satisfeita apenas por texto na conversa, Markdown, HTML ou especificação interna.

### RF-010 — Gerar dashboard HTML

Quando solicitado, a aplicação deve gerar HTML real para o dashboard, respeitando a ausência de narrativa interpretativa. Uma imagem, PDF ou descrição da interface não substitui essa entrega.

### RF-011 — Produzir gráficos

As entregas devem poder incluir gráficos compatíveis com a análise. Não atende à intenção do produto entregar somente uma listagem básica de estatísticas quando foram solicitadas visualizações ou dashboard. A quantidade e os tipos dependem do pedido e dos dados; não existe número fixo aprovado.

### RF-012 — Aplicar cuidado visual às entregas

A produção dos dashboards deve contemplar composição visual, uso de cores, hierarquia e legibilidade. A expectativa inclui corrigir resultados monótonos ou visualmente fracos. **Revisão 1.4 (confirmado pelo usuário):** a identidade visual do DataAI (paleta, tipografia, símbolo e regras de uso) foi aprovada e está na seção 12.10.

### RF-013 — Revisar criticamente o resultado final

Antes da liberação, um agente orquestrador de qualidade deve examinar as entregas produzidas e procurar problemas de conteúdo, storytelling e apresentação. A conferência de PDF versus HTML e da ausência de interpretação no dashboard deve ser explícita.

### RF-014 — Encaminhar problemas aos responsáveis

O orquestrador deve indicar os problemas encontrados e encaminhar cada correção ao agente especializado responsável. Uma orientação genérica como “melhorar a entrega”, sem localizar o problema, não satisfaz esse requisito.

### RF-015 — Conferir o resultado das correções

O fluxo de revisão deve permitir examinar novamente a entrega após as correções. Um problema identificado não é considerado resolvido apenas porque o agente produtor declara ter corrigido. Ver RN-010 e a referência técnica da seção 12.3.

### RF-016 — Conservar os arquivos utilizados

Cada análise deve conservar os arquivos que foram efetivamente usados. A conservação deve permitir identificar quais arquivos pertencem à análise, e não apenas manter arquivos sem vínculo com o pedido. Prazo de retenção, exclusão e armazenamento estão em P-007 e P-009.

### RF-017 — Conservar pedido e esclarecimentos

Cada análise deve conservar o pedido recebido e os esclarecimentos fornecidos durante sua definição ou execução. Não foi decidido se a aplicação terá uma interface de chat completo, formulário ou combinação dos dois.

### RF-018 — Conservar definições e tratamentos

Cada análise deve conservar as definições das métricas usadas e os tratamentos efetivamente aplicados. Registrar uma transformação não concede autorização para executá-la; essa autonomia é a pendência P-004.

### RF-019 — Conservar versões de resultados e entregas

A aplicação deve conservar as versões dos resultados e dos arquivos entregues, vinculadas à análise correspondente. Não foi definido o formato de versionamento, a política de restauração nem se toda tentativa intermediária deve ser mantida. Ver P-008.

### RF-020 — Organizar competências em skills temáticas

As instruções especializadas do projeto devem ser organizadas em pastas com `SKILL.md`, com definições, explicações e nomenclatura claras. A referência estrutural solicitada é o padrão Agent Skills, disponível em `https://agentskills.io/home`. O catálogo existente está na seção 12.1.

### RF-021 — Permitir uso sem programação pelo público inicial

O fluxo principal deve permitir enviar arquivos, descrever a intenção e receber as entregas sem exigir do usuário escrita de Python, SQL, código de agentes ou configuração de skills.

### RF-022 — Calcular métricas abrangentes e orientadas à decisão

A aplicação deve dispor de métricas que vão além de posição (média, mediana) e dispersão (desvio-padrão, quartis). O catálogo cobre qualidade e confiabilidade dos dados, volume, forma da distribuição, composição, concentração, evolução no tempo, comparação com referências, taxas e funis, decomposição de variações, comportamento de entidades e coortes, prazos e durações, associação descritiva, reconciliação entre fontes e sensibilidade dos resultados. A seleção depende dos dados e do objetivo; não se executa o catálogo inteiro em toda análise. O catálogo, as condições de uso e as convenções estão na seção 12.7. Confirmado na revisão 1.3; os detalhes do catálogo são **[proposta MVP]** (P-016).

### RF-023 — Trabalhar com tabelas distribuídas em vários arquivos

Uma análise pode receber uma mesma tabela dividida em vários arquivos ou abas (partições por período, filial, região etc.) e várias tabelas diferentes espalhadas por arquivos e abas. A aplicação deve identificar quais arquivos são partições de uma mesma tabela, empilhá-las preservando a origem de cada linha e tratar as demais como tabelas distintas. Regras na seção 12.8. Confirmado na revisão 1.3.

### RF-024 — Descobrir ligações entre arquivos

A aplicação deve descobrir, a partir dos próprios dados, as chaves e relações candidatas entre tabelas de arquivos diferentes, sem exigir que o usuário as informe. Cada ligação descoberta deve trazer evidência: colunas envolvidas, correspondência de valores, cardinalidade observada e integridade referencial (órfãos). A descoberta não autoriza usar uma ligação que a análise não pede (RN-003). Regras na seção 12.8. Confirmado na revisão 1.3.

### RF-025 — Aceitar insumos de origens diferentes

Arquivos podem vir de sistemas, setores ou fontes diferentes, com nomes de colunas, códigos, formatos de data, unidades e granularidades distintos. A aplicação deve registrar a origem (linhagem) de cada dataset, coluna derivada e resultado; harmonizar formatos de forma registrada; e, quando duas fontes trouxerem a mesma medida ou entidade, medir cobertura e divergência entre elas em vez de escolher uma em silêncio. Confirmado na revisão 1.3; política de conflitos em P-020.

## 7. Regras de negócio confirmadas

### RN-001 — O produto é multidomínio

O tema do conjunto de dados não pode ser fixado como e-commerce. A escolha de métricas e análises deve considerar os dados e o pedido. Por exemplo, ticket médio e valor de vendas não são métricas obrigatórias para um conjunto educacional.

**Relacionamentos:** RF-003; CA-003.

### RN-002 — Pergunta específica não é obrigatória na exploração geral

Uma solicitação de varredura geral é um objetivo válido. O sistema deve poder iniciar esse modo sem exigir que o usuário invente uma pergunta específica. Isso não elimina a possibilidade de uma dúvida concreta sobre o significado dos dados, cuja condução ainda depende de P-005.

**Relacionamentos:** RF-005; CA-005.

### RN-003 — Mais de um arquivo pode participar da mesma análise

O envio de múltiplos arquivos não representa, obrigatoriamente, múltiplas análises independentes. O sistema deve considerar o conjunto e suas relações para atender à solicitação. Arquivos independentes não devem receber uma relação sem fundamento apenas por terem sido enviados juntos.

**Relacionamentos:** RF-001, RF-007; CA-007.

### RN-004 — Relatório final é PDF

Qualquer entrega apresentada como relatório final deve ser um arquivo PDF. A interpretação textual dos resultados pertence a essa modalidade de entrega.

**Relacionamentos:** RF-008, RF-009; CA-008.

### RN-005 — Dashboard final é HTML

Qualquer entrega apresentada como dashboard final deve ser um arquivo HTML. O dashboard deve apresentar visualizações e elementos de exploração, respeitando RN-006.

**Relacionamentos:** RF-008, RF-010; CA-009.

### RN-006 — O dashboard não contém narrativa interpretativa

O dashboard não deve conter parágrafos analíticos, resumos executivos, conclusões, recomendações ou cards textuais de insights. Uma frase que interpreta o resultado continua proibida se colocada em título, tooltip ou outro componente.

Títulos de gráficos e os elementos indispensáveis à leitura e operação — valores, unidades, eixos, legendas, cabeçalhos e rótulos de controles — não são interpretação. Essa delimitação é a usada no pacote de skills existente para operacionalizar a instrução do usuário.

Exemplo permitido: “Ocorrências por mês”. Exemplo proibido: “O aumento de ocorrências demonstra falha da estratégia”. O segundo contém uma conclusão e deve ficar no relatório, caso a análise a sustente.

**Relacionamentos:** RF-010, RF-013; CA-010, CA-011.

### RN-007 — Duas modalidades de entrega não criam um terceiro formato

Quando o usuário solicitar ambas, devem ser produzidos PDF e HTML. Não substituir os dois por um único arquivo em formato diferente. A quantidade de relatórios ou dashboards por solicitação continua em P-010.

**Relacionamentos:** RF-008 a RF-010; CA-012.

### RN-008 — Insights não autorizam narrativa no HTML

O pedido de insights na exploração geral não modifica RN-006. A interpretação pertence ao PDF; o dashboard apresenta as visualizações relacionadas aos achados. Esclarecimentos e limitações quando somente HTML for pedido seguem RN-015.

**Relacionamentos:** RF-005, RF-008; CA-013.

### RN-009 — A conferência de formato faz parte da revisão final

O orquestrador deve verificar especificamente se o relatório é PDF, se o dashboard é HTML e se o HTML está livre de narrativa interpretativa. A correção dos cálculos não dispensa essa conferência.

**Relacionamentos:** RF-013; CA-014.

### RN-010 — Defeitos encontrados exigem correção e nova conferência

O orquestrador deve procurar problemas, indicá-los e encaminhá-los aos responsáveis. A entrega não deve ser apresentada como aprovada enquanto um defeito identificado permanecer sem resolução verificada. O limite de tentativas e a distinção entre defeito e sugestão opcional ainda não foram aprovados como políticas de produto; ver P-012.

Essa exigência não representa garantia de detecção de todo erro possível. A aplicação deve demonstrar quais verificações realizou, em vez de prometer infalibilidade.

**Relacionamentos:** RF-013 a RF-015; CA-015 a CA-017.

### RN-011 — O relatório precisa de encadeamento analítico

O relatório deve apresentar achados e interpretação de forma coerente e conectada ao objetivo da análise. O orquestrador deve avaliar seu storytelling, conforme solicitado. Não basta reunir estatísticas sem explicar sua relação com o objetivo. A matriz detalhada existente está na seção 12.3.

**Relacionamentos:** RF-009, RF-013; CA-018.

### RN-012 — Acabamento visual é critério de entrega

A composição do dashboard deve ser revisada quanto a monotonia, hierarquia, diferenciação visual e legibilidade. A expectativa de variedade de cores não autoriza cores aleatórias nem exige várias cores para uma única série quando isso prejudicar a leitura.

**Relacionamentos:** RF-012, RF-013; CA-019.

### RN-013 — O histórico pertence à análise correspondente

Arquivos, pedido, esclarecimentos, definições de métricas, tratamentos e versões dos resultados e entregas devem permanecer associados à análise em que foram usados. Preservar itens isolados sem permitir reconstruir essa associação não satisfaz a decisão confirmada.

**Relacionamentos:** RF-016 a RF-019; CA-020 a CA-023.

### RN-014 — As definições do exemplo não se tornam definições universais

Métricas, nomes de colunas, moeda, datas, filtros, relações e critérios específicos de um conjunto de teste não devem ser automaticamente reutilizados em outros temas ou arquivos. A demonstração de e-commerce não definiu uma moeda padrão, uma chave global nem um período padrão do DataAI.

**Relacionamentos:** RF-003, RF-007, RF-018; CA-003, CA-024.

### RN-015 — Resumo da execução acompanha toda entrega

Toda solicitação concluída gera, além das entregas pedidas, um **resumo da execução**: texto separado do dashboard que registra suposições adotadas, esclarecimentos, tratamentos aplicados, limitações dos dados e resultado da revisão de qualidade. Ele é mostrado ao usuário junto da entrega e conservado no histórico da análise.

O resumo da execução não é relatório nem dashboard: não contém análise interpretativa dos achados, que continua exclusiva do PDF. Quando somente o dashboard for pedido, é por ele que o usuário recebe as limitações, sem violar RN-006. O formato técnico (por exemplo, mensagem na interface ou arquivo Markdown) será definido junto da interface (P-018).

**Relacionamentos:** RN-006, RN-008, RF-017, RF-018; resolve P-011.

### RN-016 — Métricas não se limitam a posição e dispersão

Toda análise deve considerar, entre as famílias aplicáveis do catálogo (12.7), as que ajudam a decidir: onde está o volume ou o problema (composição e concentração), para onde está indo (tendência), em relação a quê (referência), o que explica a variação (decomposição) e quanto se pode confiar no número (qualidade e sensibilidade). Uma análise composta apenas de médias, medianas e desvios, quando os dados permitem mais, é incompleta e deve ser apontada pela revisão.

**Relacionamentos:** RF-006, RF-022; CA-026, CA-031.

### RN-017 — Um arquivo não é uma tabela

Arquivo, aba e tabela são coisas diferentes. Uma tabela pode estar em vários arquivos (partições) e um arquivo pode ter várias tabelas (abas). Partições são empilhadas; tabelas diferentes só se juntam por chave verificada. Empilhar tabelas de esquemas diferentes ou juntar partições é defeito.

**Relacionamentos:** RF-023, RN-003; CA-027.

### RN-018 — Ligações exigem evidência nos dados

Uma ligação entre tabelas só pode ser usada quando houver evidência nos valores (correspondência e cardinalidade medidas). Nome de coluna parecido é indício, não prova. Toda ligação usada é declarada no resumo da execução e no relatório (seção de dados utilizados) com sua cardinalidade e taxa de órfãos.

**Relacionamentos:** RF-007, RF-024, RN-003; CA-028, CA-029.

### RN-019 — Origem de todo número é rastreável

Todo resultado deve permitir chegar aos arquivos, abas, colunas, junções e tratamentos que o produziram. Divergências entre fontes para a mesma medida são reportadas, não escondidas por escolha silenciosa de uma das fontes.

**Relacionamentos:** RF-018, RF-025; CA-030.

## 8. Fluxos de uso

### 8.1. Fluxo principal — análise direcionada

**Base confirmada:** RF-001 a RF-004, RF-006 a RF-019 e RF-021.

1. O usuário fornece um ou mais CSVs ou arquivos Excel e descreve sua pergunta.
2. O pedido inclui ou permite estabelecer se a entrega desejada é PDF, HTML ou ambas. A escolha exata de componente de interface não foi definida.
3. O sistema identifica os dados relevantes e as relações exigidas pela pergunta.
4. O processamento realiza a análise descritiva e conserva as definições de métricas e os tratamentos usados.
5. Os agentes produtores geram as modalidades de entrega solicitadas.
6. O orquestrador examina os arquivos finais e direciona problemas aos responsáveis.
7. Havendo correção, a parte afetada é conferida novamente.
8. A entrega aprovada é disponibilizada ao usuário, conservando-se seu histórico.

**Alternativas e exceções:**

- Relação ou significado ambíguo: o pacote de skills prevê esclarecimento; a política de quando perguntar está em P-005.
- Necessidade de excluir dados, imputar valores ou resolver duplicidade: a autonomia para esse tratamento está em P-004.
- Arquivo ilegível ou estrutura não suportada: o catálogo prevê informar bloqueio/falha; as regras de rejeição de lote e entrega parcial não foram aprovadas. Ver P-013.
- Defeito de entrega: encaminhar para correção; não liberar como aprovado enquanto o problema identificado persistir.

### 8.2. Fluxo principal — exploração geral

**Base confirmada:** RF-005, RF-006 a RF-019 e RN-002.

1. O usuário fornece os arquivos e solicita exploração geral ou insights.
2. A aplicação aceita o pedido sem exigir uma pergunta específica.
3. O sistema examina a estrutura e o contexto disponível para selecionar análises descritivas e relações pertinentes.
4. A análise produz resultados e identifica achados.
5. A interpretação é preparada para PDF, quando solicitado; o HTML respeita RN-006.
6. As entregas percorrem o mesmo ciclo de revisão e conservação do fluxo direcionado.

**Ainda não aprovado:** conjunto mínimo fixo de verificações, regra para selecionar os “principais” achados, aprovação prévia do plano e grau de autonomia para avançar quando o contexto for insuficiente. Ver P-005 e P-016.

### 8.3. Fluxo de correção da entrega

**Base confirmada:** RF-013 a RF-015.

1. O revisor identifica o problema na entrega final.
2. Indica o problema e o agente especializado responsável.
3. Encaminha a correção ao responsável.
4. O responsável produz uma revisão do resultado ou do artefato afetado.
5. O orquestrador verifica a revisão e decide se o problema foi resolvido.
6. Se continuar presente, a entrega permanece sem aprovação.

O formato técnico do registro de problemas e o teto de ciclos existentes no pacote estão nas seções 9 e 12.3; não são políticas de produto ratificadas separadamente.

### 8.4. Retomada e pedidos após a entrega

A conservação do histórico está confirmada. A possibilidade de retomar uma análise por conversa, recalcular um recorte, restaurar uma versão ou editar um dashboard após a entrega foi sugerida, mas ainda não foi aprovada como funcionalidade. Ver P-008.

## 9. Estados e transições

### 9.1. Estados da solicitação na aplicação

Não há máquina de estados de negócio aprovada para a solicitação completa. Não foram definidos códigos persistidos, tela de acompanhamento, fila, retomada, cancelamento ou transições executadas por um usuário administrador. Ver P-013 e P-017.

Portanto, não criar nesta especificação uma enumeração definitiva como se já tivesse sido acordada para o banco ou para a API.

### 9.2. Estados existentes no contrato das skills — referência existente

Os códigos abaixo pertencem aos resultados internos das skills do pacote `3.0.0`.

| Código | Significado no pacote | Condição/participante |
|---|---|---|
| `completed` | A tarefa da skill terminou. | Emitido pela skill quando conclui sua responsabilidade. Não significa automaticamente entrega aprovada. |
| `needs_clarification` | É necessário esclarecimento. | A skill registra a dúvida; a forma de coleta da resposta depende da aplicação. |
| `blocked` | Falta um pré-requisito para concluir. | A skill informa a dependência ausente, por exemplo dado ou ferramenta. |
| `failed` | Uma operação tentada falhou. | A skill informa a falha e sua causa útil. |

A retomada após esclarecimento ou bloqueio não tem transições formais de aplicação definidas. Esses códigos não estabelecem, por si só, persistência de jobs ou reexecução automática.

### 9.3. Decisões de revisão — referência existente

| Responsável | Campo e valores existentes | Interpretação |
|---|---|---|
| `validate-analysis` | `result.decision`: `pass`, `pass_with_warnings`, `fail`, `blocked` | Resultado da auditoria técnica; não substitui a liberação final. |
| `orchestrate-quality-review` | `result.decision`: `approve`, `revise`, `blocked` | Aprovar a revisão examinada, pedir correção ou declarar impedimento. |

O fluxo do pacote permite revisão concluída com entrega reprovada: `status=completed` e decisão desfavorável não são contraditórios.

No pacote, uma mudança posterior em artefato aprovado invalida a liberação da revisão alterada. Essa verificação usa hashes; a tecnologia definitiva de versionamento e persistência não foi aprovada.

## 10. Modelo de dados acordado

### 10.1. Situação do modelo físico

**Não foram acordados banco de dados, tabelas, colunas, tipos, chaves primárias, chaves estrangeiras, índices, restrições de unicidade ou procedimentos para o DataAI.** Não há DDL aprovado.

Nomes de tabelas, páginas ou procedimentos de outros projetos do usuário não integram este projeto. Os nomes dos CSVs de e-commerce são dados de uma demonstração, não tabelas obrigatórias do banco do DataAI.

### 10.2. Informações cuja conservação está confirmada

O quadro descreve informações e associações, sem propor tabelas ou campos físicos.

| Informação | Associação obrigatória | Origem do requisito |
|---|---|---|
| Arquivos utilizados | À análise que os utilizou. | RF-016 |
| Pedido recebido | À análise correspondente. | RF-017 |
| Esclarecimentos recebidos | À análise e ao pedido a que se referem. | RF-017 |
| Definições das métricas | À análise em que foram adotadas. | RF-018 |
| Tratamentos aplicados | À análise em que foram executados. | RF-018 |
| Versões dos resultados | À análise e ao resultado versionado. | RF-019 |
| Versões das entregas | À análise e à entrega versionada. | RF-019 |

Não foram definidas quantidade máxima de arquivos por análise, obrigatoriedade de esclarecimentos quando não houver dúvidas, conservação de tentativas malsucedidas, exclusão em cascata ou restauração de versões.

### 10.3. Contratos de intercâmbio existentes — não são esquema de banco

O pacote de skills utiliza o envelope `skill_name`, `status`, `result`, `warnings`, `questions` e `evidence_refs`. Os dados específicos de cada skill ficam diretamente em `result`.

Referências como `dataset_id`, `metric_id`, `result_id`, `chart_id` e `artifact_ref` já existem nos contratos do pacote. Seu uso não implica tabelas com esses nomes, nem define como a aplicação deve gerá-las e persistir suas associações.

## 11. Telas e comportamento da interface

### 11.1. Interações funcionais confirmadas

| Interação | Comportamento exigido | Requisitos relacionados |
|---|---|---|
| Fornecer arquivos | Permitir entradas CSV/Excel e múltiplos arquivos. | RF-001, RF-002 |
| Apresentar intenção | Permitir pergunta específica ou pedido de exploração geral. | RF-004, RF-005 |
| Escolher entrega | Permitir relatório, dashboard ou ambos. | RF-008 |
| Receber entrega | Disponibilizar PDF e/ou HTML reais após a revisão. | RF-009, RF-010, RF-013 |

Não foram acordados quantidade e nomes de telas, campos obrigatórios de formulários, componentes, rotas, menus, URLs, páginas, modais ou navegação entre telas. As interações acima podem compartilhar uma tela; essa disposição não está aprovada.

### 11.2. Dashboard

**Confirmado:** HTML sem interpretação textual, gráficos e cuidado visual explícito.

**Referência existente:** hierarquia, paleta com funções definidas, cores consistentes entre categorias, tipografia legível, responsividade e inspeção de interações. O pacote recomenda verificar telas amplas, intermediárias e móveis, sem transformar larguras exemplificativas em padrões obrigatórios de produto.

**Não confirmado:** filtros fixos ou obrigatórios para todo dashboard, múltiplas abas/visões como padrão, um HTML único como limite e execução inteiramente offline como requisito universal. Os filtros de ano e UF e as duas visões da demonstração não devem ser impostos a outros conjuntos de dados.

### 11.3. Validações de interface e banco

Não foi acordada a distribuição de validações entre interface, backend e banco de dados. Não considerar uma validação de tela como restrição de banco automaticamente. Ver P-009 e P-018.

## 12. Agentes, skills, integrações e processos automáticos

### 12.1. Catálogo existente

O projeto pretende utilizar múltiplos agentes especializados. O pacote `dataai-skills` versão `3.0.0` contém os nomes abaixo, preservados nesta especificação.

| Skill | Responsabilidade documentada | Perfil relacionado |
|---|---|---|
| `plan-analysis` | Interpretar intenção e planejar a análise e as entregas. | `analysis-planner` |
| `ingest-tabular` | Ler CSV e Excel (`.xlsx`) e registrar opções, origem, abas e erros de leitura. Substitui a antiga `ingest-csv`. | `data-specialist` |
| `profile-data` | Examinar tipos semânticos, ausências, duplicidades e qualidade. | `data-specialist` |
| `relate-datasets` | Planejar e verificar relações entre tabelas. | `data-specialist` |
| `describe-data` | Calcular estatísticas e agregações descritivas. | `data-analyst` |
| `design-charts` | Definir visualizações e semântica dos gráficos. | `visualization-specialist` |
| `compose-dashboard` | Produzir HTML e cuidar da interface e UX. | `interface-designer` |
| `write-analysis-report` | Produzir PDF, interpretação e storytelling. | `report-writer` |
| `validate-analysis` | Auditar números, relações, contratos e consistência. | `technical-reviewer` |
| `orchestrate-quality-review` | Revisar entregas finais, direcionar correções e decidir liberação. | `quality-orchestrator` |
| `brand-identity` | Guardar a identidade visual aprovada e dizer como aplicá-la (revisão 1.4, seção 12.10). | `visualization-specialist`, `interface-designer`, `report-writer` |

Os oito perfis declarativos estão em `agents/*.yaml` deste repositório (revisão 1.3). Eles são lidos pelo código da aplicação (seção 12.9); sozinhos, não criam agentes executáveis. A execução dos agentes será feita pela própria aplicação, sem CrewAI (ver 12.5).

**Ingestão de CSV e Excel (confirmado na revisão 1.2):** a skill `ingest-csv` do pacote `3.0.0` passa a se chamar `ingest-tabular` e é responsável pela leitura de CSV e Excel. Uma única skill de ingestão cobre os dois formatos; não haverá skill separada para Excel. O pacote de skills e os contratos que citam `ingest-csv` devem ser atualizados para o novo nome. O suporte Excel do MVP está em 16.3 (P-001).

Uma skill pode ser usada por um agente com outras skills. Não foi estabelecida regra que imponha um agente exclusivo para cada arquivo ou cada skill.

### 12.2. Encadeamento existente — referência de implementação

O pacote documenta a sequência: leitura e perfil dos arquivos; planejamento com colunas e significado verificados; relações quando exigidas; cálculo; preparação de gráficos; geração de PDF/HTML; auditoria técnica; revisão final e correções.

PDF e HTML podem ser produzidos a partir da mesma base de resultados. O pacote permite produção paralela depois dos cálculos; paralelismo não foi aprovado como requisito de desempenho nem como execução obrigatória.

### 12.3. Revisão de qualidade — detalhes existentes

O comportamento geral do revisor está confirmado em RF-013 a RF-015. O pacote detalha esse comportamento da seguinte forma:

- Verificar os arquivos efetivamente gerados e suas renderizações, não somente a descrição do agente produtor.
- Conferir contagens, totais, taxas, unidades e consistência das bases.
- No PDF, verificar objetivo, evidências, sequência dos achados, interpretação proporcional, limitações e legibilidade de todas as páginas.
- No HTML, examinar conteúdo visível, títulos, tooltips e outros componentes para localizar narrativa interpretativa.
- Testar as interações presentes no dashboard e a leitura em diferentes tamanhos de tela.
- Registrar problema, localização, evidência, responsável, correção e critério de verificação.
- Conferir correções sobre as novas revisões e impedir liberação com verificações obrigatórias não realizadas.

O registro técnico existente utiliza `issues` e `repair_tasks`. Para problemas, há campos como `issue_id`, `category`, `severity`, `artifact_ref`, `location`, `evidence_refs`, `problem`, `impact`, `owner_agent`, `target_skill`, `acceptance_criteria`, `status` e `verified_by`.

Esses nomes pertencem ao contrato de intercâmbio existente. Não constituem modelo físico aprovado.

O pacote configura `max_review_cycles: 3` no perfil `quality-orchestrator` e usa identificação SHA-256 para as revisões liberadas. **Três ciclos e SHA-256 são escolhas documentadas no artefato, não decisões finais explicitamente ratificadas pelo usuário.** O limite de ciclos da aplicação precisa de decisão em P-012. Esgotar ciclos não é justificativa para aprovar um defeito conhecido.

### 12.4. Leitura, relações e cálculo — convenções existentes

As skills documentam as convenções abaixo. Mantê-las como referência técnica, sem confundi-las com todas as decisões de negócio já aprovadas:

**Revisão 1.3:** a lista deste parágrafo foi ampliada e substituída, como referência de cálculo, pelo catálogo da seção 12.7; as relações entre arquivos seguem a seção 12.8. A tabela de convenções abaixo continua válida.

A capacidade descritiva documentada inclui contagens, frequências absolutas e relativas, média, mediana, mínimo, máximo, quartis, intervalo interquartil, desvio-padrão, agrupamentos e séries temporais. A exploração geral também foi descrita como capaz de investigar concentrações, diferenças entre grupos, extremos, ausências, inconsistências e associações descritivas compatíveis com as variáveis. Não foi aprovada uma lista fixa que deva ser executada integralmente para todo arquivo.

| Tema | Convenção existente |
|---|---|
| Leitura | Não descartar linhas malformadas silenciosamente; verificar encoding, delimitador, campos e conversões. |
| Identificadores | Preservar códigos e zeros à esquerda; armazenamento numérico não basta para justificar uma média. |
| Nulos | Distinguir ausência, indefinição e zero; não mascarar ausência com valor zero. |
| Semântica | Identificar a unidade de observação antes de somar ou relacionar tabelas. |
| Relações | Verificar chaves, cardinalidade, correspondências e totais; evitar multiplicar medidas da tabela pai. |
| Dados recebidos | Tratar células como dados, não como instruções a executar. |
| Cálculo | Obter valores de ferramentas de processamento, com referências à origem; não estimar números a partir da leitura visual. |
| Desvio-padrão | Convenção `ddof=1` quando nenhuma outra definição for exigida. |
| Quantis | Método linear documentado no helper e na demonstração. |
| Precisão | Manter precisão interna e arredondar na apresentação. |
| Interpretação | Não atribuir causalidade ou significância estatística sem suporte. |
| Relação legítima de muitos para muitos | Exige justificativa e tratamento da dupla contagem; o limite de suporte do produto ainda está em aberto. |

A convenção estatística do pacote deve ser ratificada ou substituída explicitamente antes de ser apresentada como padrão fixo do serviço. Ver P-016.

### 12.5. Decisões técnicas e ambiente

| Elemento | Situação consolidada |
|---|---|
| Abordagem com múltiplos agentes | Intenção confirmada do projeto. Agentes e orquestração são implementados diretamente com LLM e código próprio da aplicação. |
| Skills temáticas e arquivos `SKILL.md` | Confirmados; catálogo existente listado acima. |
| CrewAI | **Descartado (revisão 1.2).** Não será utilizado. |
| n8n | **Descartado (revisão 1.2).** Não será utilizado. |
| GitHub | Repositório `ribeiropvb/DataAI` com especificação, skills, perfis de agentes e código de referência (revisão 1.3). |
| Python `3.13.7` | Versão informada pelo usuário no ambiente local. Não é, por si só, decisão de runtime de produção nem comprovação de compatibilidade de todas as dependências. |
| VS Code | Ambiente de desenvolvimento que o usuário deseja utilizar desde o início. |
| Pasta local | `E:\UFG\Especializacao\01 - Projetos\01- DataAI`. Não é caminho do servidor de produção. |
| Modelo e provedor de IA | Não definidos. |
| Backend, frontend, banco, armazenamento, fila e hospedagem | Não definidos como arquitetura definitiva. |

**Confirmado na revisão 1.2:** o DataAI não utilizará CrewAI nem n8n. Toda a coordenação será feita por agentes baseados em LLM, chamados pelo código da própria aplicação, que fornece a eles as skills e as ferramentas (leitura de arquivos, cálculo, geração de PDF/HTML e renderização para revisão). A sugestão do pacote de usar n8n como porta de entrada fica sem efeito. Provedor de IA: Claude (Anthropic) ou OpenAI, decidido por Pedro em 31/10/2026 (P-017).

Os códigos de entrega existentes no pacote são `output_mode=report`, `output_mode=dashboard` e `output_mode=both`. Esses valores representam a modalidade de saída; não representam análise direcionada versus exploração geral. Não há nome de campo ou enumeração técnica aprovada para esses dois modos de análise.

Nos produtores de arquivos, o pacote diferencia um intermediário de uma entrega efetivamente gerada: `stage=specification` ou `stage=artifact` no dashboard; `stage=draft` ou `stage=artifact` no relatório. Concluir uma especificação interna não satisfaz RF-009 ou RF-010. O adaptador que converteria o antigo valor `analysis` para `report` é uma proposta de compatibilidade do pacote, não requisito de migração aprovado.

### 12.6. Integrações externas e execução automática

Não foram acordadas APIs externas de dados, autenticação, e-mail, mensagens, pagamentos, agendamento ou publicação. O pedido de colocar o serviço em produção existe, mas fornecedor e condições de operação continuam pendentes.

O orquestrador deve encaminhar correções dentro do processamento da análise. Isso não estabelece integração com um gerenciador externo de tarefas.

### 12.7. Catálogo de métricas (revisão 1.3)

**Situação:** a abrangência é confirmada (RF-022, RN-016). As famílias, fórmulas, limiares e convenções abaixo são **[proposta MVP]** e substituem a lista curta da seção 12.4 como referência de cálculo (P-016). Cada métrica é implementada em `dataai/tools/metrics.py`; o nome da função aparece na última coluna.

#### 12.7.1. Como as métricas são escolhidas

1. **Qualidade (M1) sempre entra.** Ela informa quanto se pode confiar em cada número e alimenta o resumo da execução.
2. **Aplicabilidade pelos tipos semânticos.** Cada família exige certos tipos de coluna (tabela 12.7.3). Uma família só é planejada quando os dados a suportam.
3. **Análise direcionada:** entram as famílias que respondem à pergunta, mais M1 e a sensibilidade (M15) da métrica principal.
4. **Exploração geral:** entram as famílias aplicáveis com maior chance de achado relevante, de 5 a 12 análises, cobrindo pelo menos três perguntas de decisão (12.7.2).
5. **Nada de catálogo inteiro por padrão.** Uma métrica que não se liga ao objetivo não é calculada só porque é possível.

#### 12.7.2. Perguntas de decisão que o conjunto deve cobrir

| Pergunta de decisão | Famílias que respondem |
|---|---|
| Posso confiar nestes dados? | M1, M15, M14 |
| Quanto e quão típico? | M2, M3, M4 |
| Onde está o volume ou o problema? | M5, M6 |
| Para onde está indo? | M7 |
| Em relação a quê (meta, período anterior, média, outro grupo)? | M8, M9 |
| O que explica a variação? | M10 |
| Quem são as entidades e como se comportam? | M11 |
| Os prazos estão sendo cumpridos? | M12 |
| O que varia junto? | M13 |
| As fontes concordam entre si? | M14 |

Na exploração geral e no relatório, cada achado principal responde a pelo menos uma dessas perguntas e traz: magnitude (valor absoluto e relativo), comparação com uma referência, indicação de confiabilidade (n, ausências, sensibilidade) e, quando couber, ponto a investigar. Isso é o que torna a métrica útil para decidir, sem atribuir causa.

#### 12.7.3. Famílias

**M1 — Qualidade e confiabilidade** (sempre)

| Métrica | Definição | Função |
|---|---|---|
| Completude | % de valores não ausentes por coluna, por linha e no dataset; completude dos campos usados em cada métrica. | `quality_completeness` |
| Unicidade | % de linhas totalmente duplicadas; % de duplicidade em cada chave candidata. | `quality_uniqueness` |
| Validade | % de valores que respeitam o tipo e a faixa plausível (datas convertíveis, números, negativos inesperados, datas futuras). | `quality_validity` |
| Consistência | Variantes de grafia da mesma categoria (`SP`, `sp`, ` S.P.`); regras entre colunas detectáveis (fim ≥ início, total = soma das partes). | `quality_consistency` |
| Cobertura temporal | Data mínima e máxima, períodos sem registro, períodos parciais nas pontas. | `quality_temporal_coverage` |
| Integridade referencial | % de órfãos em cada ligação usada (12.8). | `relations.referential_integrity` |
| Base efetiva | Para cada resultado: n usado, n excluído por ausência ou filtro. | registrado em todo resultado |

**M2 — Volume e contagem:** linhas, distintos por coluna, contagem por entidade, densidade (eventos por entidade, por período). Função `volume_counts`.

**M3 — Posição:** média, mediana, moda, média aparada a 5% em cada ponta, média ponderada (quando há coluna de peso declarada), mínimo, máximo e percentis P1, P5, P10, P25, P50, P75, P90, P95, P99. Função `position_stats`.

**M4 — Dispersão e forma:** desvio-padrão e variância amostrais (`ddof=1`), amplitude, IQR, desvio absoluto mediano (MAD), coeficiente de variação (só para medidas de razão estritamente positivas), assimetria e curtose em excesso (estimadores corrigidos), histograma com regra de Freedman–Diaconis e extremos por cercas do IQR (1,5·IQR) e por z robusto (|0,6745·(x − mediana)/MAD| > 3,5). Extremos são sinalizados, nunca removidos. Função `dispersion_shape`.

**M5 — Frequência e composição:** frequência absoluta, relativa e acumulada; moda categórica; número de categorias; diversidade pela entropia de Shannon normalizada (0 = tudo em uma categoria, 1 = distribuição uniforme); participação de cada categoria no total de uma medida; tabela cruzada com percentuais por linha, por coluna e do total. Funções `frequency_table`, `share_of_total`, `crosstab`.

**M6 — Concentração e Pareto:** participação dos maiores (top 1, top 5, top 10 e top 20% dos itens); curva de Pareto e classes ABC (A até 80% acumulado, B até 95%, C o restante); número de itens que somam 80%; índice de Gini (0 = igualdade, 1 = concentração total); índice Herfindahl-Hirschman (HHI, soma dos quadrados das participações em %, de 0 a 10.000). Funções `concentration`, `pareto_abc`. Exige medida não negativa.

**M7 — Tempo e tendência:** série na granularidade declarada (dia, semana, mês, trimestre, ano); variação absoluta e percentual período a período; comparação com o mesmo período do ano anterior quando há pelo menos 13 meses; acumulado no ano; média móvel com janela declarada; taxa composta de crescimento (CAGR) quando há pelo menos dois anos completos e valores positivos; inclinação da tendência linear por período (mínimos quadrados, descritiva, sem p-valor) e variação total entre o primeiro e o último período completo; perfil sazonal descritivo (média por mês do ano, dia da semana ou hora); volatilidade (desvio-padrão das variações percentuais); pico e vale; períodos parciais e lacunas. Funções `time_series`, `period_change`, `trend_summary`, `seasonal_profile`.

**M8 — Comparação entre grupos e com referências:** diferença absoluta e relativa entre grupos; razão; índice relativo à média geral (100 = média); ranking com tratamento de empates; comparação contra referência — atingimento (realizado ÷ meta) e lacuna (realizado − meta), quando a referência existe nos dados ou foi informada pelo usuário (P-019); sinal de grupo pequeno (n < 30). Funções `group_comparison`, `compare_to_reference`.

**M9 — Taxas, proporções e funis:** toda taxa guarda numerador e denominador; distinção explícita entre taxa agregada (Σnumerador ÷ Σdenominador) e média das taxas dos grupos; funil de etapas sequenciais com conversão por etapa e acumulada; verificação de paradoxo de Simpson (a direção da diferença entre dois grupos no total se inverte dentro dos estratos), que gera aviso obrigatório. Funções `rate`, `funnel`, `simpson_check`.

**M10 — Decomposição e fatores da variação:** contribuição de cada grupo para a variação do total entre dois períodos (Δgrupo ÷ Δtotal, somando 100%); decomposição exata da variação de uma média ou taxa em efeito composição (mudança no peso dos grupos) e efeito desempenho (mudança dentro dos grupos), pelo método de shift-share com pesos médios; ponte (waterfall) do valor inicial ao final. É a família que responde "o que explica a mudança" sem afirmar causa. Funções `contribution_to_change`, `mix_rate_decomposition`.

**M11 — Entidades, coortes e comportamento** (exige identificador de entidade e data de evento): recência (dias entre o último evento da entidade e a data de referência, que é a maior data dos dados, salvo outra declarada), frequência (eventos por entidade), valor (soma de uma medida por entidade); segmentação por quintis de recência, frequência e valor; coortes pelo período da primeira ocorrência e retenção nos períodos seguintes (% da coorte ativa); entidades novas e recorrentes por período; inatividade descritiva (sem evento há mais que um limite declarado); intervalo mediano entre eventos. Funções `entity_rfm`, `cohort_retention`, `new_vs_returning`.

**M12 — Durações e prazos** (exige duas datas, ou uma data e um prazo): duração (fim − início) com estatísticas de M3 e M4; % concluído dentro do prazo ou limite declarado; atraso médio e mediano entre os atrasados; itens em aberto em uma data de referência (backlog). Funções `durations`, `deadline_compliance`.

**M13 — Associação descritiva:** Pearson (medida × medida, relação linear), Spearman (monotônica, também para ordinais), V de Cramér com correção de viés (categoria × categoria) e razão de correlação eta (categoria × medida). Sempre com n e sem p-valor. Linguagem: |coeficiente| < 0,3 fraca, de 0,3 a 0,5 moderada, ≥ 0,5 forte. Associação nunca é apresentada como causa. Função `association`.

**M14 — Reconciliação entre fontes** (exige duas fontes com entidade ou medida em comum, 12.8): cobertura cruzada (% das entidades de A presentes em B e vice-versa); sobreposição dos períodos cobertos; reconciliação de medida equivalente no nível comum (total em A, total em B, diferença absoluta e %); divergência de atributos (mesma chave com valor diferente, em %); participação de cada partição ou fonte em um conjunto empilhado. Funções `source_coverage`, `reconcile_measure`, `attribute_divergence`.

**M15 — Sensibilidade e robustez:** recálculo da métrica principal sem os extremos (cercas do IQR) e variação resultante; distância entre média e mediana; resultado com e sem linhas órfãs ou com ausências; estabilidade do ranking dos grupos (quantos mudam de posição). Se a sensibilidade passar de 10%, o resultado recebe `sensitive: true` e o relatório deve dizer isso. Função `sensitivity`.

#### 12.7.4. Aplicabilidade

| Família | Exige |
|---|---|
| M1, M2 | qualquer dataset |
| M3, M4, M15 | uma `measure` |
| M5 | uma `category` (e, para participação, uma `measure`) |
| M6 | `category` ou `identifier` + `measure` não negativa |
| M7 | `datetime` + `measure` ou contagem, com pelo menos 3 períodos |
| M8 | `category` + `measure`/taxa; para referência, coluna ou valor de meta (P-019) |
| M9 | numerador e denominador definidos; funil exige etapas ordenadas |
| M10 | `datetime` (dois períodos) + `category` + `measure` |
| M11 | `identifier` de entidade + `datetime` de evento (+ `measure` para valor) |
| M12 | duas `datetime` ou `datetime` + prazo |
| M13 | duas colunas compatíveis com n ≥ 10 |
| M14 | duas fontes com entidade ou medida comum |

#### 12.7.5. Convenções comuns

- Desvio-padrão `ddof=1`; quantis pelo método linear; precisão total interna e arredondamento só na apresentação; percentuais guardados como fração.
- Ausentes são excluídos de cada métrica e a exclusão é contada; zero nunca é ausente.
- Divisão por zero gera ausente com aviso, nunca zero.
- Grupos com n < 30 recebem `small_sample: true`; períodos incompletos recebem `partial_period: true`.
- Totais de controle: a soma dos grupos confere com o total quando a métrica é aditiva.
- Todo resultado registra `metric_id`, família, fórmula, população, filtros, unidade, n, excluídos, parâmetros, avisos, linhagem (datasets, arquivos, abas e colunas) e o código que o calculou.
- Fora do MVP continuam testes de hipótese, p-valores, intervalos de confiança inferenciais, previsão e inferência causal (P-014). Tendência, sazonalidade e decomposição acima são descritivas.

### 12.8. Múltiplos arquivos, origens e descoberta de ligações (revisão 1.3)

**Situação:** o comportamento é confirmado (RF-023 a RF-025, RN-017 a RN-019). Limiares e pesos são **[proposta MVP]** (P-003). Implementação em `dataai/tools/relations.py`.

#### 12.8.1. Inventário

Cada CSV é uma tabela; cada aba `.xlsx` com dados é uma tabela (P-001). Toda tabela guarda arquivo, aba, hash do arquivo e, opcionalmente, a **origem** informada pelo usuário (sistema, setor ou fonte). Sem essa informação, a origem é o nome do arquivo.

#### 12.8.2. Partições: uma tabela em vários arquivos

1. Compare os esquemas normalizados (nomes sem acento, minúsculos, sem espaços nas pontas) de todos os pares de tabelas.
2. **Esquema idêntico** (mesmos nomes e tipos compatíveis): grupo de partições. Empilhamento automático, registrado como ajuste de leitura, com as colunas `_source_file` e `_source_sheet` em cada linha.
3. **Esquema quase idêntico** (similaridade de Jaccard dos nomes ≥ 0,8): proposta de mapeamento de colunas enviada como pergunta. Não empilhar sem resposta.
4. Depois de empilhar: confira que o total de linhas é a soma das partições; procure chaves repetidas entre partições (mesmo registro em dois arquivos) e períodos sobrepostos. Repetição entre partições é aviso e, se afetar a resposta, pergunta.
5. Identifique o discriminador da partição quando possível (token do nome do arquivo, como mês ou filial, ou coluna cujos valores não se sobrepõem entre arquivos) e registre.

#### 12.8.3. Descoberta de ligações entre tabelas

1. **Chaves candidatas** por tabela: colunas e combinações de até 3 colunas, sem ausentes e com valores únicos.
2. **Pares candidatos:** para cada coluna de uma tabela e cada chave candidata de outra, com tipos compatíveis depois de normalizar formato (texto aparado, zeros à esquerda alinhados, número inteiro como texto). Ficam fora colunas `measure` contínuas, datas e booleanos. Colunas com menos de 10 valores distintos, colunas inteiras classificadas como `measure` e alvos que são sequências 1..N só entram se a semelhança dos nomes for pelo menos 0,5, para evitar coincidências entre números pequenos. Nomes genéricos (como `id`) são comparados pelo nome da tabela.
3. **Evidência medida:**
   - contenção = |distintos de A ∩ distintos de B| ÷ |distintos de A|;
   - unicidade do lado referenciado;
   - semelhança dos nomes (indício, nunca suficiente sozinha, RN-018);
   - compatibilidade de formato.
4. **Pontuação** = 0,50·contenção + 0,25·unicidade do alvo + 0,15·semelhança do nome + 0,10·formato. **Forte:** pontuação ≥ 0,7 e contenção ≥ 0,9. **Provável:** pontuação ≥ 0,5 e contenção ≥ 0,5; só é usada depois de confirmada. Abaixo disso, descartada.
5. **Cardinalidade observada** pelo máximo de repetições da chave em cada lado: 1:1, 1:N, N:1 ou N:N.
6. **Integridade referencial:** órfãos no lado filho (contagem, %, exemplos), registros do pai sem filhos, chaves nulas.
7. **Papel de cada tabela:** fato, dimensão, ponte, agregada, referência ou isolada, a partir de medidas, chaves e grão.
8. **Grafo de ligações:** tabelas são nós; ligações fortes são arestas. Caminhos de junção são escolhidos pelo menor caminho com ligações fortes. Tabelas ponte permitem N:N controlado.
9. **Armadilhas detectadas antes de juntar:**
   - *fan-out*: duas relações 1:N saindo da mesma tabela pai juntadas na mesma consulta multiplicam medidas;
   - grão diferente: juntar fato diário a metas mensais exige agregar ao grão comum antes;
   - caminhos alternativos: dois caminhos diferentes entre as mesmas tabelas são ambiguidade e geram pergunta.
10. **Saída:** `results/relationship_map.json` com tabelas, papéis, partições, ligações, evidências e armadilhas, e um diagrama simples no apêndice do relatório.

#### 12.8.4. Uso das ligações

Descobrir não é usar. `plan-analysis` escolhe quais ligações a análise exige; `relate-datasets` executa a junção com verificação antes e depois (linhas, totais de controle, órfãos) e regras de agregação para medidas da tabela pai. Medidas de tabelas de grão mais fino são agregadas ao grão da análise antes de juntar.

#### 12.8.5. Origens diferentes

- **Harmonização registrada:** formatos de data, separador decimal, caixa e espaços de códigos, nomes de colunas equivalentes. Conversões de unidade ou moeda só com regra explícita (dado ou usuário); nunca presumidas.
- **Códigos diferentes para a mesma coisa** entre fontes (por exemplo, `SP` e `35`) exigem tabela de correspondência existente nos dados ou informada; sem ela, a ligação não é feita.
- **Mesma medida em duas fontes:** reconciliar (M14) e reportar divergência. Escolher uma fonte como oficial exige decisão do usuário (P-020).
- **Linhagem:** todo dataset derivado lista seus pais e tratamentos; todo resultado lista datasets, arquivos, abas e colunas de origem (RN-019).

### 12.9. Implementação de referência (revisão 1.3)

**Situação:** estrutura criada no repositório na revisão 1.3 para tornar as skills executáveis. Não é arquitetura de produção (P-017).

| Parte | Local | Papel |
|---|---|---|
| Ferramentas determinísticas | `dataai/tools/` | Leitura, perfil, descoberta de ligações, métricas, gráficos, dashboard HTML, relatório PDF, inspeção de entregas e validação. Todo número sai daqui. |
| Pasta e manifesto da análise | `dataai/workspace.py` | Pasta por análise, hashes, versões e manifesto (P-009). |
| Perfis de agentes | `agents/*.yaml` | Oito perfis: papel, skills, ferramentas permitidas, saída esperada e limites. |
| Execução de agentes | `dataai/agents/` | Monta as instruções do agente (perfil + `SKILL.md`), expõe as ferramentas por chamada de função e executa o ciclo até a resposta final. |
| Provedor de IA | `dataai/llm/` | Interface única com adaptadores para Claude (Anthropic) e OpenAI. O provedor é escolhido pela chave de API configurada (Claude tem prioridade se houver as duas); o modelo tem padrão e pode ser trocado por configuração (P-017). |
| Orquestração | `dataai/orchestrator.py` | Encadeia as etapas, aplica os ciclos de revisão (P-012) e escreve o resumo da execução (RN-015). |
| Modo harness | `dataai/harness.py`, `CLAUDE.md`, `AGENTS.md` | Um agente externo com terminal (Claude Code, Codex) faz o papel dos agentes seguindo as skills e chama as mesmas ferramentas por linha de comando (`preparar`, `ferramenta`, `revisar`). A revisão determinística continua obrigatória. |
| Modo sem IA | `--no-llm` | Executa o fluxo com planejamento heurístico e texto em modelo fixo, para testar ferramentas e entregas antes de escolher o provedor. Não substitui os agentes. |

O LLM decide (planejar, escolher gráficos, redigir, revisar) e as ferramentas calculam. O texto do relatório referencia resultados por marcadores (`{{res_id.campo}}`) que o código substitui pelos valores calculados, de modo que nenhum número do PDF é digitado pelo modelo.

### 12.10. Identidade visual (revisão 1.4)

**Situação:** confirmada pelo usuário em 31/10/2026. A skill `brand-identity` é a dona da identidade; `design-charts`, `compose-dashboard` e `write-analysis-report` a aplicam.

| Item | Decisão |
|---|---|
| Princípios | O dado fala primeiro; descrever, não julgar (nenhuma cor diz se um valor é bom ou ruim); todo número mostra a origem; legível para quem não programa. |
| Cor da marca | Petróleo `#067689`, com neutros "ardósia" levemente puxados para ela. Temas claro (padrão e PDF) e escuro (dashboard, por `prefers-color-scheme`). Texto com contraste mínimo de 4,5:1 nos dois temas. |
| Estados do sistema | `sucesso` (família da marca, fora do eixo verde-vermelho), `atencao`, `erro` e `info`, sempre com ícone e palavra e só para estados do sistema. |
| Cores de dados | Oito categóricas em ordem testada para daltonismo (petróleo, ocre, vinho, azul, ameixa, laranja, violeta, verde); até seis só com legenda; sequencial petróleo; divergente laranja-neutro-petróleo, usada também para variação positiva e negativa. |
| Tipografia | IBM Plex Sans e IBM Plex Mono (licença OFL), embutidas no pacote para o PDF e os gráficos. |
| Símbolo | "Barra-fonte": duas barras e um traço com ponto (lê como o "i" de AI); versões clara, escura e monocromática. |
| Fonte única | `dataai/brand/tokens.json`, lido por `dataai/theme.py`. Nenhum módulo escreve cor própria. |

## 13. Requisitos não funcionais

### 13.1. Expectativas explicitamente estabelecidas

| ID | Definição | Forma de verificar |
|---|---|---|
| RNF-001 | O público inicial deve usar o fluxo principal sem programar. | Executar uma solicitação sem exigir código do usuário; CA-006. |
| RNF-002 | Dashboards devem ter cuidado visual e evitar a apresentação monótona apontada pelo usuário. | Conferir hierarquia, legibilidade e uso de cores na revisão; CA-019. |
| RNF-003 | O relatório deve ter storytelling analítico examinado pelo revisor. | Conferir a ligação entre objetivo, achados e interpretação; CA-018. |
| RNF-004 | Cada análise deve conservar os itens de histórico aprovados. | Recuperar as associações exigidas em RF-016 a RF-019; CA-020 a CA-023. |
| RNF-005 | As skills devem ter definições, explicações e nomes organizados. | Verificar os arquivos `SKILL.md` e as responsabilidades; CA-025. |

### 13.2. Parâmetros ainda não definidos

Não foram definidos SLA, tempo máximo por análise, tamanho dos arquivos, número de usuários simultâneos, orçamento por execução, cota de tokens, preço, escalabilidade, disponibilidade, recuperação de desastre, idiomas da interface ou padrão obrigatório de acessibilidade.

Há necessidade de decidir identidade, acesso, isolamento entre usuários, retenção e exclusão antes de uma implementação de produção. Não há neste documento cláusulas legais ou padrões de conformidade apresentados como se já tivessem sido acordados.

O pacote contém recomendações de contraste, responsividade, uso de referências, preservação de origem e inspeção visual; elas não fixam métricas de serviço ou uma certificação de acessibilidade.

## 14. Propostas recentes ainda não aprovadas

Esta seção evita que sugestões da revisão do negócio sejam incorporadas silenciosamente à base obrigatória.

| Proposta | Situação | Pendência |
|---|---|---|
| Executar automaticamente ajustes de leitura verificáveis e solicitar autorização antes de excluir registros, preencher ausências ou resolver duplicidades ambíguas. | Foi a última pergunta apresentada; ainda não houve resposta. | P-004 |
| Perguntar somente quando uma ambiguidade puder alterar materialmente a resposta e dispensar aprovação técnica em cada etapa. | Proposta de experiência, sem política ratificada. | P-005 |
| Identificar múltiplas tabelas em uma aba, tratar células mescladas e reconhecer subtotais de planilhas. | Proposta posterior à inclusão de Excel; abrangência não aprovada. | P-001 |
| Preservar originais imutáveis e criar representações de trabalho separadas para todos os tratamentos. | As skills já orientam preservação; a política de manipulação e autonomia da aplicação não foi ratificada. A conservação dos arquivos utilizados está confirmada. | P-004, P-007 |
| Usar um HTML com múltiplas visões como padrão e arquivos separados somente por necessidade. | Proposta de organização, não limite universal aprovado. | P-010 |
| Exibir limitações e esclarecimentos fora do HTML quando somente dashboard for solicitado. | **Confirmado na revisão 1.2** como resumo da execução (RN-015). | P-011 (resolvida) |
| Separar defeitos obrigatórios de preferências opcionais de acabamento. | Proposta de classificação; não autoriza ignorar defeitos identificados. | P-012 |
| Retomar pedidos por conversa, recalcular recortes e permitir restauração. | Conservação foi aprovada; essas operações não foram. | P-008 |
| Manter fórmulas, unidades, filtros, denominadores e população de cada métrica em estrutura técnica padronizada. | Detalhamento existente nas skills; esquema persistido e campos obrigatórios ainda não aprovados. | P-009, P-016 |

## 15. Critérios de aceite da base confirmada

Os critérios desta seção não resolvem pendências de extensão, limites ou política. Quando uma capacidade depende dessas escolhas, o critério só pode ser executado com uma entrada pertencente ao suporte efetivamente acordado.

### CA-001 — Um arquivo CSV

**Dado** um CSV legível pertencente ao suporte definido, **quando** o usuário solicitar uma análise, **então** o arquivo deve poder participar do processamento e do histórico da análise. Relaciona-se a RF-001 e RF-016.

### CA-002 — Arquivo Excel

**Dado** um arquivo Excel pertencente ao suporte a ser definido em P-001, **quando** for enviado para análise, **então** a aplicação deve poder analisar seus dados. O aceite fica bloqueado enquanto não houver definição de extensões e estruturas suportadas. Relaciona-se a RF-002.

### CA-003 — Tema diferente de e-commerce

**Dado** um conjunto tabular de outro tema, **quando** uma análise for solicitada, **então** a aplicação deve selecionar análises relacionadas àquele conjunto, sem exigir colunas de vendas, receita ou pedidos. Relaciona-se a RF-003 e RN-001.

### CA-004 — Pergunta específica

**Dado** um pedido com pergunta que pode ser respondida pelos arquivos, **quando** a análise direcionada for concluída, **então** seus resultados devem responder à pergunta e não somente apresentar uma varredura genérica. Relaciona-se a RF-004.

### CA-005 — Exploração sem pergunta específica

**Dado** um pedido de exploração geral acompanhado dos arquivos, **quando** for iniciado, **então** a aplicação deve aceitar a intenção e selecionar análises para identificar achados, sem rejeitar o pedido exclusivamente pela ausência de pergunta específica. Relaciona-se a RF-005 e RN-002.

### CA-006 — Uso sem programação

**Dado** o público inicial, **quando** percorrer o fluxo de entrada e recebimento da entrega, **então** não deve ser obrigado a escrever ou executar código. Relaciona-se a RF-021 e RNF-001.

### CA-007 — Arquivos relacionados

**Dado** um conjunto de tabelas relacionadas e uma pergunta cuja resposta exige cruzá-las, **quando** a análise for concluída, **então** deve considerar essas relações e não substituir a resposta pela análise do primeiro arquivo isolado. Relaciona-se a RF-007 e RN-003. O suporte à cardinalidade específica depende de P-003.

### CA-008 — Formato do relatório

**Dado** um pedido de relatório, **quando** houver entrega final, **então** deve existir um arquivo PDF contendo a interpretação da análise. Entregar somente Markdown ou HTML reprova o critério. Relaciona-se a RF-009 e RN-004.

### CA-009 — Formato do dashboard

**Dado** um pedido de dashboard, **quando** houver entrega final, **então** deve existir um HTML que apresente as visualizações. Uma captura de tela ou PDF isolado reprova o critério. Relaciona-se a RF-010 e RN-005.

### CA-010 — Ausência de narrativa no HTML

**Dado** um dashboard gerado, **quando** seu conteúdo for inspecionado, **então** não deve conter parágrafos interpretativos, conclusões, recomendações ou cards de insights. Relaciona-se a RN-006.

### CA-011 — Interpretação em outros componentes

**Dado** um título ou tooltip que apresenta uma conclusão sobre os resultados, **quando** a revisão ocorrer, **então** esse conteúdo deve ser apontado como violação mesmo que não esteja em um parágrafo. Títulos descritivos, valores e rótulos operacionais permanecem permitidos. Relaciona-se a RN-006.

### CA-012 — Ambas as entregas

**Dado** um pedido de relatório e dashboard, **quando** concluído, **então** devem existir PDF e HTML respeitando seus respectivos contratos. Um único formato alternativo não satisfaz o pedido. Relaciona-se a RF-008 e RN-007.

### CA-013 — Insights na exploração geral

**Dado** um pedido de exploração com insights, **quando** PDF e HTML forem produzidos, **então** a interpretação dos achados deve constar no PDF e não no HTML. Relaciona-se a RN-008.

### CA-014 — Checagem específica de formatos

**Dado** um arquivo gerado em formato incorreto ou um dashboard com interpretação, **quando** o orquestrador revisar a entrega, **então** deve apontar a violação e encaminhar correção, mesmo que os valores numéricos estejam certos. Relaciona-se a RF-013 e RN-009.

### CA-015 — Encaminhamento de defeito

**Dado** um problema localizado no resultado final, **quando** o revisor o registrar, **então** deve indicar o defeito e o agente responsável pela correção. Relaciona-se a RF-014.

### CA-016 — Verificação após correção

**Dado** um problema encaminhado e uma nova versão devolvida pelo produtor, **quando** ocorrer nova revisão, **então** o orquestrador deve verificar se o problema foi resolvido antes de considerá-lo encerrado. Relaciona-se a RF-015.

### CA-017 — Defeito ainda presente

**Dado** um defeito que continua presente após uma tentativa de correção, **quando** a decisão de qualidade for tomada, **então** a entrega não deve ser apresentada como aprovada. O comportamento após esgotamento das tentativas depende de P-012. Relaciona-se a RN-010.

### CA-018 — Storytelling do PDF

**Dado** um relatório que lista números sem relacioná-los ao objetivo nem desenvolver sua interpretação, **quando** o revisor avaliar o storytelling, **então** deve apontar o problema e solicitar correção ao responsável pelo relatório. Relaciona-se a RN-011 e RNF-003.

### CA-019 — Revisão visual

**Dado** um dashboard com monotonia que prejudica a diferenciação, hierarquia confusa ou valores ilegíveis, **quando** a revisão ocorrer, **então** devem ser indicadas as ocorrências concretas e encaminhadas ao responsável pela apresentação. O critério não obriga multicolorir uma única série sem motivo. Relaciona-se a RF-012 e RN-012.

### CA-020 — Arquivos conservados

**Dada** uma análise executada, **quando** seus dados conservados forem consultados, **então** deve ser possível identificar e recuperar os arquivos utilizados nessa análise. Relaciona-se a RF-016 e RN-013. A consulta pode ser técnica; uma tela de histórico ainda não foi definida.

### CA-021 — Pedido e esclarecimentos conservados

**Dado** um pedido que recebeu esclarecimentos, **quando** o histórico da análise for consultado, **então** devem estar disponíveis o pedido e os esclarecimentos associados. Relaciona-se a RF-017.

### CA-022 — Definições e tratamentos conservados

**Dada** uma análise com métricas definidas e tratamentos executados, **quando** seu histórico for consultado, **então** deve ser possível localizar essas definições e tratamentos. Registrar uma transformação apenas planejada como executada não atende ao critério. Relaciona-se a RF-018.

### CA-023 — Versões de resultados e entregas

**Dada** a produção de uma nova versão de um resultado ou entrega de uma análise, **quando** as versões conservadas forem consultadas, **então** elas devem ser distinguíveis e associadas à análise correspondente. A política de quais intermediários conservar depende de P-008. Relaciona-se a RF-019.

### CA-024 — Definições do conjunto analisado

**Dados** dois conjuntos de temas diferentes, **quando** forem analisados, **então** métricas, filtros e unidades do primeiro não devem ser impostos ao segundo somente porque foram usados em uma demonstração anterior. Relaciona-se a RN-014.

### CA-025 — Organização das skills

**Dado** o pacote de competências do projeto, **quando** suas instruções forem utilizadas por outro desenvolvedor ou IA, **então** cada skill deve possuir `SKILL.md` identificável, responsabilidade definida e referências necessárias para executar sua tarefa, sem depender de reconstruir nomes ou conceitos a partir da conversa. Relaciona-se a RF-020 e RNF-005.

### CA-026 — Métricas além de posição e dispersão

**Dado** um conjunto com ao menos uma medida, uma categoria e uma data, **quando** for pedida exploração geral, **então** o plano e os resultados devem incluir indicadores de qualidade (M1) e pelo menos uma métrica de composição ou concentração (M5/M6), uma de evolução no tempo (M7) e uma comparação com referência (M8), cada uma com fórmula, população, n e origem. Relaciona-se a RF-022 e RN-016.

### CA-027 — Tabela dividida em vários arquivos

**Dado** três CSVs com o mesmo esquema, um por mês, **quando** forem enviados juntos, **então** a aplicação deve reconhecê-los como partições, empilhá-los com a coluna de origem, conferir que o total de linhas é a soma das partes e analisar o conjunto como uma tabela. Relaciona-se a RF-023 e RN-017.

### CA-028 — Descoberta de ligações sem informação do usuário

**Dado** arquivos com uma chave comum não informada pelo usuário (inclusive com nomes de coluna diferentes), **quando** forem ingeridos, **então** o mapa de ligações deve apresentar a relação com contenção, cardinalidade observada e percentual de órfãos. Relaciona-se a RF-024 e RN-018.

### CA-029 — Arquivos independentes não são ligados

**Dado** dois arquivos sem valores de chave em comum, **quando** forem analisados juntos, **então** nenhuma ligação forte deve ser criada e nenhum resultado deve depender de junção entre eles. Relaciona-se a RN-003 e RN-018.

### CA-030 — Origem e divergência entre fontes

**Dado** dois arquivos de origens diferentes que trazem a mesma medida para as mesmas entidades, **quando** a análise usar essa medida, **então** cada resultado deve citar arquivo, aba e coluna de origem, e a divergência entre as fontes deve ser medida e reportada no resumo da execução. Relaciona-se a RF-025 e RN-019.

### CA-031 — Achados orientados à decisão

**Dado** um relatório PDF gerado, **quando** for revisado, **então** cada achado principal deve trazer magnitude, comparação com uma referência e indicação de confiabilidade (n, ausências ou sensibilidade). Relaciona-se a RF-022 e RN-016.

### 15.1. Cenários técnicos existentes que ainda exigem ratificação

O pacote prevê verificações de linhas malformadas, cabeçalhos repetidos, chaves nulas, expansão de joins, base inteiramente ausente, divisão por zero, formatos ambíguos, falta de ferramenta de renderização e ausência de inspeção. Esses casos devem ser usados na decisão sobre P-003 a P-005, P-012, P-013 e P-016.

Não foi criado um critério de aceite obrigatório que aprove automaticamente excluir linhas, imputar dados, escolher uma relação ambígua ou entregar parcialmente. As políticas correspondentes ainda não foram decididas.

## 16. Pendências e decisões em aberto

| ID | Decisão necessária | Informação existente | Impacto da lacuna |
|---|---|---|---|
| P-001 | Quais extensões e estruturas Excel serão aceitas? Como lidar com abas, tabelas múltiplas, fórmulas, subtotais, células mescladas, arquivos protegidos e macros? | Excel foi confirmado; a ingestão passa a ser `ingest-tabular`. Proposta para o MVP em 16.3. | Bloqueia contrato e aceite completos de RF-002. |
| P-002 | Quantidade/tamanho máximos de arquivos e suporte a convenções CSV. | Um ou mais arquivos; limites e convenções não definidos. | Bloqueia validação de entrada e dimensionamento. |
| P-003 | Quais relações serão suportadas no MVP? Como tratar chaves ambíguas, relações de muitos para muitos e partições com esquema parecido? | Múltiplos arquivos relacionados, partições e descoberta de ligações confirmados (RF-023, RF-024). Regras e limiares propostos em 12.8. | Bloqueia definição completa dos casos relacionais aceitos. |
| P-004 | Qual autonomia para corrigir leitura, excluir registros, imputar ausências, resolver duplicidades e preservar originais? | Divisão entre ajustes automáticos e tratamentos sujeitos a aprovação foi proposta e não respondida. | Impede implementar tratamento automático como se já estivesse autorizado. |
| P-005 | Quando pedir esclarecimento? Há aprovação de plano? O que fazer com contexto insuficiente? | Dois modos confirmados; perguntas somente para ambiguidades materiais são proposta. | Afeta fluxo, pausas e experiência do usuário. |
| P-006 | Como serão identidade, acesso, propriedade de análises e isolamento entre usuários? | Públicos definidos, permissões não definidas. | Bloqueia arquitetura completa de acesso em produção. |
| P-007 | Por quanto tempo conservar arquivos e histórico? Quem pode excluir e o que ocorre com as versões? | Conservação confirmada, sem prazo ou política de exclusão. | Bloqueia ciclo de vida dos dados. |
| P-008 | Quais intermediários versionar? Haverá retomada, restauração, reanálise e interface de histórico? | Versões de resultados e entregas confirmadas; operações sobre elas não foram aprovadas. | Afeta armazenamento e funcionalidades após a entrega. |
| P-009 | Qual banco/armazenamento e qual modelo físico? Quais identificadores, obrigatoriedades e restrições? | Informações a conservar definidas; nenhum esquema aprovado. | Bloqueia implementação definitiva da persistência. |
| P-010 | Quem decide número e organização de PDFs/HTMLs? Há abas, múltiplas visões ou arquivos separados? | Um relatório e liberdade para dashboards foram pedidos na demonstração de e-commerce; um HTML com visões foi sugerido como padrão. | Evita transformar uma escolha do exemplo em limite universal. |
| P-011 | ~~Como comunicar limitações e perguntas quando somente dashboard for solicitado?~~ | **Resolvida na revisão 1.2:** resumo da execução separado do HTML (RN-015). | Nenhum. |
| P-012 | Quais critérios obrigatórios de qualidade, categorias de defeito e limite de correções? Como encerrar sem aprovação? | Revisão exigente confirmada; três ciclos no pacote e distinção entre defeito e preferência não foram ratificados como política. | Bloqueia conclusão automática e controle de custo do ciclo de revisão. |
| P-013 | Como tratar arquivo inválido, falha parcial, falta de ferramenta e parte do pedido inviável? | Skills têm estados internos; política de lote/entrega parcial não foi aprovada. | Bloqueia comportamento completo de falhas e exceções da aplicação. |
| P-014 | Quais capacidades adicionais ficam explicitamente fora do MVP? | Escopo confirmado é descritivo; lista de exclusões do documento inicial era proposta. | Evita prometer inferência, previsão ou integrações sem definição. |
| P-015 | Quais controles serão oferecidos ao perfil de analista e em qual versão? | Intenção de atender ambos os perfis confirmada; primeiro público é o não programador. | Afeta evolução, sem obrigar modo avançado imediato. |
| P-016 | Quais padrões de métricas, quantis, desvio-padrão e seleção/priorização de achados serão fixos? Como registrar evidências? | Abrangência confirmada (RF-022); catálogo, limiares e convenções propostos em 12.7. | Bloqueia contrato analítico definitivo e parte da validação automática. |
| P-017 | Qual arquitetura de execução e produção: provedor de IA, fila, hospedagem, custos, tempo e cancelamento? | CrewAI e n8n descartados; agentes LLM com código próprio confirmados; provedor Claude ou OpenAI confirmado. Fila, hospedagem e custos seguem em proposta (16.3). | Bloqueia implantação e operação com limites definidos. |
| P-018 | Qual desenho de telas e distribuição de validações entre interface, serviço e banco? | Interações principais definidas; sem telas, rotas ou responsabilidades técnicas aprovadas. | Bloqueia detalhamento final da interface e das validações por camada. |
| P-019 | De onde vêm metas e referências para as métricas de comparação (M8)? | Proposta MVP: usar colunas de meta existentes nos dados ou valores informados pelo usuário no pedido; sem isso, comparar com período anterior, média geral ou outros grupos. Nunca inventar meta. | Sem meta, atingimento e lacuna não são calculados. |
| P-020 | Quando duas fontes divergem sobre a mesma medida ou atributo, qual prevalece? | Proposta MVP: nenhuma prevalece automaticamente; a divergência é medida (M14) e reportada; se afetar materialmente a resposta, o usuário escolhe a fonte. | Afeta resultados que dependem de fontes sobrepostas. |

### 16.1. Correções e substituições resolvidas

| Ponto anterior | Definição vigente |
|---|---|
| Entrada tratada inicialmente apenas como CSV | A entrada também deve aceitar Excel; RF-002, com suporte detalhado ainda em aberto. |
| Exemplos e artefatos focados em e-commerce | O produto é multidomínio; RN-001 e RN-014. |
| Usuário precisaria sempre formular uma pergunta | Exploração geral sem pergunta específica está confirmada; RF-005 e RN-002. |
| “Análise” sem formato final definido | Relatório é PDF; dashboard é HTML; RN-004 e RN-005. |
| Possibilidade de interpretar resultados no dashboard | Narrativa interpretativa no HTML é proibida; RN-006 e RN-008. |
| Histórico tratado como sugestão | Conservação dos quatro grupos de informação foi expressamente aprovada; RF-016 a RF-019. |
| Público apresentado como escolha exclusiva entre negócio e analista | Primeiro público é o de negócio sem programação; intenção final é atender ambos. |
| CrewAI e n8n considerados para orquestração | Descartados; agentes LLM com código próprio (revisão 1.2, seção 12.5). |
| Ingestão restrita a `ingest-csv` | Renomeada para `ingest-tabular`, cobrindo CSV e Excel (revisão 1.2, seção 12.1). |
| Canal de limitações indefinido quando só há dashboard | Resumo da execução (revisão 1.2, RN-015). |
| Capacidade descritiva centrada em posição e dispersão | Catálogo abrangente e orientado à decisão (revisão 1.3, RF-022, RN-016, seção 12.7). |
| Cada arquivo tratado implicitamente como uma tabela | Partições empilhadas e ligações descobertas entre arquivos (revisão 1.3, RF-023, RF-024, RN-017, seção 12.8). |
| Caminho local `E:\UFG\Especializacao\Projetos\DataAI` | Caminho correto: `E:\UFG\Especializacao\01 - Projetos\01- DataAI`. |

### 16.2. Tensões ainda não resolvidas

1. **Entrada multidomínio versus significado das métricas:** é obrigatório aceitar diferentes temas, mas não foi aprovada a política de esclarecimento quando o significado não puder ser obtido dos arquivos. P-005 e P-016.
2. **Excel confirmado versus ingestão existente:** a ingestão foi unificada em `ingest-tabular`; resta fechar a abrangência do suporte Excel. P-001.
3. **Rigor de qualidade versus encerramento:** corrigir problemas está confirmado, mas teto de ciclos e tratamento de sugestões opcionais ainda não estão fechados. P-012.
4. **Conservar histórico versus duração e acesso:** a conservação está aprovada, mas acesso, exclusão, prazo e armazenamento não foram definidos. P-006 a P-009.
5. ~~**Insights versus pedido somente de HTML.**~~ Resolvida: o resumo da execução (RN-015) é o canal das limitações; interpretações continuam fora do dashboard.

### 16.3. Triagem das pendências para o MVP (revisão 1.2, P-003 e P-016 atualizadas na 1.3)

O MVP é uma versão inicial, executada localmente por um único usuário, cujo objetivo é demonstrar o fluxo completo: entrada, análise descritiva, PDF/HTML, revisão de qualidade e histórico. Com esse recorte, as pendências se dividem em três grupos. As decisões abaixo são a **proposta para o MVP**, com a qual o usuário concordou em linhas gerais; cada item pode ser ajustado antes da implementação da parte afetada.

**A. Decidir agora (bloqueiam o MVP)**

| ID | Decisão proposta para o MVP |
|---|---|
| P-001 | Aceitar somente `.xlsx`. Cada aba é tratada como um dataset, com cabeçalho na primeira linha e uma tabela por aba. Fórmulas são lidas pelo valor calculado. Várias tabelas na mesma aba, células mescladas no cabeçalho, linhas de subtotal, arquivos protegidos por senha, `.xls` e `.xlsm` ficam fora: a ingestão informa o bloqueio e não tenta adivinhar a estrutura. |
| P-002 | Até 10 arquivos por análise e até 50 MB somados. CSV com detecção de encoding (UTF-8 e Latin-1) e de delimitador (vírgula, ponto e vírgula e tabulação). Valores fora disso são informados ao usuário. |
| P-003 | Suportar relações um para um, um para muitos e muitos para um, com chave simples ou composta (até 3 colunas), descobertas e verificadas pelos critérios de 12.8 (contenção, cardinalidade, integridade). Muitos para muitos só por tabela ponte detectada. Muitos para muitos direto, chaves ambíguas, caminhos alternativos e ligações apenas "prováveis" geram pedido de esclarecimento. Partições com esquema idêntico são empilhadas automaticamente; com esquema parecido, geram pergunta com o mapeamento proposto. |
| P-004 | Ajustes de leitura verificáveis (encoding, delimitador, tipos, datas, separador decimal) são feitos automaticamente e registrados. Excluir registros, imputar ausências ou resolver duplicidades ambíguas exige autorização do usuário. Os arquivos originais são preservados sem alteração; os tratamentos operam sobre cópias de trabalho. |
| P-005 | Perguntar ao usuário somente quando a ambiguidade puder alterar materialmente a resposta. Não há aprovação obrigatória do plano. Com contexto insuficiente para uma ambiguidade não material, a análise segue com a suposição registrada no resumo da execução (RN-015). |
| P-012 | Até 3 ciclos de revisão. Problemas são classificados como **defeito** (impede a aprovação) ou **sugestão** (opcional). Se um defeito persistir após o terceiro ciclo, a entrega é disponibilizada marcada como "não aprovada", com a lista de defeitos no resumo da execução. Nunca é apresentada como aprovada. |
| P-013 | Arquivo inválido ou não suportado: informar e prosseguir com os demais somente se o pedido não depender dele; caso contrário, bloquear a análise. Se só parte do pedido for viável, entregar a parte viável identificada como parcial. Falta de ferramenta de geração ou renderização bloqueia a entrega afetada. |
| P-016 | Adotar o catálogo da seção 12.7 (15 famílias, de qualidade a sensibilidade) e as convenções do pacote: desvio-padrão com `ddof=1`, quantis pelo método linear, precisão interna completa e arredondamento só na apresentação. A seleção dos achados prioriza os que respondem ao objetivo e, na exploração geral, os que cobrem mais perguntas de decisão (12.7.2) com maior magnitude. Todo número cita a origem do cálculo. |
| P-017 | Execução local em Python, com agentes LLM coordenados pelo código da aplicação (sem CrewAI e sem n8n). Sem fila nem hospedagem no MVP: uma análise por vez. **Provedor decidido: Claude ou OpenAI** (escolha automática pela chave configurada; modelo configurável). Registrar o custo de tokens por análise para servir de base a limites futuros. |

**B. Versão simplificada no MVP**

| ID | Simplificação proposta |
|---|---|
| P-007 | Conservar arquivos e histórico por tempo indeterminado na máquina local. A exclusão é manual, removendo a pasta da análise. |
| P-008 | Conservar a versão de cada resultado e entrega produzida em cada ciclo de revisão. Retomada, restauração e reanálise ficam fora do MVP. |
| P-009 | Armazenamento em sistema de arquivos: uma pasta por análise contendo originais, cópias de trabalho, resultados, entregas e um manifesto JSON que associa todos os itens de histórico (RF-016 a RF-019). Sem banco de dados no MVP. |
| P-010 | No máximo um PDF e um HTML por solicitação. O HTML pode ter mais de uma visão quando os dados pedirem. |
| P-018 | Interface mínima: uma tela para enviar arquivos, escrever a pergunta ou pedir exploração e escolher a entrega, mais a área de resultado com o resumo da execução. Validações de entrada ficam no serviço. |

**C. Fora do MVP**

| ID | Motivo |
|---|---|
| P-006 | Uso local por um único usuário; identidade, acesso e isolamento entram antes de qualquer uso por terceiros. |
| P-014 | Ficam fora do MVP: modelos preditivos, testes de hipóteses, inferência causal, conexão direta a bancos e sistemas externos, atualização recorrente e upload de arquivos compactados. Não estão proibidos em versões futuras. |
| P-015 | Controles específicos para analistas entram em versão posterior. |

P-011 foi resolvida pela RN-015.

## 17. Exemplo de validação já realizado e seus limites

A demonstração utilizou nove CSVs relacionados do arquivo `ecommerce.rar`: `Categories.csv`, `Customers.csv`, `Geolocation.csv`, `Order Items.csv`, `Order Payments.csv`, `Orders.csv`, `Products.csv`, `Reviews.csv` e `Sellers.csv`.

Foram produzidos `Dashboard_Ecommerce.html`, com visões Comercial e Entregas e avaliações, e `Relatorio_Ecommerce.pdf`, com sete páginas. Esse trabalho é evidência de uma execução assistida e serve como caso de teste para relações, entregas e revisão.

Não comprova que o serviço DataAI está implantado, que o catálogo executa sozinho, que Excel já funciona ou que qualquer formato tabular arbitrário é automaticamente interpretável. Não autoriza fixar no produto as colunas, filtros, período, unidade monetária ou quantidade de páginas dessa demonstração.

O uso de `.rar` nessa conversa foi um meio de fornecer a base de teste, não decisão de oferecer upload de arquivos compactados na aplicação.

## 18. Verificação desta consolidação

- Foram contempladas as decisões confirmadas sobre público, CSV/Excel, múltiplos arquivos, temas distintos, análise direcionada, exploração geral, PDF/HTML, revisão crítica, design e histórico.
- As correções mais recentes prevalecem e estão registradas na seção 16.1.
- Sugestões não respondidas, especialmente autonomia de tratamento, não foram promovidas a regras aprovadas.
- O modelo físico e as permissões não foram inventados.
- Nomes de skills, perfis, contratos e pasta local existentes foram preservados.
- Parâmetros da demonstração não foram convertidos em regras universais.
- Estados de skills foram separados dos estados ainda indefinidos da aplicação.
- Os critérios de aceite estão vinculados à base confirmada e explicitam dependências de decisões pendentes.
- CrewAI e n8n foram descartados (revisão 1.2). Não foi presumida escolha definitiva de banco, provedor de IA ou hospedagem.
- Revisão 1.3: a abrangência das métricas, as partições, a descoberta de ligações e as origens diferentes foram confirmadas pelo usuário (RF-022 a RF-025, RN-016 a RN-019); catálogo, limiares e pesos ficaram marcados como proposta MVP (P-003, P-016, P-019, P-020).
- As lacunas que impedem partes da implementação estão localizadas na seção 16. Este documento não declara prontas as partes que dependem dessas decisões.

## 19. Histórico deste documento

| Versão | Data | Alteração |
|---|---|---|
| 1.0 | 24/10/2026 | Consolidação dos requisitos confirmados, referências existentes, propostas e pendências da conversa. |
| 1.1 | 24/10/2026 | Atualização da referência ao `DatAI_Definicao_MVP.pdf` para a versão 0.2 e esclarecimento do papel de cada artefato. Nenhum requisito de negócio ou decisão pendente foi alterado. |
| 1.2 | 31/10/2026 | CrewAI e n8n descartados em favor de agentes LLM com código próprio; `ingest-csv` renomeada para `ingest-tabular` (CSV e Excel); criada a RN-015 (resumo da execução), resolvendo P-011; corrigido o caminho da pasta local; adicionada a triagem das pendências para o MVP (16.3). |
| 1.3 | 31/10/2026 | Métricas abrangentes e orientadas à decisão (RF-022, RN-016, catálogo de 15 famílias em 12.7); tabelas em vários arquivos, partições e descoberta de ligações entre arquivos (RF-023, RF-024, RN-017, RN-018, seção 12.8); origens diferentes com linhagem e reconciliação (RF-025, RN-019); implementação de referência no repositório (12.9); critérios CA-026 a CA-031; novas pendências P-019 e P-020; P-003 e P-016 revistas. |
| 1.4 | 31/10/2026 | Identidade visual aprovada (RF-012, seção 12.10) e skill `brand-identity`. |
