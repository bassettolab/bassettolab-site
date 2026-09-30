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

La complejidad del sistema fiscal y tributario brasileño no es ninguna novedad y plantea desafíos importantes para los ERP, que necesitan adaptarse continuamente a las particularidades y exigencias locales.

Dentro de este contexto, quiero compartir un escenario técnico que puede surgir en implementaciones de transferencias internas en Oracle Cloud.

En una transferencia entre unidades, como entre una casa matriz y sus filiales, puede ser obligatoria la emisión de una NF-e para acompañar el material durante el transporte.

Fiscal Document Generation (FDG) genera el documento fiscal y permite crear un extract file con la información necesaria para que un socio fiscal formatee el XML del documento y se comunique con la autoridad fiscal. [Oracle — Fiscal Document Extract](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/fiscal-document-extract-fd-generation.html)

Después de la autorización, el XML estructurado puede volver a la organización de destino, ser transformado por Collaboration Messaging y ser capturado por Fiscal Document Capture (FDC). [Oracle — Internal Transfer of Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fafdc/internal-transfer-of-fiscal-documents.html)

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

La limitación está en el layout de la NF-e exigido por SEFAZ: `nItemPed` admite un máximo de 6 dígitos, mientras que `xPed` admite entre 1 y 15 caracteres. [NF-e — MOC 7.0, Layout de NF-e/NFC-e](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=J+I+v4eN00E%3D)

Cuando el identificador de la línea en Oracle supera los 6 dígitos, el socio fiscal no puede enviar el valor completo en `nItemPed` y debe truncarlo o ajustarlo antes de la transmisión a SEFAZ.

Este es precisamente el punto crítico: al truncar el identificador se pierde el valor original de la línea y pueden producirse colisiones entre identificadores diferentes, dificultando la correlación correcta del documento en FDC.

## La alternativa

La alternativa fue utilizar `infAdProd` para transportar el identificador completo de la línea. El campo admite hasta 500 caracteres en el layout de la NF-e. [NF-e — MOC 7.0, infAdProd](https://hom.nfe.fazenda.gov.br/PORTAL/exibirArquivo.aspx?conteudo=DQFCIFUzszw%3D)

El diseño queda así:

```text
Shipment Number > xPed
Line Identifier > infAdProd
```

Para transportar el identificador completo, utilizamos la tag `infAdProd` en el XML.

Para shipments de tipo `TRANSFER ORDER SHIPMENT`, utilizamos una lógica en FDG en la que el valor destinado a `infAdProd` se obtiene de la tabla `ZX_LINES_DET_FACTORS`:

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

Con este enfoque, la información del ID de la línea viaja en el XML por medio de la tag `infAdProd`, preservando el identificador completo.

## Ajuste en Collaboration Messaging

Cuando el XML autorizado vuelve a Oracle, Collaboration Messaging transforma el mensaje antes de que FDC lo procese.

El camino en Oracle Cloud es:

```text
Tools > Collaboration Messaging > Manage Collaboration Message Definitions
```

La definición utilizada para la NF-e de entrada apunta a un XSL responsable del mapeo. La documentación de Collaboration Messaging confirma que la definición del mensaje referencia el archivo XSL utilizado para la transformación. [Oracle — Collaboration Message Definitions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/facmm/create-a-collaboration-message-definition.html)

El comportamiento estándar es:

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

La idea es simple:

```text
XML NF-e > infAdProd > Collaboration Messaging XSL > SourceDocumentLine > FDC
```

Así, solamente los CFOP tratados pasan a utilizar `infAdProd`. Para los demás documentos, se mantiene el comportamiento estándar con `nItemPed`.

## Resultado

Con este diseño, el identificador completo de la línea puede recorrer el proceso de emisión y retorno de la NF-e sin depender del límite de 6 dígitos de `nItemPed`.

El flujo técnico queda así:

```text
Shipment > FDG > Socio Fiscal > infAdProd > SEFAZ > XML > Collaboration Messaging > SourceDocumentLine > FDC > Receipt
```

Es importante recordar que `infAdProd` es un campo fiscal de la NF-e. Por lo tanto, este tipo de uso debe validarse con el equipo fiscal y con el socio responsable de la integración.

También es recomendable evitar cambios directos en definiciones seeded de Collaboration Messaging y mantener la personalización separada siempre que sea posible.

## Referencias públicas

- [Oracle — Fiscal Document Extract](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/fiscal-document-extract-fd-generation.html)
- [Oracle — Internal Transfer of Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fafdc/internal-transfer-of-fiscal-documents.html)
- [Oracle — Collaboration Message Definitions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/facmm/create-a-collaboration-message-definition.html)
- [Portal Nacional de NF-e de Brasil](https://www.nfe.fazenda.gov.br/)
