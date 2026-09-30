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

A complexidade do sistema fiscal e tributário brasileiro não é novidade e traz desafios importantes para os ERPs, que precisam se adaptar constantemente às particularidades e exigências locais.

Dentro desse contexto, quero compartilhar um cenário técnico que pode surgir em implementações de transferências internas no Oracle Cloud.

Em uma transferência entre unidades, como entre matriz e filiais, pode ser obrigatória a emissão de uma NF-e para acompanhar o material durante o transporte.

O Fiscal Document Generation (FDG) gera o documento fiscal e permite a criação de um extract file com as informações necessárias para que um parceiro fiscal formate o XML do documento e faça a comunicação com a autoridade fiscal. [Oracle — Fiscal Document Extract](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/fiscal-document-extract-fd-generation.html)

Depois da autorização, o XML estruturado pode retornar para a organização de destino, ser transformado pelo Collaboration Messaging e capturado pelo Fiscal Document Capture (FDC). [Oracle — Internal Transfer of Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fafdc/internal-transfer-of-fiscal-documents.html)

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

A limitação está no leiaute da NF-e exigido pela SEFAZ: o `nItemPed` aceita no máximo 6 dígitos, enquanto o `xPed` aceita de 1 a 15 caracteres. [NF-e — MOC 7.0, Leiaute da NF-e/NFC-e](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=J+I+v4eN00E%3D)

Quando o identificador da linha no Oracle ultrapassa 6 dígitos, o parceiro fiscal não consegue enviar o valor completo em `nItemPed` e precisa truncá-lo ou ajustá-lo antes da transmissão para a SEFAZ.

Esse é justamente o ponto crítico: ao truncar o identificador, perde-se o valor original da linha e podem ocorrer colisões entre identificadores diferentes, dificultando a correlação correta do documento no FDC.

## Alternativa utilizada

A alternativa foi utilizar o `infAdProd` para transportar o identificador completo da linha. O campo suporta até 500 caracteres no leiaute da NF-e. [NF-e — MOC 7.0, infAdProd](https://hom.nfe.fazenda.gov.br/PORTAL/exibirArquivo.aspx?conteudo=DQFCIFUzszw%3D)

O desenho fica assim:

```text
Shipment Number > xPed
Line Identifier > infAdProd
```

Para transportar o identificador completo, passamos a utilizar a tag `infAdProd` no XML.

Para shipments do tipo `TRANSFER ORDER SHIPMENT`, usamos uma lógica no FDG em que o valor destinado ao `infAdProd` é obtido da tabela `ZX_LINES_DET_FACTORS`:

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

Com isso, a informação do ID da linha passa a viajar no XML por meio da tag `infAdProd`, preservando o identificador completo.

## Ajuste no Collaboration Messaging

Quando o XML autorizado retorna ao Oracle, o Collaboration Messaging transforma a mensagem antes do processamento pelo FDC.

O caminho no Oracle Cloud é:

```text
Tools > Collaboration Messaging > Manage Collaboration Message Definitions
```

A definição utilizada para a NF-e de entrada aponta para um XSL responsável pelo mapeamento. A documentação do Collaboration Messaging confirma que a definição de mensagem referencia o arquivo XSL usado na transformação. [Oracle — Collaboration Message Definitions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/facmm/create-a-collaboration-message-definition.html)

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
Shipment > FDG > Parceiro Fiscal > infAdProd > SEFAZ > XML > Collaboration Messaging > SourceDocumentLine > FDC > Receipt
```

É importante lembrar que `infAdProd` é um campo fiscal da NF-e. Portanto, esse tipo de uso deve ser validado com a área fiscal e com o parceiro responsável pela integração.

Também é recomendável evitar alterações diretas em definições seeded do Collaboration Messaging e manter a customização separada sempre que possível.

## Referências públicas

- [Oracle — Fiscal Document Extract](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/fiscal-document-extract-fd-generation.html)
- [Oracle — Internal Transfer of Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fafdc/internal-transfer-of-fiscal-documents.html)
- [Oracle — Collaboration Message Definitions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/facmm/create-a-collaboration-message-definition.html)
- [Portal Nacional da NF-e](https://www.nfe.fazenda.gov.br/)
