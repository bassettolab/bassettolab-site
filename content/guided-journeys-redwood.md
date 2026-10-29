---
title: "Oracle Cloud Redwood: Guided Journeys tradicionais e com agentes de IA"
date: 2026-10-28
description: "Guia prático de configuração de Guided Journeys para documentos, relatórios e agentes de IA no Self Service Procurement Redwood."
categories: ["TI", "Oracle", "Cloud"]
tags: ["Oracle Fusion Cloud", "Redwood", "Guided Journeys", "Procurement", "AI Agent Studio", "Visual Builder Studio"]
draft: false
toc: true
---

## O que são os dois cenários?

No Oracle Fusion Cloud Redwood, **Guided Journey** é um recurso de orientação contextual inserido em páginas da aplicação. Os documentos utilizados neste tutorial apresentam duas aplicações do mesmo recurso, e não dois produtos diferentes:

| Cenário | Objetivo | Conteúdo |
| --- | --- | --- |
| **Journey informativo** | Orientar o usuário durante a execução de uma atividade | PDF, relatórios BI Publisher/OTBI, análises, vídeo e links externos |
| **Journey com agente de IA** | Oferecer consultas interativas no contexto da tela | Tarefa do tipo Agent associada a um agente publicado no AI Agent Studio |

O procedimento demonstrado utiliza a página inicial de **Self Service Procurement / Purchase Requisitions** do Redwood. A abordagem pode ser aplicada a outras páginas de Procurement e SCM **desde que exista uma propriedade de Journey suportada naquela página**. A Oracle esclarece que não é possível associar o recurso por esse método quando a página ou seção não possui a propriedade correspondente.

## Onde utilizar

- **Self Service Procurement:** manual para solicitação de compras, consulta de requisições pendentes, vídeos de treinamento e dúvidas sobre aprovações.
- **Purchasing e outros fluxos de Procurement:** políticas, instruções operacionais e consultas contextuais nas páginas compatíveis.
- **SCM (Inventory, Order Management e outras áreas):** conteúdo de apoio contextual nas páginas Redwood que disponibilizem propriedades de Guided Journey.
- **Agente de IA em Procurement:** perguntas como situação da requisição, aprovador pendente e número de requisições aguardando aprovação, conforme as ferramentas e autorizações do agente.

O Journey não substitui o fluxo transacional nem concede automaticamente acesso a dados: as permissões do usuário, do relatório e do agente continuam aplicáveis.

## Fluxo 1 — Journey informativo

```text
My Routines > Journeys Setup > Guided Journey
                     |
                Create > Name + Code
                     |
                 Create Draft
                     |
              Add Tasks (1..N)
         /      |       |        \
     Document  Report  Analytics  Video / External URL
         \      |       |        /
          Salvar e revisar traduções
                     |
             Preview e validação
                     |
        Registrar o código do Journey
                     |
Redwood > Edit Page in Visual Builder Studio
                     |
 Page Properties > Guided Journey Code
                     |
              Preview > Publish
```

### 1. Criar o Journey

1. Entre em **My Routines > Journeys Setup > Guided Journey**.
2. Selecione **Create**.
3. Informe **Name** e **Code**. Como exemplo genérico, utilize *Guia de Requisições* e `GUIA_REQUISICOES`.
4. Clique em **Create Draft**.
5. Na seção **Tasks**, clique em **Add** para adicionar as tarefas.

Para implementações SCM/Procurement, a documentação Oracle também descreve o acesso a **Setup and Maintenance > Application Extensions > Guided Journeys**, a partir de um offering de SCM ou Procurement.

### 2. Configurar tarefas

**Document:** selecione `Task Type = Document`, atribua nome, descrição, instruções e anexe o PDF. É possível anexar um manual genérico de requisições. Depois de salvar, utilize **Translation Editor** para localizar os textos nos idiomas habilitados (o arquivo demonstra inglês, português e espanhol).

**Report:** selecione `Task Type = Report` e informe o caminho de um relatório acessível ao usuário. Exemplo ilustrativo (substituir pelo caminho real do catálogo autorizado):

```text
/Custom/Procurement/EXEMPLO_RELATORIO.xdo
```

O exemplo é de um relatório com extensão `.xdo` (BI Publisher); não confundir o caminho com uma análise OTBI.

**Analytics:** selecione `Task Type = Analytics`, `Type of Analysis = OTBI Analysis` e indique o caminho da análise no catálogo compartilhado:

```text
/shared/Custom/Procurement/EXEMPLO_ANALISE
```

**Video:** selecione `Task Type = Video`, `Video Type = Embedded URL` e informe uma URL de incorporação permitida.

**External URL:** selecione `Task Type = External URL` e informe a página de apoio, por exemplo a [biblioteca de vídeos Oracle Procurement 26C](https://docs.oracle.com/en/cloud/saas/procurement/26c/videos.html).

No painel **Advanced** é possível configurar imagem de fundo e, conforme o tipo, rótulos das ações. Cada tarefa pode ser revisada individualmente na pré-visualização. Os relatórios e vídeos devem ser validados na instância em que serão utilizados.

### 3. Testar e inserir no Redwood

1. Utilize **Preview** no Journey para conferir cada tarefa.
2. Anote o **Code** (no exemplo, `GUIA_REQUISICOES`).
3. Abra a página Redwood de **Self Service Procurement**.
4. No menu **Settings and Actions**, selecione **Edit Page in Visual Builder Studio**.
5. No projeto/extensão, utilize **Express mode**.
6. Em **Page Properties**, procure a propriedade identificada na interface como **Redwood Self Service Procurement Homepage Guided Journey Code** (a nomenclatura técnica varia entre as páginas) e insira o código.
7. Revise com **Preview** e publique a alteração com **Publish**.

Na documentação de SCM, propriedades genéricas de associação podem aparecer como `journeyCode` (nível da página) ou `sectionNameJourneyCode` (nível de seção). Elas precisam efetivamente existir na página de destino; não se deve inventar uma propriedade.

## Fluxo 2 — Journey com agente de IA

```text
Configurações de segurança do AI Agent Studio
                     |
       Roles de administrador e usuário
                     |
       AI Agent Studio > Marketplace
                     |
     Copiar Purchase Requisition Status Advisor
                     |
   Ajustar perguntas e testar > Publish Agent
                     |
  Habilitar tarefas Agent em Guided Journeys
                     |
          Criar Guided Journey
                     |
     Task Type = Agent > selecionar agente
                     |
            Salvar e ativar
                     |
      Redwood > Visual Builder Studio
                     |
  Guided Journey Code > Preview > Publish
```

### 1. Segurança e habilitação inicial

Na tarefa **Setup and Maintenance > Manage Administrator Profile Values**, procure a opção:

```text
ORA_ASE_SAS_INTEGRATION_ENABLED = Yes (Site)
```

O procedimento de configuração de segurança orienta, em seguida, executar nesta ordem em **Tools > Scheduled Processes**:

1. `Import Resource Application Security Data`
2. `Import User and Role Application Security Data`

O acesso administrativo pode ser concedido por uma função administrativa adequada ou por uma **custom role** com privilégio restrito ao pilar Procurement. Exemplo genérico de função personalizada (o nome e o código abaixo são ilustrativos):

```text
Role Name: Custom Procurement AI Administrator
Role Code: CUSTOM_PRC_AI_ADMIN
Category: Common - Job Roles
```

Habilite **Enable Permission Groups** e configure as duties indicadas no material de referência:

| Área | Duty/privilege |
| --- | --- |
| Roles and Privileges | `ORA_PO_PRC_AI_AGENT_MANAGEMENT_DUTY` |
| Roles and Privileges (variante documentada) | `ORA_PO_PRC_AI_AGENT_MANAGEMENT_DUTY_HCM` |
| Roles and Permission Groups | `ORA_DR_FAI_GENERATIVE_AI_AGENT_PRC_ADMINISTRATOR_DUTY` |

**Atenção:** a variante terminada em `_HCM` aparece no roteiro de configuração; confirme sua existência, aplicabilidade e necessidade na versão do ambiente antes de adicioná-la. Evite atribuir privilégios de outros pilares sem necessidade.

Para o usuário final, o procedimento de segurança descreve a opção `ORA_HCM_VBCS_PWA_ENABLED = Y` e uma função personalizada de acesso ao chat (nome ilustrativo: `CUSTOM_AI_CHAT_USER`) com:

- `HRC_ACCESS_AI_AGENT_CHAT_PRIV` — **Access Intelligent Agent Chat**, em **Function Security Policies**.
- `ORA_DR_FAI_GENERATIVE_AI_AGENT_RUNTIME_DUTY` — em **Roles and Permission Groups**.

Essas configurações representam um exemplo técnico, não uma matriz universal de segurança. Valide os pré-requisitos exigidos pela release, o acesso aos dados e as permissões mínimas para cada perfil. Teste com um usuário sem funções administrativas.

### 2. Copiar e publicar o agente

1. Acesse **AI Agent Studio > Marketplace**.
2. Localize **Purchase Requisition Status Advisor**.
3. Selecione **Copy Template**.
4. Personalize as perguntas iniciais (*Starter Prompts*) e as ferramentas conforme o processo e as permissões disponíveis.
5. Teste o agente; depois selecione **Publish**.

Perguntas exemplificadas no documento:

```text
What is the status of purchase requisition REQ_EXEMPLO?
Who is the pending approver for requisition REQ_EXEMPLO?
How many requisitions are pending approval under my account?
```

Os identificadores são apenas placeholders ilustrativos. A resposta depende das ferramentas configuradas, dos registros existentes e da segurança.

### 3. Ativar a integração do agente com Journey

No **Manage Administrator Profile Values**, a configuração prevê habilitar:

```text
ORA_PER_AGENT_TASK_TYPE_GUIDED_JOURNEYS_ENABLED = Y
```

Em seguida:

1. Acesse **My Routines > Journey Setup > Guided Journey**.
2. Crie um Journey e uma tarefa do tipo **Agent**.
3. Na configuração da tarefa, selecione o agente publicado.
4. Salve e **Activate** o Journey.
5. Use **Preview** e confira a interação com o agente.

O procedimento `Task Type = Agent` e a ativação também são mostrados na documentação oficial de agentes SCM da Oracle.

### 4. Publicar na página Redwood

O processo de associação é o mesmo do primeiro cenário: anote o **Code** do Journey e configure-o na propriedade da página inicial de **Self Service Procurement** em **Edit Page in Visual Builder Studio > Page Properties**. Teste em Preview/Live e selecione **Publish**.

### 5. Acesso por ícone de chat (alternativa)

Um procedimento alternativo também descreve criar um atalho personalizado por um **sandbox Structure**, com **Create Page Entry**. O exemplo inclui:

```text
Name: AI Chat
Group: Shortcuts
Link Type: VB Studio Page
Focus View ID: /index.html
Web Application: ORA_FSCM_UI
Secured Resource Name: /vbcs/hcm/hcmAgentChat/access
Application Stripe: hcm
```

Essa é **uma alternativa de navegação**, e não um segundo Journey. A configuração deve ser validada na instância e na release, sobretudo os identificadores HCM utilizados para abrir o chat em contexto SCM/Procurement. Não publicar esse atalho sem testar as políticas de segurança e o acesso do usuário final.

## Pontos de atenção

- **Segurança:** funções administrativas de configuração não devem ser concedidas indiscriminadamente aos usuários finais. Teste acesso e isolamento entre pilares e objetos.
- **Publicação em duas camadas:** criar/ativar o Journey não basta; a página Redwood também precisa ter o código configurado e a extensão publicada.
- **Disponibilidade por página:** se a propriedade de Journey não existir, o encaixe direto não é suportado naquela página.
- **Permissões de conteúdo:** PDF, catálogo BI, URLs externas e agente devem estar acessíveis ao público-alvo.
- **Versionamento:** nomes de menus e propriedades variam conforme a release. Os documentos exemplificam configurações específicas; revise em homologação antes de replicá-las em produção.

## Documentação e referências

- [Oracle — Guided Journeys no Fusion SCM e Procurement](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faicf/guided-journeys.html)
- [Oracle — Redwood: SCM AI Agents (exemplo de agente em Guided Journey)](https://docs.oracle.com/en/cloud/saas/readiness/scm/25a/plm25a/25A-plm-wn-f36914.htm)
- [Oracle — Extending Redwood Applications for HCM and SCM Using Visual Builder Studio (PDF)](https://docs.oracle.com/cd/G55130_01/trans/G34703-05/extending-redwood-applications-for-hcm-and-scm-using-visual-builder-studio.pdf)
- [Oracle — Adoção de Redwood em SCM e Procurement](https://docs.oracle.com/en/cloud/saas/readiness/redwood-adoption/raoac/rw-scm.html)

**Referências:** documentação pública da Oracle listada acima. Caminhos de catálogo, nomes de funções personalizadas, códigos de Journey e identificadores de requisição são exemplos genéricos; substitua-os pelos valores adequados ao ambiente autorizado.
