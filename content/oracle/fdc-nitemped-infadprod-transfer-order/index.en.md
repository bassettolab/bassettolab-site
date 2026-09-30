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

# Oracle Cloud: Working Around the nItemPed Limit in Internal Transfers

I want to share a technical scenario that can appear in Oracle Cloud internal-transfer implementations.

In a transfer between units, Oracle can generate the NF-e through FDG and send it to a fiscal partner, which handles the communication with SEFAZ. After authorization, the XML returns to Oracle and is processed by FDC.

Summary flow:

```text
Transfer Order > Shipment > FDG > Fiscal Partner > SEFAZ > NF-e XML > Collaboration Messaging > FDC > Receipt
```

## The issue

For FDC to relate the received document to the correct transfer, we need to identify the shipment and its corresponding line.

In the NF-e XML, one possible approach is:

```xml
<xPed>Shipment Number</xPed>
<nItemPed>Shipment Line Identifier</nItemPed>
```

The limitation is that `nItemPed` accepts only 6 digits. When the Oracle line identifier is already larger than that, the complete value cannot be carried in this field.

Truncating the identifier is also not a good option because different lines may eventually produce the same shortened value.

## The alternative

The alternative was to use `infAdProd` to carry the complete line identifier.

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

The fiscal partner can then map that value to:

```xml
<infAdProd>...</infAdProd>
```

## Collaboration Messaging adjustment

When the authorized XML returns to Oracle, Collaboration Messaging transforms the message before FDC processing.

The Oracle Cloud path is:

```text
Tools > Collaboration Messaging > Manage Collaboration Message Definitions
```

The inbound NF-e message definition points to an XSL responsible for the mapping.

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

The idea is:

```text
NF-e XML > infAdProd > Collaboration Messaging XSL > SourceDocumentLine > FDC
```

Only the required CFOPs use `infAdProd`; all other documents keep the standard `nItemPed` behavior.

## Result

With this approach, the complete line identifier can travel through the NF-e outbound and inbound process without depending on the 6-digit limitation of `nItemPed`.

Technical flow:

```text
Shipment > FDG > LEGAL_MESSAGE_TEXT > Fiscal Partner > infAdProd > SEFAZ > XML > Collaboration Messaging > SourceDocumentLine > FDC > Receipt
```

It is important to remember that `infAdProd` is a fiscal field in the NF-e. This type of use should therefore be validated with the fiscal team and the fiscal integration partner.

It is also preferable to avoid changing seeded Collaboration Messaging definitions directly and to keep the customization separate whenever possible.

## Public references

- Oracle Fusion Cloud — Fiscal Document Capture  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — Collaboration Messaging Framework  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — ZX_LINES_DET_FACTORS  
  https://docs.oracle.com/en/cloud/saas/financials/

- Brazil NF-e Portal  
  https://www.nfe.fazenda.gov.br/
