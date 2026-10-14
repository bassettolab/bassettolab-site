---
title: "Oracle Cloud: supplier item relationships with Product Hub, FDC and FBDI"
description: "How to create supplier item relationships through FBDI and derive them from FDC data using LACLS and OIC."
date: 2026-10-14
article_id: "007"
tags: ["Oracle Cloud", "Product Hub", "FDC", "FBDI", "OIC", "LACLS", "Trading Partner Items", "SCM", "SQL"]
categories: ["Oracle"]
toc: true
type: post
featured: true
draft: false
---

The same material may have two identifiers: the internal Oracle item number and the code used by its supplier. When an electronic invoice is received, the supplier's XML normally contains its own item code; Oracle Fusion Cloud must find the corresponding internal item.

**Trading Partner Item Relationships** in Product Hub can help reduce repeated manual identification. In the tests reviewed for this article, supplier relationships used **SUPPLIER_ITEM_XREF**.

There are two complementary ways to maintain these relationships: FBDI import and automated derivation from Fiscal Document Capture (FDC).

## 1. What is a Trading Partner Item?

A *Trading Partner Item* represents a product identified by a commercial partner. A relationship connects this external record to an internal Oracle item.

| Attribute | Fictional example |
|---|---|
| Oracle item | INTERNAL_ITEM_001 |
| Supplier item | SUP-98765 |
| Partner type | SUPPLIER |
| Relationship | SUPPLIER_ITEM_XREF |
| Organization | MASTER |

The supplier is as important as the external code: different suppliers may reuse the same code for different products.

### Two approaches

| Approach | Main use | Components |
|---|---|---|
| **FBDI** | Initial migration, bulk imports and controlled corrections | XLSM template, CSV/ZIP, Load Interface File for Import, Item Import |
| **LACLS/OIC** | Ongoing maintenance based on operational data | FDC, BI Publisher, Oracle Integration Cloud and Product Hub |

## 2. Creating relationships through FBDI

Two worksheets of the Oracle item-import template are central to this scenario:

- **EGP_TRADING_PARTNER_ITEMS_INTF** creates the partner's item record.
- **EGP_ITEM_RELATIONSHIPS_INTF** links that item to an Oracle item.

### 2.1. Trading Partner Item

| Technical field | Fictional value |
|---|---|
| TRANSACTION_TYPE | SYNC |
| BATCH_ID | 90001 |
| TP_ITEM_NUMBER | SUP-98765 |
| TP_ITEM_DESC | SAMPLE MATERIAL |
| TP_TYPE | SUPPLIER |
| TRADING_PARTNER_NUMBER | 7000123 |

**Important:** in the documented pre-production test, TRADING_PARTNER_NUMBER accepted **HZ_PARTIES.PARTY_NUMBER**, rather than the supplier number (POZ_SUPPLIERS_V.SEGMENT1) or the internal PARTY_ID. Using the supplier number produced **EGP_TP_PK_MISSING**.

This is an observed test result, not a substitute for checking the partner master data and the current application release.

### 2.2. Item Relationship

| Technical field | Fictional value |
|---|---|
| TRANSACTION_TYPE | SYNC |
| BATCH_ID | 90002 |
| ITEM_RELATIONSHIP_TYPE | SUPPLIER_ITEM_XREF |
| ITEM_NUMBER | INTERNAL_ITEM_001 |
| ORGANIZATION_CODE | MASTER |
| MASTER_ORGANIZATION_CODE | MASTER |
| SOURCE_SYSTEM_CODE | PIMDH |
| TP_ITEM_NUMBER | SUP-98765 |
| TRADING_PARTNER_NUMBER | 7000123 |

The value **PIMDH** came from the tested template; verify the configured source-system code in your instance.

**The two worksheets do not have to use the same batch.** Both example workbooks used a separate BATCH_ID for the partner-item records and their relationships. This allows sequential processing: first import the external item, then import its relationship, running **Item Import once per batch**. For combined loads, plan batches and job parameters according to the template and your environment. The job's Batch ID must match the records being processed.

### 2.3. Import procedure

1. Confirm that the Oracle item exists in the intended organization.
2. Identify the supplier, its PARTY_NUMBER and the supplier item number.
3. Check for an existing partner item or relationship.
4. Fill in the original Oracle XLSM without changing worksheets, headers or macros.
5. Run **Generate CSV File** to create the ZIP.
6. Under **Tools > Scheduled Processes**, run **Load Interface File for Import**.
7. Run **Item Import** for the appropriate batch and review its output and errors.
8. Validate the result in Product Hub or using an authorized query.

A **Succeeded** status for *Load Interface File for Import* only means that data reached the interface tables; **it does not confirm that the relationship was created**.

> **Release-specific caveat:** Oracle's 26C FBDI documentation lists MANUFACTURER, COMPETITOR and CUSTOMER in the Trading Partner Type examples, while the supplied test files successfully used SUPPLIER in one pre-production environment. Verify support and validations for your exact release and setup before adopting this supplier import scenario.

## 3. Automatic derivation from FDC through LACLS

The **Latin America Cloud Local Solution (LACLS) — Item Relationship Derivation** technical guide, dated 2021, describes a solution that derives product relationships from operational information.

For example, a received fiscal document contains a supplier item code that has not been mapped. During FDC handling, a user selects its Oracle item. The integration reads that association and can maintain the relationship in Product Hub. On subsequent documents, the relationship **may** allow FDC to identify the internal item automatically, subject to supplier identification and fiscal-process conditions.

~~~text
Invoice XML / Purchase data
            |
Fiscal Document Capture (FDC)
            |
Supplier item + mapped Oracle item
            |
BI Publisher (extract)
            |
Oracle Integration Cloud (OIC)
            |
Product Hub
            |
SUPPLIER_ITEM_XREF
~~~

### 3.1. Components in the technical guide

| Component | Identifier |
|---|---|
| BI Publisher report | LACLS_BR_ITEM_RELATIONSHIP_UPDATE |
| BI Publisher Data Model | LACLS_BR_ItemRelationShipsDm |
| Scheduled OIC integration | LACLS_BR_FDC_TRADING_RELAT_UPD |
| OIC lookup | LACLS_FDC_TRADING_REL_LKP |

The documented BI Publisher location is **Shared Folders / Custom / Local Solution / BR / FDC x Product Info Item**, with the data model under **Data Models**.

The OIC lookup includes integration settings, trading-partner type and a cutoff date; the guide uses **Supplier** for the partner type. Its scheduled integration is shown as running **once daily**, an example implementation setting rather than a universal Oracle requirement.

The guide references OIC package **LACLS_BR_FDC_TRADING_PARTNER_MGMT.par** and technical reference **33210053**. As the guide dates from 2021, availability and compatibility should be reassessed in the current environment.

### 3.2. Procurement as another data source

The functional document also describes supplier item information originating in a quotation, negotiation, purchasing agreement or purchase order. When that information reaches FDC and is exposed to the integration, it may be used to maintain Product Hub relationships. Actual propagation depends on the implemented business flow.

## 4. SQL validation queries

These statements are adapted from the supplied operational manuals. Their availability in BI Publisher depends on object access and instance permissions.

### 4.1. Supplier Number versus Party Number

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

### 4.2. Existing partner items

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

### 4.3. Existing supplier-item relationships

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

An external item code may exist for multiple suppliers: also verify supplier and organization when interpreting this result.

### 4.4. Interface records for a batch

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

In the documented test, **PROCESS_STATUS = 3** indicated an error. Use the detailed *Item Import* log to establish the actual cause.

## 5. Common problems

| Symptom | Check |
|---|---|
| EGP_TP_PK_MISSING | Verify PARTY_NUMBER and TP_TYPE |
| Invalid Oracle item | Verify ITEM_NUMBER and organization |
| Supplier item not found | Import the Trading Partner Item before its relationship |
| Duplicate relationship | Search for an existing link before re-importing |
| Interface load succeeded but no relationship | Run Item Import for the matching batch and inspect logs |
| ORA-00942 in BI Publisher | Check object exposure and permissions |

## 6. Choosing the approach

Use **FBDI** for initial data conversion and planned bulk maintenance; use **LACLS/OIC** where ongoing learning from fiscal documents has been properly implemented and validated. Both approaches may coexist with appropriate duplicate prevention and error monitoring.

**A product relationship alone does not guarantee that an invoice will complete FDC processing.** Other fiscal rules and validations still apply.

## References

- [Oracle — Overview of Item Relationships](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/fapim/overview-of-item-relationships.html)
- [Oracle — Overview of Import Items](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faicf/overview-of-import-items.html)
- [Oracle — Item Import](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faspc/item-import.html)
- [Oracle — How do I create Trading Partner Items with FBDI?](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/faipr/how-do-i-create-trading-partner-items-with-fbdi.html)
- Oracle LACLS — *Item Relationship Derivation, Technical Installation*, version 1 (2021), reference 33210053, and the supplied FBDI operating manuals.
