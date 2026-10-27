---
title: "Oracle Cloud FDC: Transfer Order sem source number e line por divergência de CEP"
date: 2026-10-27
article_id: "008"
description: "Como investigar linhas de NF-e paradas em Interface Exceptions no FDC quando a localização de destino tem CEP divergente e a Transfer Order não é derivada."
tags:
  - Oracle Cloud
  - Brazil Localization
  - FDC
  - Transfer Order
  - NF-e
  - Interface Exceptions
categories:
  - Oracle
toc: true
type: post
featured: true
draft: false
---

No Fiscal Document Capture (FDC), uma NF-e de transferência interna pode ficar em **Manage Interface Exceptions** sem derivar o número do documento de origem (*source document number*) e a linha (*source document line*).

Neste cenário, a causa identificada foi a divergência entre o endereço do destinatário informado na NF-e e o endereço da localização de destino cadastrada no Oracle. O CEP era diferente e os demais dados do endereço também precisavam ser conferidos.

## O que conferir primeiro

Compare o endereço usado na nota com o cadastro do estabelecimento que recebe a mercadoria:

- CNPJ do destinatário e da filial correspondente.
- CEP, logradouro, número, complemento, bairro, município e UF.
- Endereço de entrega informado no XML da NF-e, quando houver.
- Organização de inventário e localização de destino relacionadas à Transfer Order.

Não use automaticamente o endereço principal do CNPJ como endereço de entrega. Confirme se a filial e o endereço do comprovante correspondem ao local de destino informado na NF-e e usado pelo Oracle.

## Como a divergência afeta a análise

No fluxo de transferência, o FDC precisa relacionar as linhas do documento fiscal ao documento de origem para continuar o processamento. A documentação da Oracle explica que uma Transfer Order pode ser o documento de origem e que seus dados são usados para identificar os itens e as informações das linhas. A API de Transfer Orders também expõe atributos da localização e do CEP de destino.

A documentação pública não afirma que o CEP, isoladamente, seja a chave padrão usada para derivar o número e a linha da Transfer Order. Portanto, a divergência de endereço deve ser tratada como a causa observada neste cenário; se a derivação continuar falhando após a correção, também é necessário conferir a mensagem de erro e o mapeamento de origem no Collaboration Messaging.

## Corrigir a localização no Oracle

Acesse:

~~~text
Setup and Maintenance
> Manufacturing and Supply Chain Materials Management
> Setup
> Enterprise Profile
> Show: All Tasks
> Manage Locations
~~~

Pesquise a localização associada à organização de destino da Transfer Order. Confirme o código, a vigência e se ela representa o endereço de recebimento correto. Atualize o endereço e o CEP com base no endereço validado da filial/local de entrega.

Uma localização representa um endereço físico e pode ser associada a organizações de inventário. A tarefa **Manage Locations** mantém campos como endereço, cidade, estado e CEP. Veja [Create Locations — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fammi/create-locations.html) e [Update existing setup data — Oracle Applications](https://docs.oracle.com/en/cloud/saas/applications-common/26b/oafsm/update-existing-setup-data.html).

## Revisar e reprocessar no FDC

1. Abra o work area **Fiscal Document Capture**.
2. No painel de tarefas, selecione **Manage Interface Exceptions**.
3. Abra o documento e consulte o detalhe da exceção. Confirme se a localização/endereço é a causa registrada.
4. Depois da correção do cadastro, execute o processo **Import and Validate Electronic Fiscal Documents** em **Scheduled Processes**. Para tratar documentos ainda na interface, use o parâmetro **Fiscal Documents to Validate = New**; use **All** quando também precisar validar documentos que já foram criados no FDC.
5. Volte ao FDC e confirme se o documento de origem e a linha foram derivados. Depois acompanhe a validação e a criação do recebimento.

A Oracle descreve **Manage Interface Exceptions** como a página para revisar discrepâncias e erros de validação/importação, que podem ser resolvidos automaticamente ou por intervenção manual. Veja [Interface Exceptions — Oracle FDC](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/fafdc/interface-exceptions.html). O processo de importação e validação está em [Import and Validate Electronic Fiscal Documents — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faspc/import-and-validate-electronic-fiscal-documents.html). A criação do recebimento depende da conclusão da validação fiscal, conforme [Inbound Shipments for Brazil — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/famli/inbound-shipments-for-brazil.html).

## Se a derivação continuar falhando

Após confirmar o endereço e reprocessar, valide também:

- Se o XML recebido contém o CNPJ e o endereço corretos do destinatário/local de entrega.
- Se a Transfer Order e a linha estão ativas e correspondem ao material e à quantidade da NF-e.
- Se o número e a linha estão sendo enviados nos campos esperados pelo FDC, conforme o XSL/definição de mensagem do Collaboration Messaging.
- Se o XML usa `xPed` e `nItemPed` de forma compatível com o mapeamento configurado. Para um caso de limite de tamanho do `nItemPed`, veja [Oracle Cloud: contornando o limite do nItemPed em transferências internas](/oracle/fdc-nitemped-infadprod-transfer-order/).

A [visão geral do Fiscal Document Capture](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fafdc/overview-of-fiscal-document-capture.html) descreve a Transfer Order como um possível documento de origem. Para consultar os atributos da Transfer Order, incluindo localização e CEP de destino, veja a [REST API de Transfer Orders — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fasrp/op-transferorders-get.html).

## Referências

- [Oracle — Interface Exceptions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/fafdc/interface-exceptions.html)
- [Oracle — Overview of Fiscal Document Capture](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fafdc/overview-of-fiscal-document-capture.html)
- [Oracle — Create Locations](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fammi/create-locations.html)
- [Oracle — Import and Validate Electronic Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faspc/import-and-validate-electronic-fiscal-documents.html)
- [Oracle — Inbound Shipments for Brazil](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/famli/inbound-shipments-for-brazil.html)
