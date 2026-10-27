---
title: "Oracle Cloud FDC: la Transfer Order no deriva el source number ni la line por una diferencia en el código postal"
date: 2026-10-27
article_id: "008"
description: "Cómo investigar líneas de NF-e detenidas en Interface Exceptions de FDC cuando la ubicación de destino tiene un código postal diferente y no se deriva la Transfer Order."
tags:
  - Oracle Cloud
  - Brazil Localization
  - FDC
  - Transfer Order
  - NF-e
  - Interface Exceptions
categories:
  - Oracle
toc: true
type: post
featured: true
draft: false
---

En Fiscal Document Capture (FDC), una NF-e de transferencia interna puede permanecer en **Manage Interface Exceptions** sin derivar el número del documento de origen (*source document number*) ni la línea (*source document line*).

En este escenario, la causa identificada fue una diferencia entre la dirección del destinatario informada en la NF-e y la dirección de la ubicación de destino registrada en Oracle. El código postal era diferente y también era necesario revisar los demás datos de la dirección.

## Qué revisar primero

Compare la dirección del documento fiscal con el registro del establecimiento que recibe la mercancía:

- CNPJ del destinatario y la sucursal correspondiente.
- Código postal, calle, número, complemento, barrio, municipio y estado.
- Dirección de entrega informada en el XML de la NF-e, si existe.
- Organización de inventario y ubicación de destino asociadas a la Transfer Order.

No considere automáticamente la dirección principal del CNPJ como dirección de entrega. Confirme que la sucursal y la dirección del comprobante correspondan al lugar de entrega indicado en la NF-e y utilizado por Oracle como destino.

## Cómo afecta la diferencia al análisis

En el flujo de transferencia, FDC necesita relacionar las líneas del documento fiscal con el documento de origen para continuar el procesamiento. La documentación de Oracle explica que una Transfer Order puede ser el documento de origen y que sus datos se utilizan para identificar los artículos y la información de las líneas. La API REST de Transfer Orders también expone atributos de ubicación y código postal de destino.

La documentación pública de Oracle no afirma que el código postal, por sí solo, sea la clave estándar para derivar el número y la línea de la Transfer Order. Por eso, trate la diferencia de dirección como la causa observada en este escenario. Si la derivación sigue fallando después de corregir la dirección, revise también el detalle de la excepción y el mapeo del documento de origen en Collaboration Messaging.

## Corregir la ubicación en Oracle

Acceda a:

~~~text
Setup and Maintenance
> Manufacturing and Supply Chain Materials Management
> Setup
> Enterprise Profile
> Show: All Tasks
> Manage Locations
~~~

Busque la ubicación asociada a la organización de destino de la Transfer Order. Confirme el código, la vigencia y que represente la dirección correcta de recepción. Actualice la dirección y el código postal con base en la dirección validada de la sucursal/lugar de entrega.

Una ubicación representa una dirección física y puede asociarse a organizaciones de inventario. La tarea **Manage Locations** mantiene campos como dirección, ciudad, estado y código postal. Consulte [Create Locations — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fammi/create-locations.html) y [Update existing setup data — Oracle Applications](https://docs.oracle.com/en/cloud/saas/applications-common/26b/oafsm/update-existing-setup-data.html).

## Revisar y reprocesar en FDC

1. Abra el work area **Fiscal Document Capture**.
2. En el panel de tareas, seleccione **Manage Interface Exceptions**.
3. Abra el documento y revise el detalle de la excepción. Confirme si la ubicación/dirección está registrada como causa.
4. Después de corregir el registro, ejecute **Import and Validate Electronic Fiscal Documents** desde **Scheduled Processes**. Para procesar documentos que todavía están en la interfaz, use el parámetro **Fiscal Documents to Validate = New**. Use **All** cuando también necesite validar documentos ya creados en FDC.
5. Vuelva a FDC y confirme si se derivaron el documento de origen y la línea. Luego supervise la validación y la creación del recibo.

Oracle describe **Manage Interface Exceptions** como la página para revisar discrepancias y errores de validación/importación, que pueden resolverse automáticamente o mediante intervención manual. Consulte [Interface Exceptions — Oracle FDC](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/fafdc/interface-exceptions.html). El proceso de importación y validación se documenta en [Import and Validate Electronic Fiscal Documents — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faspc/import-and-validate-electronic-fiscal-documents.html). La creación del recibo depende de completar la validación fiscal, como se describe en [Inbound Shipments for Brazil — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/famli/inbound-shipments-for-brazil.html).

## Si la derivación continúa fallando

Después de confirmar la dirección y reprocesar, valide también:

- Si el XML recibido contiene el CNPJ y la dirección correctos del destinatario/lugar de entrega.
- Si la Transfer Order y la línea están activas y corresponden al artículo y la cantidad de la NF-e.
- Si el número y la línea se envían en los campos esperados por FDC, según el XSL/definición de mensaje de Collaboration Messaging.
- Si el XML utiliza `xPed` y `nItemPed` de forma compatible con el mapeo configurado. Para un caso relacionado con el límite de longitud de `nItemPed`, consulte [Oracle Cloud: conservar el identificador completo de nItemPed en transferencias internas](/es/oracle/fdc-nitemped-infadprod-transfer-order/).

La [visión general de Fiscal Document Capture](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fafdc/overview-of-fiscal-document-capture.html) describe la Transfer Order como un posible documento de origen. Para consultar los atributos de la Transfer Order, incluida la ubicación y el código postal de destino, consulte la [REST API de Transfer Orders — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fasrp/op-transferorders-get.html).

## Referencias

- [Oracle — Interface Exceptions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/fafdc/interface-exceptions.html)
- [Oracle — Overview of Fiscal Document Capture](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fafdc/overview-of-fiscal-document-capture.html)
- [Oracle — Create Locations](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fammi/create-locations.html)
- [Oracle — Import and Validate Electronic Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faspc/import-and-validate-electronic-fiscal-documents.html)
- [Oracle — Inbound Shipments for Brazil](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/famli/inbound-shipments-for-brazil.html)
