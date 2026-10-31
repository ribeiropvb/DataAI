# DataAI — Especificação consolidada da aplicação

**Arquivo:** `specs.md`  
**Versão do documento:** 1.2  
**Data da consolidação:** 24/10/2026 (revisão 1.2 em 31/10/2026)  
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

## 3. Escopo

### 3.1. Funcionalidades confirmadas para a primeira versão

- Recebimento de um ou mais arquivos CSV ou Excel.
- Análise direcionada por pergunta do usuário.
- Exploração geral dos dados sem exigir uma pergunta específica.
- Análises descritivas e identificação de achados sobre os dados.
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

A produção dos dashboards deve contemplar composição visual, uso de cores, hierarquia e legibilidade. A expectativa inclui corrigir resultados monótonos ou visualmente fracos. Não há paleta de marca definitiva acordada.

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

Os oito perfis declarativos estão em `agents/*.yaml`. Eles não criam agentes executáveis automaticamente. A execução dos agentes será feita pela própria aplicação, sem CrewAI (ver 12.5).

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
| GitHub | Considerado para organizar/versionar skills. Não foi indicado repositório definitivo. |
| Python `3.13.7` | Versão informada pelo usuário no ambiente local. Não é, por si só, decisão de runtime de produção nem comprovação de compatibilidade de todas as dependências. |
| VS Code | Ambiente de desenvolvimento que o usuário deseja utilizar desde o início. |
| Pasta local | `E:\UFG\Especializacao\01 - Projetos\01- DataAI`. Não é caminho do servidor de produção. |
| Modelo e provedor de IA | Não definidos. |
| Backend, frontend, banco, armazenamento, fila e hospedagem | Não definidos como arquitetura definitiva. |

**Confirmado na revisão 1.2:** o DataAI não utilizará CrewAI nem n8n. Toda a coordenação será feita por agentes baseados em LLM, chamados pelo código da própria aplicação, que fornece a eles as skills e as ferramentas (leitura de arquivos, cálculo, geração de PDF/HTML e renderização para revisão). A sugestão do pacote de usar n8n como porta de entrada fica sem efeito. Continuam em aberto o provedor e o modelo de IA (P-017).

Os códigos de entrega existentes no pacote são `output_mode=report`, `output_mode=dashboard` e `output_mode=both`. Esses valores representam a modalidade de saída; não representam análise direcionada versus exploração geral. Não há nome de campo ou enumeração técnica aprovada para esses dois modos de análise.

Nos produtores de arquivos, o pacote diferencia um intermediário de uma entrega efetivamente gerada: `stage=specification` ou `stage=artifact` no dashboard; `stage=draft` ou `stage=artifact` no relatório. Concluir uma especificação interna não satisfaz RF-009 ou RF-010. O adaptador que converteria o antigo valor `analysis` para `report` é uma proposta de compatibilidade do pacote, não requisito de migração aprovado.

### 12.6. Integrações externas e execução automática

Não foram acordadas APIs externas de dados, autenticação, e-mail, mensagens, pagamentos, agendamento ou publicação. O pedido de colocar o serviço em produção existe, mas fornecedor e condições de operação continuam pendentes.

O orquestrador deve encaminhar correções dentro do processamento da análise. Isso não estabelece integração com um gerenciador externo de tarefas.

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

### 15.1. Cenários técnicos existentes que ainda exigem ratificação

O pacote prevê verificações de linhas malformadas, cabeçalhos repetidos, chaves nulas, expansão de joins, base inteiramente ausente, divisão por zero, formatos ambíguos, falta de ferramenta de renderização e ausência de inspeção. Esses casos devem ser usados na decisão sobre P-003 a P-005, P-012, P-013 e P-016.

Não foi criado um critério de aceite obrigatório que aprove automaticamente excluir linhas, imputar dados, escolher uma relação ambígua ou entregar parcialmente. As políticas correspondentes ainda não foram decididas.

## 16. Pendências e decisões em aberto

| ID | Decisão necessária | Informação existente | Impacto da lacuna |
|---|---|---|---|
| P-001 | Quais extensões e estruturas Excel serão aceitas? Como lidar com abas, tabelas múltiplas, fórmulas, subtotais, células mescladas, arquivos protegidos e macros? | Excel foi confirmado; a ingestão passa a ser `ingest-tabular`. Proposta para o MVP em 16.3. | Bloqueia contrato e aceite completos de RF-002. |
| P-002 | Quantidade/tamanho máximos de arquivos e suporte a convenções CSV. | Um ou mais arquivos; limites e convenções não definidos. | Bloqueia validação de entrada e dimensionamento. |
| P-003 | Quais relações serão suportadas no MVP? Como tratar chaves ambíguas e relações de muitos para muitos? | Múltiplos arquivos relacionados estão confirmados; skills já verificam cardinalidade. | Bloqueia definição completa dos casos relacionais aceitos. |
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
| P-016 | Quais padrões de métricas, quantis, desvio-padrão e seleção/priorização de achados serão fixos? Como registrar evidências? | Há convenções no pacote, sem ratificação individual como política do serviço. | Bloqueia contrato analítico definitivo e parte da validação automática. |
| P-017 | Qual arquitetura de execução e produção: provedor de IA, fila, hospedagem, custos, tempo e cancelamento? | CrewAI e n8n descartados; agentes LLM com código próprio confirmados. Proposta para o MVP em 16.3. | Bloqueia implantação e operação com limites definidos. |
| P-018 | Qual desenho de telas e distribuição de validações entre interface, serviço e banco? | Interações principais definidas; sem telas, rotas ou responsabilidades técnicas aprovadas. | Bloqueia detalhamento final da interface e das validações por camada. |

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
| Caminho local `E:\UFG\Especializacao\Projetos\DataAI` | Caminho correto: `E:\UFG\Especializacao\01 - Projetos\01- DataAI`. |

### 16.2. Tensões ainda não resolvidas

1. **Entrada multidomínio versus significado das métricas:** é obrigatório aceitar diferentes temas, mas não foi aprovada a política de esclarecimento quando o significado não puder ser obtido dos arquivos. P-005 e P-016.
2. **Excel confirmado versus ingestão existente:** a ingestão foi unificada em `ingest-tabular`; resta fechar a abrangência do suporte Excel. P-001.
3. **Rigor de qualidade versus encerramento:** corrigir problemas está confirmado, mas teto de ciclos e tratamento de sugestões opcionais ainda não estão fechados. P-012.
4. **Conservar histórico versus duração e acesso:** a conservação está aprovada, mas acesso, exclusão, prazo e armazenamento não foram definidos. P-006 a P-009.
5. ~~**Insights versus pedido somente de HTML.**~~ Resolvida: o resumo da execução (RN-015) é o canal das limitações; interpretações continuam fora do dashboard.

### 16.3. Triagem das pendências para o MVP (revisão 1.2)

O MVP é uma versão inicial, executada localmente por um único usuário, cujo objetivo é demonstrar o fluxo completo: entrada, análise descritiva, PDF/HTML, revisão de qualidade e histórico. Com esse recorte, as pendências se dividem em três grupos. As decisões abaixo são a **proposta para o MVP**, com a qual o usuário concordou em linhas gerais; cada item pode ser ajustado antes da implementação da parte afetada.

**A. Decidir agora (bloqueiam o MVP)**

| ID | Decisão proposta para o MVP |
|---|---|
| P-001 | Aceitar somente `.xlsx`. Cada aba é tratada como um dataset, com cabeçalho na primeira linha e uma tabela por aba. Fórmulas são lidas pelo valor calculado. Várias tabelas na mesma aba, células mescladas no cabeçalho, linhas de subtotal, arquivos protegidos por senha, `.xls` e `.xlsm` ficam fora: a ingestão informa o bloqueio e não tenta adivinhar a estrutura. |
| P-002 | Até 10 arquivos por análise e até 50 MB somados. CSV com detecção de encoding (UTF-8 e Latin-1) e de delimitador (vírgula, ponto e vírgula e tabulação). Valores fora disso são informados ao usuário. |
| P-003 | Suportar relações um para um e um para muitos com chaves verificadas (correspondência e cardinalidade). Chaves ambíguas e relações de muitos para muitos geram pedido de esclarecimento; não são combinadas automaticamente. |
| P-004 | Ajustes de leitura verificáveis (encoding, delimitador, tipos, datas, separador decimal) são feitos automaticamente e registrados. Excluir registros, imputar ausências ou resolver duplicidades ambíguas exige autorização do usuário. Os arquivos originais são preservados sem alteração; os tratamentos operam sobre cópias de trabalho. |
| P-005 | Perguntar ao usuário somente quando a ambiguidade puder alterar materialmente a resposta. Não há aprovação obrigatória do plano. Com contexto insuficiente para uma ambiguidade não material, a análise segue com a suposição registrada no resumo da execução (RN-015). |
| P-012 | Até 3 ciclos de revisão. Problemas são classificados como **defeito** (impede a aprovação) ou **sugestão** (opcional). Se um defeito persistir após o terceiro ciclo, a entrega é disponibilizada marcada como "não aprovada", com a lista de defeitos no resumo da execução. Nunca é apresentada como aprovada. |
| P-013 | Arquivo inválido ou não suportado: informar e prosseguir com os demais somente se o pedido não depender dele; caso contrário, bloquear a análise. Se só parte do pedido for viável, entregar a parte viável identificada como parcial. Falta de ferramenta de geração ou renderização bloqueia a entrega afetada. |
| P-016 | Adotar as convenções do pacote como padrão do MVP: desvio-padrão com `ddof=1`, quantis pelo método linear, precisão interna completa e arredondamento só na apresentação. A seleção dos achados prioriza os que respondem ao objetivo e, na exploração geral, os de maior magnitude ou relevância. Todo número cita a origem do cálculo. |
| P-017 | Execução local em Python, com agentes LLM coordenados pelo código da aplicação (sem CrewAI e sem n8n). Sem fila nem hospedagem no MVP: uma análise por vez. **Falta escolher o provedor e o modelo de IA.** Registrar o custo de tokens por análise para servir de base a limites futuros. |

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
- As lacunas que impedem partes da implementação estão localizadas na seção 16. Este documento não declara prontas as partes que dependem dessas decisões.

## 19. Histórico deste documento

| Versão | Data | Alteração |
|---|---|---|
| 1.0 | 24/10/2026 | Consolidação dos requisitos confirmados, referências existentes, propostas e pendências da conversa. |
| 1.1 | 24/10/2026 | Atualização da referência ao `DatAI_Definicao_MVP.pdf` para a versão 0.2 e esclarecimento do papel de cada artefato. Nenhum requisito de negócio ou decisão pendente foi alterado. |
| 1.2 | 31/10/2026 | CrewAI e n8n descartados em favor de agentes LLM com código próprio; `ingest-csv` renomeada para `ingest-tabular` (CSV e Excel); criada a RN-015 (resumo da execução), resolvendo P-011; corrigido o caminho da pasta local; adicionada a triagem das pendências para o MVP (16.3). |
