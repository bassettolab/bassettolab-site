---
title: "Oracle Cloud: automatizando a preparação fiscal de shipments para emissão de NF-e"
description: "Como OIC, BI Publisher e APIs REST podem reduzir o trabalho manual de preparação fiscal de shipments no Oracle Cloud."
date: 2026-10-12
article_id: "004"
tags: ["Oracle Cloud", "Brazil Localization", "FDG", "OIC", "BI Publisher", "REST API", "NF-e", "SCM"]
categories: ["Oracle"]
toc: true
type: post
featured: true
draft: false
---

A complexidade fiscal brasileira traz desafios importantes para quem trabalha com Oracle Cloud, especialmente quando precisamos emitir uma grande quantidade de notas fiscais.

Em operações com alto volume de *Sales Orders* e *Transfer Orders*, a preparação dos documentos pode se tornar repetitiva. Antes de seguir para o *Fiscal Document Generation* (FDG), alguns atributos fiscais e logísticos precisam estar corretamente preenchidos.

Quando existem centenas de shipments, atualizar essas informações manualmente passa a consumir muito tempo. Foi pensando nesse cenário que surgiu a proposta de automatizar essa etapa.

## O problema

A criação de um shipment no Oracle Cloud não significa, necessariamente, que todos os dados exigidos pelo processo fiscal brasileiro estejam preenchidos.

Conforme o tipo de operação e a configuração fiscal, podem ser necessários dados como:

- Natureza da operação e informações fiscais complementares.
- Indicadores associados ao consumidor final e à presença do destinatário.
- Identificação do tipo de transferência.
- Atributos logísticos, como o código FOB.
- Atributos específicos mantidos no *Descriptive Flexfield* (DFF) do cabeçalho do shipment.

Preencher esses campos repetidamente, principalmente em operações de transferência entre estabelecimentos, aumenta o esforço operacional e a possibilidade de inconsistências.

## A proposta de automação

A alternativa é combinar *Oracle Integration Cloud* (OIC), *BI Publisher* e APIs REST do Oracle Fusion SCM para preparar automaticamente os shipments elegíveis.

O fluxo pode ser resumido assim:

```text
Sales Order / Transfer Order
            |
         Shipment
            |
    BI Publisher (consulta)
            |
        OIC (regras)
            |
 REST API: ShipmentUpdate
            |
     Atualização do DFF
            |
  Elegível para automação FDG
```

O BI Publisher consulta os shipments que atendem às regras definidas, levando em conta o tipo de origem, a organização de inventário e o estado dos atributos fiscais. O OIC recebe os resultados e chama a API REST `shipmentTransactionRequests`, utilizando a ação `ShipmentUpdate`, para atualizar os atributos necessários.

No desenho analisado, a integração foi concebida para executar a cada dez minutos e processar os shipments individualmente. Essa frequência é uma decisão de implementação, não uma exigência do Oracle.

## Tratamento de erros

Uma automação em volume precisa permitir que o erro de um único shipment não paralise todos os demais.

Por isso, a proposta prevê tratamento de falhas por registro, acompanhamento das execuções no OIC e possibilidade de reprocessamento após a correção da causa do erro.

Também é importante verificar critérios de elegibilidade antes de atualizar os registros, evitando alterações desnecessárias.

## O que a automação não faz

Essa integração prepara atributos do shipment. Ela não substitui a configuração tributária, não executa por si só todas as etapas de geração do documento fiscal e não autoriza uma NF-e na SEFAZ.

A etapa de automação do FDG continua responsável por identificar os registros preparados e dar continuidade ao fluxo fiscal, conforme a arquitetura adotada.

## Conclusão

O objetivo é simples: deixar que a integração faça o trabalho repetitivo, enquanto os usuários se concentram nas exceções e validações que realmente exigem análise.

Em cenários de emissão de NF-e em volume, preparar automaticamente os shipments pode reduzir o esforço manual e melhorar a consistência dos dados que alimentam o processo fiscal.

## Referências

- [Oracle Fusion SCM REST API — Shipment Transaction Requests](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fasrp/op-shipmenttransactionrequests-post.html)
- [Oracle — Fiscal Document Generation](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-configuring-fiscal-document-for-brazil.html)
