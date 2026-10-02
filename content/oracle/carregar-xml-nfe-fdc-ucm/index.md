---
title: "Oracle Cloud FDC: como carregar manualmente um XML de NF-e pelo UCM"
date: 2026-10-02
article_id: "006"
description: "Passo a passo para carregar manualmente um XML de NF-e no Oracle Cloud FDC usando o UCM, executar os processos de importação e validação e acompanhar erros, holds e o status Completed Prevalidation."
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

Então este artigo fica como referência rápida para quando eu precisar testar uma NF-e, reproduzir um problema de integração ou simplesmente validar o processamento de um XML no FDC.

O fluxo resumido é:

~~~text
XML NF-e
   ↓
UCM / Oracle Content Repository
   ↓
Import Brazil Electronic Documents
   ↓
Import and Validate Electronic Fiscal Documents
   ↓
FDC
   ↓
Validação / Holds
   ↓
Completed Prevalidation
~~~

## 1. Carregar o XML no UCM

O primeiro passo é disponibilizar o XML no Oracle Content Repository, também conhecido como UCM.

Uma forma de acessar diretamente o repositório é utilizar a URL do ambiente adicionando:

~~~text
https://<seu-ambiente>/cs
~~~

No UCM é possível pesquisar pelo nome do arquivo e confirmar se ele realmente foi carregado.

Também é possível fazer o upload pela própria aplicação Oracle Cloud:

~~~text
Navigator
> Tools
> File Import and Export
~~~

Para uma NF-e recebida do fornecedor, o arquivo deve ser carregado na conta:

~~~text
scm/BrazilSEFAZSupplierMessages/import
~~~

A Oracle documenta essa conta como o repositório utilizado para mensagens recebidas de fornecedores.

Para mensagens de retorno provenientes do provedor responsável pela comunicação com a SEFAZ, a conta utilizada é:

~~~text
scm/BrazilSEFAZPartnerMessages/import
~~~

Essas duas contas são consumidas pelo processo de importação dos documentos eletrônicos brasileiros.

## 2. Executar Import Brazil Electronic Documents

Depois que o XML estiver disponível no UCM, acessar:

~~~text
Navigator
> Tools
> Scheduled Processes
~~~

Executar o processo:

~~~text
Import Brazil Electronic Documents
~~~

Esse processo busca os arquivos existentes nas contas do Oracle Content Repository e inicia o processamento das mensagens.

Segundo a documentação Oracle, ele consulta principalmente:

~~~text
scm/BrazilSEFAZSupplierMessages/import
scm/BrazilSEFAZPartnerMessages/import
~~~

Se o arquivo estiver no UCM mas não aparecer no FDC, este é um dos primeiros processos que deve ser verificado.

## 3. Executar Import and Validate Electronic Fiscal Documents

Depois da importação da mensagem, executar:

~~~text
Import and Validate Electronic Fiscal Documents
~~~

Esse é o processo responsável por importar os documentos que estão na interface do FDC e também executar a validação dos documentos fiscais.

Um parâmetro importante é:

~~~text
Fiscal Documents to Validate
~~~

Os principais valores são:

| Valor | Comportamento |
| --- | --- |
| New | Processa documentos novos que ainda estão na interface |
| Existing | Valida documentos que já existem no FDC |
| All | Executa os dois comportamentos |

Para testes manuais, quando quero garantir que tanto a interface quanto o documento já criado sejam processados, normalmente uso:

~~~text
Fiscal Documents to Validate = All
~~~

## 4. Se o XML tiver erro

Se houver algum problema durante a importação, o documento pode permanecer na interface e não chegar corretamente ao FDC.

Nessa situação, verificar primeiro o resultado dos Scheduled Processes e depois a interface de erros do FDC.

O acesso funcional ao documento é feito por:

~~~text
Supply Chain Execution
> Fiscal Document Capture
> Manage Inbound Fiscal Documents
~~~

Quando o documento já foi criado, a região:

~~~text
Holds and Validation Errors
~~~

mostra os erros de validação e os holds existentes.

A própria Oracle recomenda corrigir os erros ou holds e executar novamente a validação do documento.

## 5. Documento importado, mas aguardando confirmação eletrônica

Quando a NF-e é importada corretamente, ainda podem existir validações relacionadas ao processo eletrônico e à confirmação da SEFAZ.

Em uma integração completa, normalmente existem pelo menos duas mensagens diferentes:

~~~text
1. XML da NF-e do fornecedor
2. Mensagem/XML de retorno relacionado à SEFAZ
~~~

O primeiro arquivo normalmente entra por:

~~~text
scm/BrazilSEFAZSupplierMessages/import
~~~

E mensagens provenientes do parceiro ou provedor de SEFAZ podem entrar por:

~~~text
scm/BrazilSEFAZPartnerMessages/import
~~~

Depois do retorno, os processos devem ser executados novamente:

~~~text
Import Brazil Electronic Documents

Import and Validate Electronic Fiscal Documents
~~~

O objetivo é permitir que o Oracle processe a confirmação recebida e atualize o documento fiscal.

## 6. Validar novamente o documento no FDC

Depois que os erros e holds aplicáveis forem resolvidos, o documento precisa passar novamente pela validação.

Isso pode ser feito diretamente no FDC:

~~~text
Actions
> Validate Fiscal Document
~~~

Ou em lote pelo processo:

~~~text
Import and Validate Electronic Fiscal Documents
~~~

A Oracle documenta que, quando não existem mais holds ou validation errors impeditivos, o documento passa para:

~~~text
Completed Prevalidation
~~~

Nesse ponto, a pré-validação do documento foi concluída.

## Fluxo completo para consulta rápida

~~~text
1. Receber o XML da NF-e

2. Fazer upload no UCM
   scm/BrazilSEFAZSupplierMessages/import

3. Confirmar o arquivo no UCM
   https://<ambiente>/cs

4. Executar
   Import Brazil Electronic Documents

5. Executar
   Import and Validate Electronic Fiscal Documents

6. Consultar
   Fiscal Document Capture
   > Manage Inbound Fiscal Documents

7. Se houver erro
   revisar Holds and Validation Errors

8. Se houver dependência da confirmação SEFAZ
   carregar/processar a mensagem de retorno
   scm/BrazilSEFAZPartnerMessages/import

9. Executar novamente
   Import Brazil Electronic Documents

10. Executar novamente
    Import and Validate Electronic Fiscal Documents

11. Validar o FDC

12. Resultado esperado
    Completed Prevalidation
~~~

## Troubleshooting rápido

### Arquivo está no UCM, mas não aparece no FDC

Verificar:

~~~text
Import Brazil Electronic Documents
~~~

Depois verificar:

~~~text
Import and Validate Electronic Fiscal Documents
~~~

### Documento ficou preso na interface

Executar:

~~~text
Import and Validate Electronic Fiscal Documents
Fiscal Documents to Validate = New ou All
~~~

e revisar os erros retornados pelo processo.

### Documento existe no FDC, mas não avança

Consultar:

~~~text
Manage Inbound Fiscal Documents
> Holds and Validation Errors
~~~

Corrigir o erro ou aguardar/processar a mensagem eletrônica pendente e validar novamente.

### Documento está correto e sem erros

Depois da validação, o status esperado antes da confirmação do recebimento é:

~~~text
Completed Prevalidation
~~~

## Observação importante

O fluxo exato pode variar conforme a arquitetura de integração utilizada pela empresa, principalmente na comunicação entre fornecedor, parceiro fiscal, Collaboration Messaging e SEFAZ.

O ponto principal para lembrar é a sequência:

~~~text
UCM
> Import Brazil Electronic Documents
> Import and Validate Electronic Fiscal Documents
> FDC
> Holds / Errors
> Validate Fiscal Document
> Completed Prevalidation
~~~

## Referências públicas

- [Oracle — Import Brazil Electronic Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faspc/import-brazil-electronic-documents.html)
- [Oracle — Import and Validate Electronic Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faspc/import-and-validate-electronic-fiscal-documents.html)
- [Oracle — Import Fiscal Document](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/import-fiscal-document.html)
- [Oracle — Task Flow for Purchase of Goods](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26a/fafdc/task-flow-for-purchase-of-goods.html)
