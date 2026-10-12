---
title: "Oracle Cloud: actualización automática del DFF de Shipments con BI Publisher, OIC y REST"
description: "Ejemplos técnicos de SQL, mapeo de DFF, API ShipmentUpdate, seguimiento y gestión de errores antes del FDG."
date: 2026-10-12
article_id: "005"
tags: ["Oracle Cloud", "Brazil Localization", "SCM", "Shipping", "BI Publisher", "OIC", "REST API", "FDG", "SQL"]
categories: ["Oracle"]
toc: true
type: post
featured: true
draft: false
---

En el [artículo anterior](/es/oracle/automatizacao-fiscal-shipment-fdg/), expliqué por qué rellenar manualmente los atributos fiscales de cada shipment puede convertirse en un cuello de botella cuando se emiten muchas NF-e en Oracle Cloud. Ahora veremos la arquitectura y un ejemplo técnico de este patrón de automatización en Oracle Fusion Cloud SCM.

> **Nota:** las consultas SQL, los identificadores y el JSON de este artículo son ejemplos didácticos basados en objetos documentados públicamente por Oracle. No son copias de código de producción. Los contextos y segmentos del DFF deben configurarse y validarse en cada entorno.

## 1. Arquitectura

La solución separa la selección de registros, la orquestación y la actualización del ERP:

```text
Oracle SCM / Shipping
        |
        | Shipment creado
        v
BI Publisher Data Model (SQL)
        |
        | Shipments elegibles
        v
Oracle Integration Cloud (OIC)
        |
        +--> Leer respuesta
        +--> Validar y mapear por operación
        +--> For-Each (uno por uno)
                 |
                 v
          REST API ShipmentUpdate
                 |
                 +--> Éxito: registrar resultado
                 +--> Error: registrar y continuar
        |
        v
Shipment con DFF preparado
        |
        v
Proceso fiscal independiente (FDG)
```

BI Publisher identifica shipments *candidatos*. OIC aplica las reglas, llama a la API REST y supervisa las respuestas. La generación del documento fiscal es una fase posterior e independiente.

## 2. Selección de shipments elegibles con BI Publisher

La tabla pública `WSH_NEW_DELIVERIES` almacena los datos de cabecera de los shipments. Incluye `DELIVERY_NAME`, `ORGANIZATION_ID`, `SOURCE_LINE_TYPE`, `ATTRIBUTE_CATEGORY` y `FD_PROCESSING_STATUS`.

En este ejemplo simplificado, la consulta selecciona Sales Orders y Transfer Orders de una organización pasada como parámetro, sin contexto DFF informado ni estado de procesamiento fiscal:

```sql
SELECT
    wnd.delivery_id,
    wnd.delivery_name       AS shipment_number,
    wnd.organization_id,
    wnd.source_line_type,
    wnd.attribute_category  AS dff_context,
    wnd.fd_processing_status,
    CASE
        WHEN wnd.source_line_type = 'SALES_ORDER'
            THEN 'SALE'
        WHEN wnd.source_line_type = 'TRANSFER_ORDER'
            THEN 'TRANSFER'
    END AS operation_type
FROM
    wsh_new_deliveries wnd
WHERE
    wnd.organization_id = :P_ORGANIZATION_ID
    AND wnd.source_line_type IN (
        'SALES_ORDER',
        'TRANSFER_ORDER'
    )
    AND wnd.attribute_category IS NULL
    AND wnd.fd_processing_status IS NULL
ORDER BY
    wnd.delivery_id
```

El parámetro `P_ORGANIZATION_ID` se configura en el Data Model de BI Publisher; no se publica ningún ID real. La expresión `CASE` sirve únicamente para apoyar el mapeo lógico, **no** es una clasificación fiscal oficial.

Los filtros son un punto de partida, no una regla definitiva. En producción debemos validar la unidad fiscal asociada, los estados operativos permitidos, si la operación requiere documento fiscal y si otro proceso ya utiliza el DFF. `ATTRIBUTE_CATEGORY IS NULL` no es un criterio universal.

### Consulta para comprobar un shipment

Después de invocar la API REST, podemos comprobar los campos de cabecera:

```sql
SELECT
    wnd.delivery_name,
    wnd.organization_id,
    wnd.source_line_type,
    wnd.attribute_category,
    wnd.attribute1,
    wnd.attribute2,
    wnd.fob_code,
    wnd.fd_processing_status,
    wnd.last_update_date
FROM
    wsh_new_deliveries wnd
WHERE
    wnd.organization_id = :P_ORGANIZATION_ID
    AND wnd.delivery_name = :P_SHIPMENT_NUMBER
```

`ATTRIBUTE1` y `ATTRIBUTE2` solo ilustran cómo se almacenan segmentos del DFF. Su correspondencia con los campos funcionales depende de la configuración y debe verificarse.

### Consulta para estimar el volumen

Antes de establecer la frecuencia de ejecución, conviene conocer la cantidad de candidatos:

```sql
SELECT
    wnd.source_line_type,
    COUNT(*) AS total_shipments,
    SUM(
        CASE
            WHEN wnd.attribute_category IS NULL
             AND wnd.fd_processing_status IS NULL
            THEN 1 ELSE 0
        END
    ) AS candidates_for_review
FROM
    wsh_new_deliveries wnd
WHERE
    wnd.organization_id = :P_ORGANIZATION_ID
    AND wnd.source_line_type IN (
        'SALES_ORDER',
        'TRANSFER_ORDER'
    )
GROUP BY
    wnd.source_line_type
ORDER BY
    wnd.source_line_type
```

Esta cifra representa registros candidatos según filtros simplificados, no la cantidad de NF-e que se emitirán.

## 3. Construcción del Data Model

En BI Publisher se crea un Data Model SQL, con el parámetro obligatorio `P_ORGANIZATION_ID` y salida XML.

OIC recibe el resultado, interpreta los elementos XML y recorre los shipments. Es importante verificar los nombres de los nodos que genera el Data Model, especialmente cuando se modifican aliases en la consulta.

No es necesario ejecutar modificaciones SQL sobre las tablas Fusion. El reporte realiza la lectura y un servicio REST soportado por Oracle realiza la actualización transaccional.

## 4. Actualización mediante API REST

El endpoint público es:

```http
POST /fscmRestApi/resources/11.13.18.05/shipmentTransactionRequests
Content-Type: application/json
```

Con `ActionCode` establecido como `ShipmentUpdate`, enviamos el shipment y los atributos de su DFF configurado. La estructura conceptual del JSON es:

```json
{
  "ActionCode": "ShipmentUpdate",
  "shipments": [
    {
      "Shipment": "1000001",
      "shipmentDFF": [
        {
          "__FLEX_Context": "<CONTEXTO_DFF>",
          "<NOMBRE_API_DEL_SEGMENTO>": "<VALOR_ASIGNADO>"
        }
      ]
    }
  ]
}
```

El número `1000001` es ficticio. Los textos entre signos `< >` son marcadores que deben sustituirse; este payload **no puede ejecutarse tal como aparece**. Los nombres de los segmentos deben corresponder al DFF desplegado y sus valores deben cumplir las reglas y listas configuradas.

No debemos confundir campos nativos del shipment, como `FOB_CODE`, con segmentos del DFF. Cada valor tiene que utilizar el atributo correcto en la API.

### Reglas de mapeo

OIC puede distinguir el tipo de operación:

```text
Si SOURCE_LINE_TYPE = SALES_ORDER:
    aplicar reglas para ventas
Si SOURCE_LINE_TYPE = TRANSFER_ORDER:
    aplicar reglas para transferencias
En otro caso:
    omitir y registrar el motivo
```

Este pseudocódigo muestra la lógica general, no las reglas tributarias completas. Los valores fiscales concretos no deben inferirse únicamente del tipo de operación. También debemos diferenciar un `null` de JSON de una cadena `"null"`: no tienen el mismo significado.

## 5. Orquestación en OIC

Una implementación puede estructurarse de este modo:

1. Crear una integración *Scheduled Orchestration* con una frecuencia ajustada al volumen.
2. Invocar el Data Model de BI Publisher mediante una conexión autenticada al ERP.
3. Interpretar el XML y construir la lista de shipments.
4. Recorrer los registros mediante `For-Each`.
5. Dentro de un `Scope`, preparar el JSON y llamar a `ShipmentUpdate`.
6. Examinar el resultado funcional de la API y registrar éxito o error.
7. Ante un fallo individual, registrarlo en un manejador local y continuar con los demás.
8. Ante fallos de conexión o extracción, marcar la ejecución como errónea y enviarla a monitorización.

Una respuesta HTTP correcta, por sí sola, no garantiza que todas las modificaciones esperadas se hayan completado. Conviene examinar el resultado de la transacción y verificar los datos en el ERP cuando sea necesario.

## 6. Idempotencia y control de actualizaciones

Las integraciones programadas requieren algunas precauciones:

- Comprobar nuevamente la elegibilidad antes de actualizar.
- No sobrescribir contextos ni segmentos DFF utilizados por otros procesos.
- Registrar el shipment, la fecha de ejecución, el resultado y una referencia de seguimiento.
- Mantener las credenciales en las conexiones de OIC, nunca en los logs o en el payload.
- Distinguir los errores transitorios de los errores persistentes de configuración.
- Evitar la ejecución simultánea de procesos que actualicen el mismo shipment.

Utilizamos BI Publisher para consultas de lectura y las API soportadas por Oracle para cambios transaccionales.

## 7. Validación y seguimiento

Para comprobar el resultado, podemos acceder a **Supply Chain Execution > Inventory Management > Manage Shipments**, buscar el shipment y revisar sus atributos.

El seguimiento en OIC debe permitir conocer cuántos registros fueron identificados, actualizados, rechazados o quedaron pendientes de intervención.

Conviene probar por separado Sales Orders, Transfer Orders, shipments con DFF informado, registros en procesamiento fiscal, payloads incorrectos e indisponibilidad temporal de la API.

## Conclusión

La llamada POST es solo una parte del trabajo. El reto técnico consiste en seleccionar correctamente los shipments, mapear los atributos fiscales y evitar que la automatización modifique datos fuera de su alcance.

BI Publisher para la extracción, OIC para la orquestación y REST para las actualizaciones permiten separar responsabilidades sin confundir la preparación fiscal con la emisión y autorización de la NF-e.

## Referencias oficiales

- [Oracle — WSH_NEW_DELIVERIES (Data Model)](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26a/oedsc/wshnewdeliveries-17278.html)
- [Oracle — REST API: Create Shipment Transaction Request](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fasrp/op-shipmenttransactionrequests-post.html)
- [Oracle — Fiscal Document Generation](https://docs.oracle.com/en/cloud/saas/financials/25d/faufa/fiscal-document-generation.html)
- [Oracle — Manage Brazil Outbound Shipments](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/famlo/how-you-manage-brazil-outbound-shipments.html)
