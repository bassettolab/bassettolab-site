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

## El problema

Para que FDC pueda relacionar correctamente el documento recibido con la transferencia, normalmente necesitamos identificar el shipment y su línea correspondiente.

En el XML de la NF-e, una posibilidad es utilizar `xPed` para el Shipment Number y `nItemPed` para el identificador de la línea.

La limitación es que `nItemPed` admite únicamente 6 dígitos. Cuando el identificador de la línea en Oracle ya supera ese tamaño, no es posible transportar el valor completo en este campo.

Truncar el identificador tampoco es una buena opción, porque diferentes líneas pueden terminar generando el mismo valor reducido.

## La alternativa

La alternativa fue utilizar `infAdProd` para transportar el identificador completo de la línea.

En FDG, el identificador puede estar disponible a nivel de línea mediante `LEGAL_MESSAGE_TEXT`. A partir de ahí, el socio fiscal puede mapearlo a `infAdProd` en el XML de la NF-e.

Cuando el XML vuelve a Oracle, Collaboration Messaging se ajusta para que, en las operaciones aplicables, `SourceDocumentLine` se obtenga de `infAdProd` en lugar de `nItemPed`.

La definición de mensaje utilizada para la NF-e de entrada se encuentra en:

```text
Tools
  → Collaboration Messaging
    → Manage Collaboration Message Definitions
```

La regla puede limitarse a los CFOP necesarios, manteniendo el comportamiento estándar con `nItemPed` para los demás documentos.

## Resultado

Con este enfoque, el identificador completo de la línea puede recorrer el proceso de emisión y retorno de la NF-e sin depender del límite de 6 dígitos de `nItemPed`.

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
