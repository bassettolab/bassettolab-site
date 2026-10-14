---
title: "Oracle Cloud: relaciones de artículos de proveedores con Product Hub, FDC y FBDI"
description: "Cómo cargar relaciones Supplier Item con FBDI y derivarlas desde FDC mediante LACLS y OIC."
date: 2026-10-14
article_id: "007"
tags: ["Oracle Cloud", "Product Hub", "FDC", "FBDI", "OIC", "LACLS", "Trading Partner Items", "SCM", "SQL"]
categories: ["Oracle"]
toc: true
type: post
featured: true
draft: false
---

Un mismo material puede tener dos códigos: el identificador interno del ERP y el utilizado por el proveedor. Al recibir una factura electrónica, el XML suele contener el código del emisor; Oracle Fusion Cloud necesita encontrar el artículo interno correspondiente.

Las **relaciones de artículos de socios comerciales** (*Trading Partner Item Relationships*) del Product Hub ayudan a evitar la identificación manual repetitiva. Los ejemplos analizados utilizan **SUPPLIER_ITEM_XREF** para las relaciones con proveedores.

Existen dos formas complementarias de mantenerlas: la importación FBDI y la derivación automática desde Fiscal Document Capture (FDC).

## 1. ¿Qué es un Trading Partner Item?

Un *Trading Partner Item* representa un producto identificado mediante el código de un socio comercial. La relación conecta ese registro externo con un artículo Oracle.

| Información | Ejemplo ficticio |
|---|---|
| Artículo Oracle | ITEM_INTERNO_001 |
| Artículo del proveedor | PROV-98765 |
| Tipo de socio | SUPPLIER |
| Relación | SUPPLIER_ITEM_XREF |
| Organización | MASTER |

También es necesario identificar al proveedor: dos empresas distintas pueden utilizar el mismo código para productos diferentes.

### Dos estrategias

| Estrategia | Aplicación | Componentes |
|---|---|---|
| **FBDI** | Migración inicial, cargas masivas y correcciones controladas | XLSM, CSV/ZIP, Load Interface File for Import, Item Import |
| **LACLS/OIC** | Mantenimiento recurrente basado en datos operativos | FDC, BI Publisher, Oracle Integration Cloud y Product Hub |

## 2. Creación mediante FBDI

El archivo de importación de artículos de Oracle contiene varias hojas. Para este escenario destacan dos:

- **EGP_TRADING_PARTNER_ITEMS_INTF**: registra el artículo del proveedor.
- **EGP_ITEM_RELATIONSHIPS_INTF**: vincula ese artículo externo con el artículo interno de Oracle.

### 2.1. Trading Partner Item

| Campo técnico | Valor ficticio |
|---|---|
| TRANSACTION_TYPE | SYNC |
| BATCH_ID | 90001 |
| TP_ITEM_NUMBER | PROV-98765 |
| TP_ITEM_DESC | MATERIAL DE EJEMPLO |
| TP_TYPE | SUPPLIER |
| TRADING_PARTNER_NUMBER | 7000123 |

**Atención al TRADING_PARTNER_NUMBER.** En las pruebas documentadas de preproducción se validó el uso de **HZ_PARTIES.PARTY_NUMBER**, en lugar de Supplier Number (POZ_SUPPLIERS_V.SEGMENT1) o PARTY_ID. Al utilizar Supplier Number, la importación devolvió **EGP_TP_PK_MISSING**.

Es un resultado del entorno probado: siempre deben comprobarse los identificadores y la versión del sistema.

### 2.2. Item Relationship

| Campo técnico | Valor ficticio |
|---|---|
| TRANSACTION_TYPE | SYNC |
| BATCH_ID | 90002 |
| ITEM_RELATIONSHIP_TYPE | SUPPLIER_ITEM_XREF |
| ITEM_NUMBER | ITEM_INTERNO_001 |
| ORGANIZATION_CODE | MASTER |
| MASTER_ORGANIZATION_CODE | MASTER |
| SOURCE_SYSTEM_CODE | PIMDH |
| TP_ITEM_NUMBER | PROV-98765 |
| TRADING_PARTNER_NUMBER | 7000123 |

**PIMDH** fue el código del sistema de origen utilizado en el ejemplo; se debe confirmar su configuración en el entorno.

**No es obligatorio utilizar el mismo BATCH_ID en ambas hojas.** Los dos libros de referencia tienen lotes distintos para artículos de socios comerciales y relaciones. Así se puede ejecutar primero el registro del artículo externo y después su relación, utilizando **Item Import para cada lote**. En una carga combinada, es necesario planificar los lotes y parámetros según el template y el entorno. El Batch ID del proceso debe coincidir con los registros que se van a importar.

### 2.3. Proceso de importación

1. Confirmar el artículo Oracle y su organización.
2. Identificar el proveedor, su PARTY_NUMBER y el código externo.
3. Comprobar si ya existen el artículo externo o la relación.
4. Completar el XLSM original sin cambiar hojas, encabezados ni macros.
5. Ejecutar **Generate CSV File** para crear el ZIP.
6. En **Tools > Scheduled Processes**, ejecutar **Load Interface File for Import**.
7. Ejecutar **Item Import** para el lote correspondiente y revisar sus mensajes.
8. Validar la creación en Product Hub o mediante una consulta autorizada.

El estado **Succeeded** de *Load Interface File for Import* confirma la carga en las tablas de interfaz, **no la creación definitiva de la relación**.

> **Consideración de versión:** la documentación Oracle FBDI para 26C enumera MANUFACTURER, COMPETITOR y CUSTOMER en los ejemplos de Trading Partner Type, mientras que los archivos y la prueba de preproducción analizados utilizaron SUPPLIER. Es necesario verificar su soporte y validaciones en la release y configuración concretas.

## 3. Derivación automática mediante FDC y LACLS

La documentación **Latin America Cloud Local Solution (LACLS) — Item Relationship Derivation**, de 2021, describe una integración para mantener relaciones a partir de información operativa.

Por ejemplo, una nota fiscal recibida contiene un código externo todavía no asociado. Durante la gestión del documento en FDC, el usuario selecciona el artículo Oracle correcto. La integración extrae esa correspondencia y puede registrarla en Product Hub. En documentos posteriores, la relación **puede** permitir identificar automáticamente el artículo interno, siempre que se cumplan las condiciones de identificación y las reglas del proceso fiscal.

~~~text
XML / Datos de compras
           |
Fiscal Document Capture (FDC)
           |
Código del proveedor + artículo Oracle
           |
BI Publisher (extracción)
           |
Oracle Integration Cloud (OIC)
           |
Product Hub
           |
SUPPLIER_ITEM_XREF
~~~

### 3.1. Componentes documentados

| Componente | Identificador |
|---|---|
| Informe BI Publisher | LACLS_BR_ITEM_RELATIONSHIP_UPDATE |
| Data Model BI Publisher | LACLS_BR_ItemRelationShipsDm |
| Integración programada | LACLS_BR_FDC_TRADING_RELAT_UPD |
| Lookup OIC | LACLS_FDC_TRADING_REL_LKP |

El informe se almacena en **Shared Folders / Custom / Local Solution / BR / FDC x Product Info Item**, con el Data Model en **Data Models**.

El lookup incorpora valores de integración, tipo de socio y fecha de corte. En la guía se utiliza **Supplier** como tipo de socio. Se muestra una ejecución de la integración **cada día**, una decisión de implementación y no una frecuencia obligatoria de Oracle.

La guía cita el paquete **LACLS_BR_FDC_TRADING_PARTNER_MGMT.par** y la referencia técnica **33210053**. Al tratarse de documentación de 2021, deben comprobarse la disponibilidad de los artefactos y su compatibilidad con la versión actual.

### 3.2. Origen de los datos en Procurement

El documento funcional también contempla información de Supplier Item presente en cotizaciones, negociaciones, acuerdos y órdenes de compra. Si esos datos llegan a FDC y están disponibles para la integración, pueden utilizarse para mantener las relaciones en Product Hub. El comportamiento exacto depende del flujo implantado.

## 4. Consultas SQL de validación

Las siguientes consultas proceden de los manuales operativos analizados, con parámetros generalizados. Su ejecución depende del acceso a los objetos desde BI Publisher.

### 4.1. Supplier Number y Party Number

~~~sql
SELECT
    ps.segment1    AS supplier_number,
    ps.vendor_name AS supplier_name,
    ps.vendor_id,
    ps.party_id,
    hp.party_number AS trading_partner_number
FROM poz_suppliers_v ps
JOIN hz_parties hp
  ON hp.party_id = ps.party_id
WHERE ps.segment1 = :P_SUPPLIER_NUMBER
ORDER BY ps.vendor_name
~~~

### 4.2. Trading Partner Items existentes

~~~sql
SELECT
    tpi.tp_item_id,
    tpi.tp_item_number,
    tpi.tp_item_desc,
    tpi.tp_type,
    hp.party_number AS trading_partner_number
FROM egp_trading_partner_items tpi
JOIN hz_parties hp
  ON hp.party_id = tpi.trading_partner_id
WHERE tpi.tp_type = 'SUPPLIER'
  AND tpi.tp_item_number = :P_SUPPLIER_ITEM
ORDER BY hp.party_number
~~~

### 4.3. Relaciones registradas

~~~sql
SELECT
    x.item_relationship_id,
    x.supplier_id,
    x.tp_item_id,
    x.supplier_item_num,
    x.inventory_item_id,
    x.master_organization_id
FROM egp_search_tpi_sup_xrefs_v x
WHERE x.supplier_item_num = :P_SUPPLIER_ITEM
ORDER BY x.supplier_id
~~~

Un mismo código externo puede pertenecer a varios proveedores. Para una validación completa, compruebe también el proveedor y la organización.

### 4.4. Registros del lote en la interfaz

~~~sql
SELECT
    transaction_id,
    batch_id,
    tp_item_number,
    tp_type,
    trading_partner_number,
    transaction_type,
    process_status
FROM egp_trading_partner_items_intf
WHERE batch_id = :P_BATCH_ID
ORDER BY transaction_id DESC
~~~

En la prueba documentada, **PROCESS_STATUS = 3** indicaba un error. El diagnóstico final debe basarse en los mensajes detallados de *Item Import*.

## 5. Problemas frecuentes

| Síntoma | Comprobación |
|---|---|
| EGP_TP_PK_MISSING | Validar PARTY_NUMBER y TP_TYPE |
| Artículo Oracle inválido | Verificar ITEM_NUMBER y organización |
| Supplier Item no localizado | Importar el Trading Partner Item antes de crear su relación |
| Relación duplicada | Buscar el vínculo antes de reenviarlo |
| Carga de interfaz correcta, sin relación | Ejecutar Item Import para el Batch ID adecuado y revisar logs |
| ORA-00942 en BI Publisher | Verificar permisos y exposición del objeto |

## 6. ¿Qué estrategia utilizar?

**FBDI** es útil para migraciones y cargas masivas planificadas. **LACLS/OIC** puede reducir tareas repetitivas de identificación en las recepciones fiscales cuando el proceso está instalado y validado.

Pueden coexistir, siempre que se controlen duplicidades, identificadores y errores. **La existencia de una relación no garantiza, por sí sola, el procesamiento correcto de cualquier nota fiscal en FDC**: continúan aplicándose las validaciones fiscales y del proceso.

## Referencias

- [Oracle — Overview of Item Relationships](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/fapim/overview-of-item-relationships.html)
- [Oracle — Overview of Import Items](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faicf/overview-of-import-items.html)
- [Oracle — Item Import](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faspc/item-import.html)
- [Oracle — How do I create Trading Partner Items with FBDI?](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/faipr/how-do-i-create-trading-partner-items-with-fbdi.html)
- Oracle LACLS — *Item Relationship Derivation, Technical Installation*, versión 1 (2021), referencia 33210053, y los manuales operativos FBDI analizados.
