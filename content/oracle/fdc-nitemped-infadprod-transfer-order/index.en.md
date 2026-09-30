---
title: "Oracle Cloud: Working Around the nItemPed Limit in Internal Transfers"
date: 2026-09-30
description: "An alternative for identifying internal transfer lines in FDC when the NF-e nItemPed field cannot hold the complete line identifier."
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

The complexity of the Brazilian fiscal and tax system is nothing new and creates important challenges for ERPs, which need to continuously adapt to local requirements and particularities.

Within this context, I want to share a technical scenario that can arise in Oracle Cloud internal-transfer implementations.

In a transfer between units, such as between a head office and its branches, issuing an NF-e to accompany the material during transportation may be mandatory.

Fiscal Document Generation (FDG) generates the fiscal document and allows the creation of an extract file containing the information required for a fiscal partner to format the fiscal document XML and communicate with the tax authority. [Oracle — Fiscal Document Extract](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/fiscal-document-extract-fd-generation.html)

After authorization, the structured XML can return to the destination organization, be transformed by Collaboration Messaging, and be captured by Fiscal Document Capture (FDC). [Oracle — Internal Transfer of Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fafdc/internal-transfer-of-fiscal-documents.html)

Summary flow:

```text
Transfer Order > Shipment > FDG > Fiscal Partner > SEFAZ > NF-e XML > Collaboration Messaging > FDC > Receipt
```

## The issue

For FDC to correctly relate the received document to the transfer, we need to identify the shipment and its corresponding line.

In the NF-e XML, one possible approach is:

```xml
<xPed>Shipment Number</xPed>
<nItemPed>Shipment Line Identifier</nItemPed>
```

The limitation appears in `nItemPed`, which accepts only 6 digits. `xPed`, on the other hand, accepts from 1 to 15 characters. [NF-e — MOC 7.0, NF-e/NFC-e Layout](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=J+I+v4eN00E%3D)

When the Oracle line identifier already exceeds that size, the complete value cannot be carried in `nItemPed`.

Truncating the identifier is also not a good solution because it can create collisions between different lines.

## The alternative

The alternative was to use `infAdProd` to carry the complete line identifier. The field supports up to 500 characters in the NF-e layout. [NF-e — MOC 7.0, infAdProd](https://hom.nfe.fazenda.gov.br/PORTAL/exibirArquivo.aspx?conteudo=DQFCIFUzszw%3D)

The design becomes:

```text
Shipment Number > xPed
Line Identifier > LEGAL_MESSAGE_TEXT > infAdProd
```

In FDG, the identifier can be exposed at line level through `LEGAL_MESSAGE_TEXT`.

One possible rule for `TRANSFER ORDER SHIPMENT` is to retrieve the identifier from `ZX_LINES_DET_FACTORS`:

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

The fiscal partner can then map the value to:

```xml
<infAdProd>...</infAdProd>
```

## Collaboration Messaging adjustment

When the authorized XML returns to Oracle, Collaboration Messaging transforms the message before FDC processing.

The Oracle Cloud path is:

```text
Tools > Collaboration Messaging > Manage Collaboration Message Definitions
```

The definition used for the inbound NF-e points to an XSL responsible for the mapping. Collaboration Messaging documentation confirms that the message definition references the XSL file used for the transformation. [Oracle — Collaboration Message Definitions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/facmm/create-a-collaboration-message-definition.html)

The standard behavior can be similar to:

```xml
<n9:SourceDocumentLine>
    <xsl:value-of select="ns3:prod/ns3:nItemPed"/>
</n9:SourceDocumentLine>
```

For selected operations, the XSL can retrieve the identifier from `infAdProd` instead:

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

The idea is simple:

```text
NF-e XML > infAdProd > Collaboration Messaging XSL > SourceDocumentLine > FDC
```

Only the selected CFOPs use `infAdProd`. For all other documents, the standard `nItemPed` behavior remains unchanged.

## Result

With this design, the complete line identifier can travel through the NF-e outbound and inbound process without depending on the 6-digit limitation of `nItemPed`.

The technical flow is:

```text
Shipment > FDG > LEGAL_MESSAGE_TEXT > Fiscal Partner > infAdProd > SEFAZ > XML > Collaboration Messaging > SourceDocumentLine > FDC > Receipt
```

It is important to remember that `infAdProd` is a fiscal field in the NF-e. Therefore, this type of use should be validated with the fiscal team and with the partner responsible for the integration.

It is also recommended to avoid direct changes to seeded Collaboration Messaging definitions and to keep the customization separate whenever possible.

## Public references

- [Oracle — Fiscal Document Extract](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/fiscal-document-extract-fd-generation.html)
- [Oracle — Internal Transfer of Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fafdc/internal-transfer-of-fiscal-documents.html)
- [Oracle — Collaboration Message Definitions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/facmm/create-a-collaboration-message-definition.html)
- [Brazil NF-e Portal](https://www.nfe.fazenda.gov.br/)
