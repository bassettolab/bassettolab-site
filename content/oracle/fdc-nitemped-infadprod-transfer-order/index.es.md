---
title: "Oracle Cloud: cómo sortear el límite de nItemPed en transferencias internas"
date: 2026-09-30
description: "Una alternativa práctica para identificar líneas de transferencias internas en FDC cuando nItemPed de la NF-e no admite el identificador completo."
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

Quiero compartir un escenario técnico que puede aparecer en implementaciones de transferencias internas con Oracle Cloud y una alternativa para tratarlo.

El escenario es bastante común. Una mercancía se mueve de una unidad a otra y, dependiendo de la operación, puede ser necesaria la emisión de una NF-e.

En una arquitectura con un socio fiscal, Oracle puede generar el documento fiscal mediante FDG, enviar los datos al socio fiscal, el socio los transmite a SEFAZ y, después de la autorización, queda disponible el XML de la NF-e.

Cuando la mercancía llega al destino, el XML vuelve a Oracle, Collaboration Messaging transforma el mensaje y FDC procesa el documento fiscal.

![Internal transfer flow with NF-e](flow-general.svg)

## Dónde aparece la limitación

Para que FDC pueda identificar correctamente la transferencia, es necesario relacionar la NF-e con el shipment y con la línea correspondiente.

Un diseño posible es:

```xml
<xPed>Shipment Number</xPed>
<nItemPed>Shipment Line Identifier</nItemPed>
```

La dificultad aparece cuando el identificador técnico de la línea es mayor que el tamaño admitido por `nItemPed`.

En el layout de la NF-e, `nItemPed` admite hasta 6 dígitos. En implementaciones donde el identificador técnico ya supera ese tamaño, el valor completo deja de caber.

Truncar el identificador no es una buena opción porque distintos identificadores pueden terminar produciendo el mismo valor reducido.

![nItemPed limitation and infAdProd alternative](nitemped-infadprod.svg)

## Una alternativa: infAdProd

Una opción es utilizar:

```xml
<infAdProd>
```

Este campo permite transportar una información más larga y puede llevar el identificador completo de la línea.

La idea queda así:

```text
xPed      → Shipment Number
nItemPed  → permanece dentro de la limitación del layout
infAdProd → identificador completo de la línea
```

Esto es una decisión de implementación. No significa que SEFAZ u Oracle definan `infAdProd` específicamente para transportar un identificador técnico de Oracle. Su uso debe validarse con el equipo fiscal y con el socio fiscal.

## Paso 1: llevar el identificador hasta el XML

FDG dispone del concepto de `LEGAL_MESSAGE_TEXT` a nivel de línea.

Dependiendo de la versión o del diseño de la automatización, puede ser necesario complementar el Data Model para rellenar este atributo automáticamente durante la generación del documento fiscal.

Una regla genérica para `TRANSFER ORDER SHIPMENT` puede obtener el identificador desde `ZX_LINES_DET_FACTORS`:

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

De esta forma, para este tipo de transferencia, el identificador completo puede quedar disponible para el socio fiscal.

El socio fiscal puede mapear el valor a:

```xml
<infAdProd>...</infAdProd>
```

## Paso 2: hacer que FDC lea infAdProd

Después de la autorización de la NF-e y del retorno del XML a Oracle, hay que ajustar el mapeo de entrada para que, en las operaciones necesarias, el identificador de la línea se lea desde `infAdProd` en lugar de `nItemPed`.

En Oracle Cloud:

```text
Tools
  → Collaboration Messaging
    → Manage Collaboration Message Definitions
```

La definición utilizada para procesar la NF-e de entrada apunta a un XSL responsable de transformar el mensaje.

El comportamiento estándar puede ser similar a:

```xml
<n9:SourceDocumentLine>
    <xsl:value-of select="ns3:prod/ns3:nItemPed"/>
</n9:SourceDocumentLine>
```

Para determinadas operaciones, el XSL puede redirigir la lectura hacia `infAdProd`.

Ejemplo genérico:

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

Los CFOP anteriores son solo un ejemplo técnico de cómo estructurar la condición. Cada implementación debe validar qué códigos pertenecen realmente a su escenario fiscal.

![Technical solution flow](flow-technical.svg)

## Algunos cuidados

Evite modificar directamente una definición seeded de Collaboration Messaging. Es más seguro trabajar con una definición personalizada y mantener el XSL estándar como referencia.

También conviene limitar la regla únicamente a las operaciones necesarias y mantener un `otherwise` utilizando `nItemPed`. Esto reduce el riesgo de afectar otros flujos de entrada de NF-e.

Antes de pasar el cambio a producción, valide un XML autorizado y confirme que `infAdProd` contiene exactamente el identificador esperado.

Por último, `infAdProd` es un campo fiscal de la NF-e. En este escenario se utiliza como parte de una solución técnica para sortear la limitación de tamaño de `nItemPed`, por lo que la validación fiscal sigue siendo necesaria.

## Referencias públicas

- Oracle Fusion Cloud — Fiscal Document Capture  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/
- Oracle Fusion Cloud — Collaboration Messaging Framework  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/
- Oracle Fusion Cloud — ZX_LINES_DET_FACTORS  
  https://docs.oracle.com/en/cloud/saas/financials/
- Portal Nacional de NF-e de Brasil  
  https://www.nfe.fazenda.gov.br/
