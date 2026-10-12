---
title: "Oracle Cloud: automatización de la preparación fiscal de shipments para emitir NF-e"
description: "Cómo OIC, BI Publisher y las API REST permiten reducir la preparación fiscal manual de shipments en Oracle Cloud."
date: 2026-10-12
article_id: "004"
tags: ["Oracle Cloud", "Brazil Localization", "FDG", "OIC", "BI Publisher", "REST API", "NF-e", "SCM"]
categories: ["Oracle"]
toc: true
type: post
featured: true
draft: false
---

La complejidad fiscal brasileña plantea desafíos importantes cuando necesitamos emitir grandes cantidades de notas fiscales electrónicas (NF-e) en Oracle Cloud.

En operaciones con muchas Sales Orders y Transfer Orders, preparar cada shipment para Fiscal Document Generation (FDG) puede convertirse en una tarea repetitiva. Antes de continuar con el proceso fiscal, es necesario completar determinados atributos fiscales y logísticos.

La propuesta consiste en automatizar esa preparación, en lugar de actualizar manualmente cientos de shipments.

## El problema

Crear un shipment en Oracle Cloud no significa necesariamente que todos los campos necesarios para el proceso fiscal brasileño estén cumplimentados.

Según el tipo de operación y la configuración, pueden requerirse:

- Naturaleza de la operación e información fiscal complementaria.
- Indicadores de consumidor final y presencia del destinatario.
- Tipo de transferencia.
- Atributos logísticos, como el código FOB.
- Campos específicos de Brasil en el Descriptive Flexfield (DFF) de la cabecera del shipment.

La introducción manual repetida aumenta la carga operativa y el riesgo de inconsistencias.

## La propuesta de automatización

La alternativa combina Oracle Integration Cloud (OIC), BI Publisher y las API REST de Oracle Fusion SCM para actualizar automáticamente los shipments elegibles.

```text
Sales Order / Transfer Order
            |
         Shipment
            |
    Consulta BI Publisher
            |
      Procesamiento OIC
            |
 REST API: ShipmentUpdate
            |
    Actualización del DFF
            |
 Listo para automatización FDG
```

BI Publisher identifica los shipments que cumplen las reglas establecidas, considerando el tipo de origen, la organización de inventario y el estado de los atributos fiscales. OIC procesa los resultados e invoca la API REST `shipmentTransactionRequests` mediante la acción `ShipmentUpdate`.

El diseño de referencia contempla una ejecución cada diez minutos y el tratamiento individual de los shipments. Esta frecuencia es una decisión de implementación, no un requisito de Oracle.

## Gestión de errores

En una operación de volumen, el error de un registro no debería detener el procesamiento de los demás.

Por eso, el diseño incorpora tratamiento de errores por shipment, seguimiento de ejecuciones en OIC y posibilidad de reprocesamiento después de corregir el problema.

Los criterios de elegibilidad ayudan además a evitar actualizaciones innecesarias.

## Alcance y limitaciones

Esta integración prepara los atributos del shipment. No sustituye la configuración tributaria, no ejecuta por sí sola todo el proceso de generación fiscal ni obtiene la autorización de la NF-e ante la SEFAZ.

Un proceso independiente de automatización del FDG identifica los shipments preparados y continúa el flujo fiscal según la arquitectura implementada.

## Conclusión

Automatizar la preparación de shipments reduce las tareas repetitivas y permite que los usuarios se concentren en las excepciones que necesitan atención.

En escenarios de emisión de NF-e en volumen, esta alternativa puede mejorar la consistencia de los datos antes de la generación de documentos fiscales.

## Referencias

- [Oracle Fusion SCM REST API — Shipment Transaction Requests](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fasrp/op-shipmenttransactionrequests-post.html)
- [Oracle — Fiscal Document Generation](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-configuring-fiscal-document-for-brazil.html)
