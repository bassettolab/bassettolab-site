---
title: "Oracle Cloud: contornando o limite do nItemPed em transferências internas"
date: 2026-09-30
description: "Uma alternativa para relacionar linhas de transferências internas no FDC quando o nItemPed da NF-e não comporta o identificador completo."
tags:
  - Oracle Cloud
  - Brazil Localization
  - FDG
  - FDC
  - NF-e
  - Collaboration Messaging
categories:
  - Oracle
toc: true
type: post
featured: true
draft: false
---

# Oracle Cloud: contornando o limite do nItemPed em transferências internas

Quero compartilhar um cenário técnico que pode aparecer em implementações de transferência interna no Oracle Cloud.

Em uma transferência entre unidades, o Oracle pode gerar a NF-e pelo FDG e enviá-la para um parceiro fiscal, que faz a comunicação com a SEFAZ. Depois da autorização, o XML retorna ao Oracle e é processado pelo FDC.

## O problema

Para o FDC relacionar corretamente o documento recebido à transferência, normalmente precisamos identificar o shipment e a respectiva linha.

No XML da NF-e, uma possibilidade é utilizar o `xPed` para o Shipment Number e o `nItemPed` para o identificador da linha.

A limitação aparece no `nItemPed`, que aceita apenas 6 dígitos. Quando o identificador da linha no Oracle já ultrapassa esse tamanho, não é possível transportar o valor completo nesse campo.

Truncar o identificador também não é uma boa solução, porque pode gerar colisões entre linhas diferentes.

## Alternativa utilizada

A alternativa foi utilizar o `infAdProd` para transportar o identificador completo da linha.

No FDG, o identificador pode ser disponibilizado em nível de linha por meio do `LEGAL_MESSAGE_TEXT` e, a partir daí, o parceiro fiscal pode mapeá-lo para `infAdProd` no XML da NF-e.

No retorno do XML, o Collaboration Messaging é ajustado para que, nas operações aplicáveis, o `SourceDocumentLine` seja obtido de `infAdProd` em vez de `nItemPed`.

Esse ajuste é feito na definição de mensagem utilizada para a NF-e de entrada:

```text
Tools
  → Collaboration Messaging
    → Manage Collaboration Message Definitions
```

A regra pode ser limitada aos CFOPs necessários, mantendo o comportamento padrão com `nItemPed` para os demais documentos.

## Resultado

Com esse desenho, o identificador completo da linha consegue percorrer o processo de emissão e retorno da NF-e sem depender do limite de 6 dígitos do `nItemPed`.

É importante lembrar que `infAdProd` é um campo fiscal da NF-e. Portanto, esse tipo de uso deve ser validado com a área fiscal e com o parceiro responsável pela integração.

Também é recomendável evitar alterações diretas em definições seeded do Collaboration Messaging e manter a customização separada sempre que possível.

## Referências públicas

- Oracle Fusion Cloud — Fiscal Document Capture  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — Collaboration Messaging Framework  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — ZX_LINES_DET_FACTORS  
  https://docs.oracle.com/en/cloud/saas/financials/

- Portal Nacional da NF-e  
  https://www.nfe.fazenda.gov.br/
