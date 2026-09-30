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

A complexidade do sistema fiscal e tributário brasileiro não é novidade e traz desafios importantes para os ERPs, que precisam se adaptar constantemente às particularidades e exigências locais.

Dentro desse contexto, quero compartilhar um cenário técnico que pode surgir em implementações de transferências internas no Oracle Cloud.

Em uma transferência entre unidades, o Oracle pode gerar a NF-e por meio do FDG e enviar as informações para um parceiro fiscal, responsável pela comunicação com a SEFAZ. Após a autorização, o XML da NF-e retorna ao Oracle e é processado pelo FDC.

Fluxo resumido:

```text
Transfer Order > Shipment > FDG > Parceiro Fiscal > SEFAZ > XML NF-e > Collaboration Messaging > FDC > Receipt
```

## O problema

Para o FDC relacionar corretamente o documento recebido à transferência, precisamos identificar o shipment e a respectiva linha.

No XML da NF-e, uma possibilidade é utilizar:

```xml
<xPed>Shipment Number</xPed>
<nItemPed>Shipment Line Identifier</nItemPed>
```

A limitação aparece no `nItemPed`, que aceita apenas 6 dígitos. Quando o identificador da linha no Oracle já ultrapassa esse tamanho, não é possível transportar o valor completo nesse campo.

Truncar o identificador também não é uma boa solução, porque pode gerar colisões entre linhas diferentes.

## Alternativa utilizada

A alternativa foi utilizar o `infAdProd` para transportar o identificador completo da linha.

O desenho fica assim:

```text
Shipment Number > xPed
Line Identifier > LEGAL_MESSAGE_TEXT > infAdProd
```

No FDG, o identificador pode ser disponibilizado em nível de linha por meio do `LEGAL_MESSAGE_TEXT`.

Uma lógica possível para `TRANSFER ORDER SHIPMENT` é buscar o identificador em `ZX_LINES_DET_FACTORS`:

```sql
CASE
    WHEN H.EVENT_CLASS_CODE = 'TRANSFER ORDER SHIPMENT'
    THEN TO_CHAR(
           (
             SELECT NVL(LINK_TO_TRX_LINE_ID, TRX_LINE_ID)
               FROM ZX_LINES_DET_FACTORS
              WHERE TRX_ID           = L.TRX_ID
                AND TRX_LINE_ID      = L.TRX_LINE_ID
                AND APPLICATION_ID   = L.APPLICATION_ID
                AND ENTITY_CODE      = L.ENTITY_CODE
                AND EVENT_CLASS_CODE = L.EVENT_CLASS_CODE
           )
         )
    ELSE L1E_1.LEGAL_MESSAGE_TEXT
END AS LEGAL_MESSAGE_TEXT
```

Com isso, o parceiro fiscal pode mapear o valor para:

```xml
<infAdProd>...</infAdProd>
```

## Ajuste no Collaboration Messaging

Quando o XML autorizado retorna ao Oracle, o Collaboration Messaging transforma a mensagem antes do processamento pelo FDC.

O caminho no Oracle Cloud é:

```text
Tools > Collaboration Messaging > Manage Collaboration Message Definitions
```

A definição utilizada para a NF-e de entrada aponta para um XSL responsável pelo mapeamento.

O comportamento padrão pode ser semelhante a:

```xml
<n9:SourceDocumentLine>
    <xsl:value-of select="ns3:prod/ns3:nItemPed"/>
</n9:SourceDocumentLine>
```

Para operações específicas, o XSL pode passar a buscar o identificador em `infAdProd`:

```xml
<n9:SourceDocumentLine>
    <xsl:choose>
        <xsl:when test="
            (ns3:prod/ns3:CFOP = 6151 or
             ns3:prod/ns3:CFOP = 5151 or
             ns3:prod/ns3:CFOP = 6557 or
             ns3:prod/ns3:CFOP = 5557)
             and normalize-space(ns3:infAdProd) != ''">

            <xsl:value-of select="ns3:infAdProd"/>

        </xsl:when>

        <xsl:otherwise>
            <xsl:value-of select="ns3:prod/ns3:nItemPed"/>
        </xsl:otherwise>
    </xsl:choose>
</n9:SourceDocumentLine>
```

A ideia é simples:

```text
XML NF-e > infAdProd > Collaboration Messaging XSL > SourceDocumentLine > FDC
```

Assim, somente os CFOPs tratados passam a usar `infAdProd`. Para os demais documentos, o comportamento padrão com `nItemPed` continua sendo utilizado.

## Resultado

Com esse desenho, o identificador completo da linha consegue percorrer o processo de emissão e retorno da NF-e sem depender do limite de 6 dígitos do `nItemPed`.

O fluxo técnico fica:

```text
Shipment > FDG > LEGAL_MESSAGE_TEXT > Parceiro Fiscal > infAdProd > SEFAZ > XML > Collaboration Messaging > SourceDocumentLine > FDC > Receipt
```

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
