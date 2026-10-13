---
title: "Oracle Cloud: CNPJ, LRU, Location e Inventory Organization en FDC"
description: "Configuración y auditoría de las asociaciones entre LRU, ubicaciones y organizaciones de inventario para FDC."
date: 2026-10-13
article_id: "006"
tags: ["Oracle Cloud", "Brazil Localization", "FDC", "LRU", "CNPJ", "Inventory Organization", "Location", "SQL"]
categories: ["Oracle"]
toc: true
type: post
featured: true
draft: false
---

Registrar el CNPJ en la Legal Reporting Unit (LRU) es solo parte de la parametrización fiscal. También hay que comprobar la Inventory Organization (IO), su Location Address y las asociaciones legales vigentes.

## Relación entre los registros

~~~text
Legal Entity
  └── Legal Reporting Unit (LRU)
       ├── CNPJ Registration
       ├── Associated Inventory Organization
       └── Associated Inventory/Ship-to Location
Inventory Organization ─── Location Address
Location ─── Inventory Organization (when applicable)
~~~

El esquema es conceptual, no una regla obligatoria de relación uno a uno. Oracle documenta la asociación de IO con LRU para ship-from y de Location con LRU para ship-to en transferencias internas.

## Un ejemplo sencillo: dos almacenes

Imagine una empresa con dos almacenes, cada uno con su propio CNPJ brasileño. El Almacén A envía mercancía al Almacén B mediante una transferencia interna de stock.

| Papel en la operación | Almacén A | Almacén B |
|---|---|---|
| Acción | Envía la mercancía | Recibe la mercancía |
| Papel fiscal | Remitente (*Ship-From*) | Destinatario (*Ship-To*) |
| Identificación fiscal | CNPJ de la filial A | CNPJ de la filial B |

El sistema debe responder a dos preguntas: **¿desde qué establecimiento fiscal sale la mercancía?** Y **¿a qué establecimiento fiscal llega?**

### ¿Qué representa cada registro?

| Registro | Explicación sencilla | Ejemplo |
|---|---|---|
| Legal Reporting Unit (LRU) | El establecimiento fiscal en el que se registra el CNPJ | Filial fiscal A |
| Inventory Organization (IO) | La organización de Oracle que controla el stock | Almacén A |
| Location | La dirección/ubicación utilizada en la operación | Dirección del almacén A |

La IO no es el CNPJ y la Location no es la LRU: son registros distintos que deben vincularse según el flujo fiscal.

### ¿Cómo determina Oracle remitente y destinatario?

Para **transferencias internas**, la [documentación oficial de Oracle 26D](https://docs.oracle.com/en/cloud/saas/financials/26d/faufa/define-ship-from-and-ship-to-legal-reporting-units.html) define dos asociaciones:

~~~text
REMITENTE (Ship-From)
Inventory Organization del Almacén A
                    |
                    v
             LRU de la filial A
                    |
                    v
                  CNPJ A

DESTINATARIO (Ship-To)
Location de destino del Almacén B
                    |
                    v
             LRU de la filial B
                    |
                    v
                  CNPJ B
~~~

- **Ship-From:** en `Manage Associated Business Entities`, seleccionar Legal Entity y LRU de origen y añadir una asociación de tipo `Inventory organization` con la IO correspondiente. Para transferencias internas y devoluciones a proveedor, se utiliza para obtener la LRU remitente en `Update Fiscal Attributes`.
- **Ship-To:** para transferencias internas, seleccionar Legal Entity y LRU de destino y añadir una asociación de tipo `Ship-from or to location` con la Location destinataria. El destino se informa en `Edit Shipment`.

En resumen, el Oracle utiliza **la IO de origen para obtener la LRU remitente** y **la Location de destino para obtener la LRU destinataria** en estos flujos. No es obligatorio crear una LRU diferente por cada IO.

### ¿Y en el FDC?

El procedimiento documentado se refiere principalmente a la determinación de las LRUs en **Fiscal Document Generation (FDG)**. No demuestra que esas asociaciones sean suficientes, por sí solas, para encontrar el CNPJ en **Fiscal Document Capture (FDC)**.

En FDC, entrar en `Create Fiscal Document` y buscar el CNPJ en `Receiver Taxpayer ID`. Si aparece, significa que el identificador está visible en esa lista, no que el proceso fiscal completo esté validado. Si falta, revisar registro, vigencia, asociaciones, contexto y permisos.

## Configuración paso a paso

1. Comprobar Legal Entity, LRU y fechas de vigencia.
2. En Manage Registrations, verificar jurisdicción, código CNPJ, número, registro identificativo y fechas.
3. En Manage Inventory Organizations, revisar entidad, estado y Location Address.
4. En Manage Locations, comprobar dirección, estado, vigencia y organización de inventario cuando corresponda.
5. En Manage Associated Business Entities, seleccionar Legal Entity/LRU y añadir los tipos de asociación necesarios según la operación.
6. Validar la consulta en FDC y probar un documento representativo.

## Ejemplo ficticio

| Object | Example |
|---|---|
| LRU | FISCAL BRANCH 02 |
| CNPJ | 12.345.678/0002-90 |
| Inventory Organization | WH02 |
| Location | WAREHOUSE LOCATION 02 |

## SQL 1 — CNPJ duplicados entre LRUs

Busca registros CNPJ vigentes compartidos por distintas LRUs y calcula el estado por las fechas de la LRU.

~~~sql
WITH base AS (
 SELECT DISTINCT e.establishment_id lru_id, e.name lru_name,
 REGEXP_REPLACE(r.registration_number,'[^0-9]','') cnpj,
 e.effective_from,e.effective_to
 FROM xle_etb_profiles e, xle_registrations r, xle_jurisdictions_b j
 WHERE r.source_table='XLE_ETB_PROFILES'
 AND r.source_id=e.establishment_id
 AND r.jurisdiction_id=j.jurisdiction_id
 AND UPPER(j.registration_code_etb) LIKE '%CNPJ%'
 AND TRUNC(SYSDATE) BETWEEN NVL(TRUNC(r.effective_from),TRUNC(SYSDATE))
 AND NVL(TRUNC(r.effective_to),TRUNC(SYSDATE))
)
SELECT b.cnpj,b.lru_id,b.lru_name,
 CASE WHEN TRUNC(SYSDATE) BETWEEN
 NVL(TRUNC(b.effective_from),TRUNC(SYSDATE))
 AND NVL(TRUNC(b.effective_to),TRUNC(SYSDATE))
 THEN 'ACTIVE' ELSE 'INACTIVE' END lru_status,
 COUNT(*) OVER(PARTITION BY b.cnpj) qtd_lrus
FROM base b
WHERE b.cnpj IN (
 SELECT cnpj FROM base WHERE cnpj IS NOT NULL
 GROUP BY cnpj HAVING COUNT(DISTINCT lru_id)>1
)
ORDER BY b.cnpj,b.lru_name;
~~~

## SQL 2 — Asociaciones IO y Location por LRU

Crear el parámetro opcional P_CNPJ (texto) en BI Publisher. La consulta muestra asociaciones fiscales vigentes y la IO asignada a la Location cuando exista.

~~~sql
WITH lru AS (
 SELECT DISTINCT e.establishment_id lru_id,e.name lru_name,
 REGEXP_REPLACE(r.registration_number,'[^0-9]','') cnpj
 FROM xle_etb_profiles e, xle_registrations r, xle_jurisdictions_b j
 WHERE r.source_table='XLE_ETB_PROFILES'
 AND r.source_id=e.establishment_id
 AND r.jurisdiction_id=j.jurisdiction_id
 AND UPPER(j.registration_code_etb) LIKE '%CNPJ%'
 AND TRUNC(SYSDATE) BETWEEN NVL(TRUNC(r.effective_from),TRUNC(SYSDATE))
 AND NVL(TRUNC(r.effective_to),TRUNC(SYSDATE))
)
SELECT l.lru_name,l.cnpj,a.entity_type,a.context,
 a.entity_name,a.entity_id,
 io.organization_code io_code,
 loc.location_code,
 loc.inventory_organization_id location_io_id,
 a.effective_from,a.effective_to
FROM lru l, xle_associations_v a,
 inv_org_parameters io, hr_locations_all_f_vl loc
WHERE a.legal_construct_id=l.lru_id
 AND io.organization_id(+)=CASE WHEN a.entity_type='INVENTORY_ORGANIZATION'
 THEN a.entity_id END
 AND loc.location_id(+)=CASE WHEN a.entity_type IN
 ('INVENTORY_LOCATION','SHIP_TO_LOCATION','BILL_TO_LOCATION')
 THEN a.entity_id END
 AND (loc.location_id IS NULL OR TRUNC(SYSDATE) BETWEEN
 loc.effective_start_date AND loc.effective_end_date)
 AND a.entity_type IN ('INVENTORY_ORGANIZATION','INVENTORY_LOCATION',
 'SHIP_TO_LOCATION','BILL_TO_LOCATION')
 AND TRUNC(SYSDATE) BETWEEN NVL(TRUNC(a.effective_from),TRUNC(SYSDATE))
 AND NVL(TRUNC(a.effective_to),TRUNC(SYSDATE))
 AND (:P_CNPJ IS NULL OR l.cnpj=REGEXP_REPLACE(:P_CNPJ,'[^0-9]',''))
ORDER BY l.cnpj,l.lru_name,a.entity_type,a.entity_name;
~~~

La consulta no devuelve LRUs sin asociaciones ni demuestra la Location Address de la propia IO. Revisar la configuración en pantalla.

## Validación funcional en FDC

Entrar en Fiscal Document Capture → Create Fiscal Document → Receiver Taxpayer ID. Buscar el CNPJ y confirmar la entidad legal. Si no aparece, revisar registro, vigencia, ubicación, asociaciones, BU y seguridad. Que aparezca en la lista no garantiza por sí solo el proceso XML, los impuestos ni la contabilización.

## Puntos de atención

La duplicidad de un CNPJ entre LRUs requiere revisión, pero no demuestra automáticamente un error. Examinar fechas, tipos de asociación y operación fiscal antes de cambiar parámetros.

No publicar capturas, CNPJs ni direcciones reales. Validar antes de modificar producción.

## Referencias

- [Oracle — Define Ship-From and Ship-To Legal Reporting Units](https://docs.oracle.com/en/cloud/saas/financials/26d/faufa/define-ship-from-and-ship-to-legal-reporting-units.html)
- [Oracle — XLE_ASSOCIATIONS_V](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/xleassociationsv-8641.html)
- [Oracle — XLE_REGISTRATIONS](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/xleregistrations-28020.html)
- [Oracle — HR_LOCATIONS_ALL_F_VL](https://docs.oracle.com/en/cloud/saas/human-resources/oedmh/hrlocationsallfvl-8019.html)
