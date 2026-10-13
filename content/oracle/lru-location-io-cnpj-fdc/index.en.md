---
title: "Oracle Cloud: CNPJ, LRU, Location and Inventory Organization in FDC"
description: "Configuring and auditing LRU, location and inventory organization associations for Brazilian Fiscal Document Capture."
date: 2026-10-13
article_id: "006"
tags: ["Oracle Cloud", "Brazil Localization", "FDC", "LRU", "CNPJ", "Inventory Organization", "Location", "SQL"]
categories: ["Oracle"]
toc: true
type: post
featured: true
draft: false
---

Registering a CNPJ on the Legal Reporting Unit (LRU) is only one part of Brazilian fiscal setup. The Inventory Organization (IO), its Location Address and the effective legal associations must also be consistent.

## How the records relate

~~~text
Legal Entity
  └── Legal Reporting Unit (LRU)
       ├── CNPJ Registration
       ├── Associated Inventory Organization
       └── Associated Inventory/Ship-to Location
Inventory Organization ─── Location Address
Location ─── Inventory Organization (when applicable)
~~~

This diagram is conceptual, not a universal one-to-one rule. Oracle documents the IO-to-LRU association for ship-from and Location-to-LRU association for ship-to in internal transfers.

## A simple example: two warehouses

### 1. Practical example

<style>
.bl-lru-example { margin: 1.25rem 0; border: 1px solid rgba(150, 150, 150, .38); border-radius: 10px; padding: 1.35rem 1.15rem 1.05rem; color: inherit; }
.bl-lru-example .bl-lru-depots { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.bl-lru-example .bl-lru-depot { text-align: center; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: .25rem; }
.bl-lru-example .bl-lru-icon { width: 26px; height: 26px; margin-bottom: .15rem; opacity: .9; }
.bl-lru-example .bl-lru-name { font-size: .96rem; font-weight: 600; }
.bl-lru-example .bl-lru-taxid, .bl-lru-example .bl-lru-action { font-size: .8rem; line-height: 1.5; opacity: .85; overflow-wrap: anywhere; }
.bl-lru-example .bl-lru-transfer { display: flex; align-items: center; justify-content: center; gap: .55rem; margin-top: 1.4rem; font-size: .85rem; }
.bl-lru-example .bl-lru-transfer svg { width: 18px; height: 18px; }
@media (max-width: 480px) {
  .bl-lru-example { padding: 1rem .65rem; }
  .bl-lru-example .bl-lru-depots { gap: .45rem; }
  .bl-lru-example .bl-lru-name { font-size: .85rem; }
  .bl-lru-example .bl-lru-taxid, .bl-lru-example .bl-lru-action { font-size: .68rem; }
}
</style>
<figure class="bl-lru-example" aria-label="Stock transfer">
  <div class="bl-lru-depots">
    <div class="bl-lru-depot">
      <svg class="bl-lru-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 20V8l9-5 9 5v12H3Z"/><path d="M7 20v-9h10v9M7 14h10M7 17h10M9 8h6"/></svg>
      <span class="bl-lru-name">Warehouse A</span>
      <span class="bl-lru-taxid">CNPJ 12.345.678/0001-XX</span>
      <span class="bl-lru-action">Ships goods</span>
    </div>
    <div class="bl-lru-depot">
      <svg class="bl-lru-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 20V8l9-5 9 5v12H3Z"/><path d="M7 20v-9h10v9M7 14h10M7 17h10M9 8h6"/></svg>
      <span class="bl-lru-name">Warehouse B</span>
      <span class="bl-lru-taxid">CNPJ 12.345.678/0002-XX</span>
      <span class="bl-lru-action">Receives goods</span>
    </div>
  </div>
  <figcaption class="bl-lru-transfer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 17H3V6h12v11h-1M15 10h4l3 3v4h-2"/><circle cx="7.5" cy="17.5" r="2"/><circle cx="17.5" cy="17.5" r="2"/></svg><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg><span>Stock transfer</span></figcaption>
</figure>

When Warehouse A transfers goods to Warehouse B, Oracle needs to know:

- Which CNPJ identifies the sender on the fiscal document?
- Which CNPJ identifies the recipient?

### How does Oracle identify sender and receiver?

For **internal transfers**, the [official Oracle 26D documentation](https://docs.oracle.com/en/cloud/saas/financials/26d/faufa/define-ship-from-and-ship-to-legal-reporting-units.html) defines two separate mappings:

~~~text
SENDER (Ship-From)
Inventory Organization of Warehouse A
                   |
                   v
            LRU of Branch A
                   |
                   v
                CNPJ A

RECEIVER (Ship-To)
Destination Location of Warehouse B
                   |
                   v
            LRU of Branch B
                   |
                   v
                CNPJ B
~~~

- **Ship-From:** in `Manage Associated Business Entities`, select the ship-from Legal Entity and LRU, then create an `Inventory organization` association for the correct IO. For internal transfers and supplier returns, Oracle uses this configuration to default the ship-from LRU on `Update Fiscal Attributes`.
- **Ship-To:** for internal transfers, select the destination Legal Entity and LRU, then create a `Ship-from or to location` association for the destination Location. The ship-to location is captured on `Edit Shipment`.

In short, Oracle uses the **source IO to determine the source LRU** and the **destination Location to determine the destination LRU** for these specific fiscal shipment processes. An individual LRU is not necessarily required for every IO.

### How does this affect FDC?

The cited Oracle procedure primarily describes LRU determination during **Fiscal Document Generation (FDG)**. It does not establish that these associations alone guarantee CNPJ selection in **Fiscal Document Capture (FDC)**.

In FDC, open `Create Fiscal Document` and search `Receiver Taxpayer ID` for the expected CNPJ. A visible result confirms the taxpayer identifier can be found in that lookup, not that the entire fiscal flow will succeed. If absent, review the registration, effective dates, relevant associations, transaction context and user access.

## Setup checklist

1. Verify Legal Entity, LRU and effective dates.
2. In Manage Registrations, confirm Brazilian CNPJ jurisdiction, code, number, identifying registration and validity.
3. In Manage Inventory Organizations, check the entity, status and Location Address.
4. In Manage Locations, check address, status, effective dates and the related Inventory Organization when applicable.
5. In Manage Associated Business Entities, select the Legal Entity/LRU scope and create the association types required by the transaction.
6. Test the FDC lookup and an actual representative document.

## Fictional example

| Object | Example |
|---|---|
| LRU | FISCAL BRANCH 02 |
| CNPJ | 12.345.678/0002-90 |
| Inventory Organization | WH02 |
| Location | WAREHOUSE LOCATION 02 |

## SQL 1 — Duplicate CNPJ across LRUs

Finds currently effective registrations shared by different LRUs; LRU status is calculated from effective dates.

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

## SQL 2 — IO and Location associations by LRU

Create an optional text parameter P_CNPJ in BI Publisher. This query lists effective fiscal associations and the Inventory Organization assigned to a Location when applicable.

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

LRUs without associations do not appear. The IO's own Location Address must be checked separately. Association types represent different business purposes.

## Functional verification in FDC

Open Fiscal Document Capture → Create Fiscal Document → Receiver Taxpayer ID. Search for the CNPJ and verify the associated legal entity. If it is absent, inspect the registration, dates, location, associations, BU and security. Lookup visibility alone does not guarantee successful XML processing, taxation or accounting.

## Important considerations

A duplicate CNPJ across LRUs should be investigated but is not necessarily an error. Consider effective dates, association types and the underlying fiscal transaction before making changes.

Avoid publishing real tax IDs, addresses or production screenshots. Validate changes before touching production.

## References

- [Oracle — Define Ship-From and Ship-To Legal Reporting Units](https://docs.oracle.com/en/cloud/saas/financials/26d/faufa/define-ship-from-and-ship-to-legal-reporting-units.html)
- [Oracle — XLE_ASSOCIATIONS_V](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/xleassociationsv-8641.html)
- [Oracle — XLE_REGISTRATIONS](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/xleregistrations-28020.html)
- [Oracle — HR_LOCATIONS_ALL_F_VL](https://docs.oracle.com/en/cloud/saas/human-resources/oedmh/hrlocationsallfvl-8019.html)
