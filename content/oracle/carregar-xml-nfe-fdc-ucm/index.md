---
title: "Oracle Cloud FDC: como carregar manualmente um XML de NF-e pelo UCM"
date: 2026-10-02
article_id: "006"
description: "Passo a passo para carregar manualmente um XML de NF-e no Oracle Cloud FDC usando o UCM, executar os processos de importação e validação e acompanhar interface exceptions, holds e o status Completed Prevalidation."
tags:
  - Oracle Cloud
  - Brazil Localization
  - FDC
  - NF-e
  - UCM
  - SEFAZ
  - Collaboration Messaging
categories:
  - Oracle
toc: true
type: post
featured: true
draft: false
---

Uma coisa simples, mas que eu sempre acabo tendo que procurar novamente: como carregar manualmente um XML de NF-e no Fiscal Document Capture (FDC) do Oracle Cloud.

Então este artigo fica como referência rápida para quando eu precisar testar uma NF-e, reproduzir um problema de integração ou simplesmente acompanhar o caminho do XML até o FDC.

A sequência principal, seguindo o fluxo documentado pela Oracle para [importação de documentos fiscais](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/import-fiscal-document.html), é:

~~~text
XML NF-e
   ↓
Oracle Content Repository / UCM
   ↓
Import Brazil Electronic Documents
   ↓
Import and Validate Electronic Fiscal Documents
   ↓
FDC
   ↓
Interface Exceptions / Holds / Validation Errors
   ↓
Completed Prevalidation
~~~

## 1. Carregar o XML no UCM

O primeiro passo é colocar o arquivo no Oracle Content Repository.

Pelo procedimento documentado pela Oracle, o caminho é:

~~~text
Navigator
> Tools
> File Import and Export
> Upload
~~~

Para esse tipo de carga, a Oracle orienta enviar um arquivo ZIP contendo um ou mais XMLs. O procedimento pode ser consultado em [Import Fiscal Document](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/import-fiscal-document.html).

Para uma NF-e recebida do fornecedor, utilizar a conta:

~~~text
scm/BrazilSEFAZSupplierMessages/import
~~~

Essa é uma das contas monitoradas pelo processo [Import Brazil Electronic Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faspc/import-brazil-electronic-documents.html).

Em alguns ambientes também é possível consultar diretamente o Content Server usando:

~~~text
https://<seu-ambiente>/cs
~~~

Isso é útil para confirmar se o arquivo realmente chegou ao UCM. Para a carga funcional, uso como referência o procedimento oficial via File Import and Export.

## 2. Executar Import Brazil Electronic Documents

Depois que o arquivo estiver no UCM, acessar:

~~~text
Navigator
> Tools
> Scheduled Processes
~~~

e executar:

~~~text
Import Brazil Electronic Documents
~~~

Esse processo busca os documentos recebidos no Oracle Content Repository e inicia o processamento das mensagens.

A documentação do [Import Brazil Electronic Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faspc/import-brazil-electronic-documents.html) mostra as duas contas usadas nesse fluxo:

~~~text
scm/BrazilSEFAZSupplierMessages/import
scm/BrazilSEFAZPartnerMessages/import
~~~

A primeira é usada para documentos recebidos de fornecedores. A segunda é usada para mensagens recebidas do provedor que faz a comunicação com a SEFAZ.

Se o arquivo estiver no UCM, mas não estiver avançando para o FDC, esse processo é um dos primeiros pontos que verifico.

## 3. Executar Import and Validate Electronic Fiscal Documents

Depois da etapa anterior, executar:

~~~text
Import and Validate Electronic Fiscal Documents
~~~

Na documentação de Scheduled Processes, esse processo trata os documentos que ainda estão na interface e também valida documentos que já foram criados no FDC. Os parâmetros estão descritos em [Import and Validate Electronic Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faspc/import-and-validate-electronic-fiscal-documents.html).

Um parâmetro importante é:

~~~text
Fiscal Documents to Validate
~~~

| Valor | O que faz |
| --- | --- |
| New | Tenta processar os documentos que ainda estão na interface |
| Existing | Valida documentos que já existem no FDC |
| All | Primeiro trata a interface e depois valida os documentos existentes |

Se nada for informado, o padrão documentado é New.

Para um teste manual em que quero processar tanto o que está parado na interface quanto o que já entrou no FDC, normalmente uso:

~~~text
Fiscal Documents to Validate = All
~~~

### Sobre o nome do processo

Algumas páginas do fluxo XML da Oracle ainda mostram:

~~~text
Import Electronic Fiscal Documents
~~~

Enquanto a documentação específica de Scheduled Processes usa:

~~~text
Import and Validate Electronic Fiscal Documents
~~~

Neste artigo uso Import and Validate Electronic Fiscal Documents, que é o nome apresentado na documentação do processo e descreve melhor o comportamento atual.

## 4. Se o XML ficar preso na interface

Um XML com problema de derivação ou validação pode não chegar a ser criado como documento fiscal.

Nesse caso, a tela correta para começar a análise é:

~~~text
Fiscal Document Capture
> Manage Interface Exceptions
~~~

A Oracle documenta essa tela em [View Interface Exceptions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fafdc/view-interface-exceptions.html).

É ali que aparecem os documentos que não conseguiram sair da interface por algum erro de processamento.

Depois de corrigir a causa, o processo pode ser executado novamente com:

~~~text
Fiscal Documents to Validate = New
~~~

ou:

~~~text
Fiscal Documents to Validate = All
~~~

## 5. Quando o documento já existe no FDC

Se o documento já foi criado, acessar:

~~~text
Fiscal Document Capture
> Manage Inbound Fiscal Documents
~~~

e localizar a NF-e.

A partir desse ponto, vale separar duas situações:

~~~text
Interface Exception
= o documento ainda não conseguiu entrar corretamente no FDC

Hold / Validation Error
= o documento já existe no FDC, mas existe alguma pendência para avançar
~~~

No documento fiscal, a região:

~~~text
Holds and Validation Errors
~~~

mostra as pendências encontradas durante a validação.

O fluxo oficial de [Import Fiscal Document](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/import-fiscal-document.html) orienta revisar essas pendências, corrigir o que for necessário, liberar os holds aplicáveis e validar novamente o documento.

## 6. Hold "Electronic fiscal documents need to be valid" e retorno da SEFAZ

Nos testes manuais que fiz com NF-e no FDC, depois que o XML é carregado e o documento passa pela validação inicial, aparece o hold:

~~~text
Electronic fiscal documents need to be valid
~~~

Na prática, esse é um comportamento esperado no fluxo eletrônico. A documentação pública da Oracle não apresenta uma lista com esse texto exato de hold, mas documenta que o [Collaboration Messaging Framework se comunica com a SEFAZ para confirmar a validade e o status do documento fiscal recebido](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fafdc/freight-fiscal-documents-for-inbound-flow.html).

Ou seja: carregar apenas o XML da NF-e não significa necessariamente que a validação eletrônica terminou. O FDC ainda precisa receber e processar a informação que confirma a situação daquele documento perante a autoridade fiscal.

No cenário que testei, o hold não é resolvido apenas executando novamente a validação do FDC. É necessário receber um novo XML/mensagem de retorno do parceiro fiscal com a confirmação relacionada à SEFAZ.

A Oracle separa esse tipo de mensagem da NF-e recebida do fornecedor. O processo [Import Brazil Electronic Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faspc/import-brazil-electronic-documents.html) monitora contas diferentes no UCM:

~~~text
XML da NF-e recebida do fornecedor
scm/BrazilSEFAZSupplierMessages/import

Retorno do parceiro fiscal / SEFAZ
scm/BrazilSEFAZPartnerMessages/import
~~~

Esse desenho faz sentido com o funcionamento do [Collaboration Messaging Framework](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faips/collaboration-messaging-framework.html), que recebe mensagens de parceiros ou provedores, transforma o XML para o formato esperado pelo Oracle e entrega a informação para a aplicação.

Então, para reproduzir manualmente o fluxo que fiz nos testes:

~~~text
1. Carregar o XML da NF-e

2. Executar:
   Import Brazil Electronic Documents

3. Executar:
   Import and Validate Electronic Fiscal Documents

4. Abrir o documento no FDC

5. O documento pode ficar com o hold:
   Electronic fiscal documents need to be valid

6. Carregar o XML/mensagem de retorno do parceiro fiscal
   em:
   scm/BrazilSEFAZPartnerMessages/import

7. Executar novamente:
   Import Brazil Electronic Documents

8. Executar novamente:
   Import and Validate Electronic Fiscal Documents

9. Validar novamente o documento no FDC
~~~

Depois que a confirmação eletrônica é processada, o FDC consegue continuar a validação do documento. Se não houver outras pendências, o fluxo pode avançar para:

~~~text
Completed Prevalidation
~~~

Um detalhe importante: o formato exato do XML de retorno depende da integração e da configuração do parceiro fiscal. O ponto principal para troubleshooting é entender que o primeiro XML representa o documento fiscal recebido, enquanto a segunda mensagem pode carregar a confirmação necessária para completar a validação eletrônica.

## 7. Validar novamente o documento

Quando o documento já está no FDC e as pendências foram resolvidas, é possível executar diretamente:

~~~text
Actions
> Validate Fiscal Document
~~~

Ou fazer a validação em lote utilizando:

~~~text
Import and Validate Electronic Fiscal Documents
~~~

De acordo com o fluxo de [Import Fiscal Document](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/import-fiscal-document.html), quando não existem mais holds ou validation errors que impeçam o avanço, o status passa para:

~~~text
Completed Prevalidation
~~~

Esse é o ponto que normalmente procuro quando quero confirmar que a pré-validação do FDC terminou corretamente.

Depois disso ainda existem etapas posteriores, como Confirm Item Deliveries e uma nova validação até o status Captured, mas isso já é outra parte do fluxo.

## Fluxo para deixar na manga

~~~text
1. Preparar o ZIP com o XML da NF-e

2. Upload
   Tools
   > File Import and Export

   Account:
   scm/BrazilSEFAZSupplierMessages/import

3. Opcionalmente confirmar o arquivo no UCM
   https://<ambiente>/cs

4. Executar
   Import Brazil Electronic Documents

5. Executar
   Import and Validate Electronic Fiscal Documents

6. Se não entrou no FDC
   Fiscal Document Capture
   > Manage Interface Exceptions

7. Se já entrou no FDC
   Manage Inbound Fiscal Documents
   > Holds and Validation Errors

8. Corrigir a pendência

9. Se houver nova mensagem do parceiro / SEFAZ
   scm/BrazilSEFAZPartnerMessages/import

10. Executar novamente
    Import Brazil Electronic Documents

11. Executar novamente
    Import and Validate Electronic Fiscal Documents

12. Validar o documento

13. Resultado esperado desta etapa
    Completed Prevalidation
~~~

## Troubleshooting rápido

### O arquivo está no UCM, mas nada aconteceu

Verificar primeiro:

~~~text
Import Brazil Electronic Documents
~~~

Depois:

~~~text
Import and Validate Electronic Fiscal Documents
~~~

### O documento não aparece em Manage Inbound Fiscal Documents

Consultar:

~~~text
Fiscal Document Capture
> Manage Interface Exceptions
~~~

Provavelmente o XML ainda não conseguiu sair da interface.

### O documento aparece no FDC, mas não avança

Consultar:

~~~text
Manage Inbound Fiscal Documents
> Holds and Validation Errors
~~~

Corrigir a pendência e validar novamente.

### Quero reprocessar tudo em um teste

~~~text
Import and Validate Electronic Fiscal Documents
Fiscal Documents to Validate = All
~~~

### Quero apenas tentar importar novamente o que ficou na interface

~~~text
Import and Validate Electronic Fiscal Documents
Fiscal Documents to Validate = New
~~~

### Quero apenas validar documentos que já entraram no FDC

~~~text
Import and Validate Electronic Fiscal Documents
Fiscal Documents to Validate = Existing
~~~

## Resumo

~~~text
UCM
> Import Brazil Electronic Documents
> Import and Validate Electronic Fiscal Documents
> Manage Interface Exceptions, se ainda estiver na interface
> Manage Inbound Fiscal Documents, se já estiver no FDC
> Holds and Validation Errors
> Validate Fiscal Document
> Completed Prevalidation
~~~

A ideia deste artigo é deixar o processo operacional em uma sequência fácil de consultar. Os links ao longo do texto apontam para a documentação Oracle usada como referência quando for necessário conferir algum detalhe.

## Referências

- [Oracle — Import Fiscal Document](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/import-fiscal-document.html)
- [Oracle — Import Brazil Electronic Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faspc/import-brazil-electronic-documents.html)
- [Oracle — Import and Validate Electronic Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faspc/import-and-validate-electronic-fiscal-documents.html)
- [Oracle — Capture Fiscal Documents using XML Import](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fafdc/Untitled.html)
- [Oracle — Freight Fiscal Documents for Inbound Flow](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fafdc/freight-fiscal-documents-for-inbound-flow.html)
- [Oracle — Collaboration Messaging Framework](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faips/collaboration-messaging-framework.html)
- [Oracle — View Interface Exceptions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fafdc/view-interface-exceptions.html)
