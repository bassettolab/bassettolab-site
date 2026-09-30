---
title: "Oracle Cloud: cómo sortear el límite de nItemPed en transferencias internas"
date: 2026-09-30
description: "Una alternativa para identificar líneas de transferencias internas en FDC cuando nItemPed de la NF-e no admite el identificador completo."
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

# Oracle Cloud: cómo sortear el límite de nItemPed en transferencias internas

Quiero compartir un escenario técnico que puede aparecer en implementaciones de transferencias internas en Oracle Cloud.

En una transferencia entre unidades, Oracle puede generar la NF-e mediante FDG y enviarla a un socio fiscal, que realiza la comunicación con SEFAZ. Después de la autorización, el XML vuelve a Oracle y es procesado por FDC.

Flujo resumido:

```text
Transfer Order > Shipment > FDG > Socio Fiscal > SEFAZ > XML NF-e > Collaboration Messaging > FDC > Receipt
```

## El problema

Para que FDC pueda relacionar correctamente el documento recibido con la transferencia, necesitamos identificar el shipment y su línea correspondiente.

En el XML de la NF-e, una posibilidad es utilizar:

```xml
<xPed>Shipment Number</xPed>
<nItemPed>Shipment Line Identifier</nItemPed>
```

La limitación es que `nItemPed` admite únicamente 6 dígitos. Cuando el identificador de la línea en Oracle ya supera ese tamaño, no es posible transportar el valor completo en este campo.

Truncar el identificador tampoco es una buena opción porque diferentes líneas pueden terminar generando el mismo valor reducido.

## La alternativa

La alternativa fue utilizar `infAdProd` para transportar el identificador completo de la línea.

El diseño queda así:

```text
Shipment Number > xPed
Line Identifier > LEGAL_MESSAGE_TEXT > infAdProd
```

En FDG, el identificador puede estar disponible a nivel de línea mediante `LEGAL_MESSAGE_TEXT`.

Una regla posible para `TRANSFER ORDER SHIPMENT` es obtener el identificador desde `ZX_LINES_DET_FACTORS`:

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

El socio fiscal puede entonces mapear el valor a:

```xml
<infAdProd>...</infAdProd>
```

## Ajuste en Collaboration Messaging

Cuando el XML autorizado vuelve a Oracle, Collaboration Messaging transforma el mensaje antes de que FDC lo procese.

El camino en Oracle Cloud es:

```text
Tools > Collaboration Messaging > Manage Collaboration Message Definitions
```

La definición utilizada para la NF-e de entrada apunta a un XSL responsable del mapeo.

El comportamiento estándar puede ser similar a:

```xml
<n9:SourceDocumentLine>
    <xsl:value-of select="ns3:prod/ns3:nItemPed"/>
</n9:SourceDocumentLine>
```

Para determinadas operaciones, el XSL puede obtener el identificador desde `infAdProd`:

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

La idea es:

```text
XML NF-e > infAdProd > Collaboration Messaging XSL > SourceDocumentLine > FDC
```

Solo los CFOP necesarios utilizan `infAdProd`; los demás documentos mantienen el comportamiento estándar con `nItemPed`.

## Resultado

Con este enfoque, el identificador completo de la línea puede recorrer el proceso de emisión y retorno de la NF-e sin depender del límite de 6 dígitos de `nItemPed`.

Flujo técnico:

```text
Shipment > FDG > LEGAL_MESSAGE_TEXT > Socio Fiscal > infAdProd > SEFAZ > XML > Collaboration Messaging > SourceDocumentLine > FDC > Receipt
```

Es importante recordar que `infAdProd` es un campo fiscal de la NF-e. Por eso, este tipo de uso debe validarse con el equipo fiscal y con el socio responsable de la integración.

También es recomendable evitar cambios directos en definiciones seeded de Collaboration Messaging y mantener la personalización separada siempre que sea posible.

## Referencias públicas

- Oracle Fusion Cloud — Fiscal Document Capture  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — Collaboration Messaging Framework  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — ZX_LINES_DET_FACTORS  
  https://docs.oracle.com/en/cloud/saas/financials/

- Portal Nacional de NF-e de Brasil  
  https://www.nfe.fazenda.gov.br/
