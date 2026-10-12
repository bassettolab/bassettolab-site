---
title: "Oracle Cloud: automating Shipment DFF updates using BI Publisher, OIC and REST"
description: "Technical SQL examples, DFF mapping, the ShipmentUpdate API, monitoring and error handling before fiscal document generation."
date: 2026-10-12
article_id: "005"
tags: ["Oracle Cloud", "Brazil Localization", "SCM", "Shipping", "BI Publisher", "OIC", "REST API", "FDG", "SQL"]
categories: ["Oracle"]
toc: true
type: post
featured: true
draft: false
---

In the [previous article](/en/oracle/automatizacao-fiscal-shipment-fdg/), I described why manually completing fiscal shipment attributes can become a bottleneck for high-volume NF-e issuance in Oracle Cloud. This article goes deeper into the architecture and technical implementation pattern in Oracle Fusion Cloud SCM.

> **Note:** all SQL queries, identifiers and JSON payloads below are illustrative examples using publicly documented Oracle objects. They are not copies of production code. DFF contexts and segments must be configured and verified in each environment.

## 1. Architecture

The approach separates record selection, orchestration and ERP updates:

```text
Oracle SCM / Shipping
        |
        | Shipment created
        v
BI Publisher Data Model (SQL)
        |
        | Eligible shipments
        v
Oracle Integration Cloud (OIC)
        |
        +--> Read response
        +--> Validate and map by operation
        +--> For-Each (one shipment at a time)
                 |
                 v
          REST API ShipmentUpdate
                 |
                 +--> Success: log result
                 +--> Failure: log and continue
        |
        v
Shipment DFF prepared
        |
        v
Independent fiscal generation process (FDG)
```

BI Publisher selects *candidate* shipments. OIC applies mapping rules, invokes the REST API and monitors responses. Fiscal document generation is a separate downstream step.

## 2. Selecting eligible shipments with BI Publisher

The publicly documented `WSH_NEW_DELIVERIES` table stores shipment header data, including `DELIVERY_NAME`, `ORGANIZATION_ID`, `SOURCE_LINE_TYPE`, `ATTRIBUTE_CATEGORY` and `FD_PROCESSING_STATUS`.

For this simplified example, the query selects Sales Orders and Transfer Orders in a parameterized inventory organization, with an empty DFF context and no fiscal processing status:

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

The `P_ORGANIZATION_ID` parameter is defined in the BI Publisher Data Model. No organization ID is hardcoded. The `CASE` expression supplies a logical mapping aid; it is **not** an official fiscal classification.

These filters are only a starting point. A production implementation must check the association with the relevant legal reporting unit, allowed operational statuses, whether a fiscal document is required and whether another process already uses the DFF. An empty `ATTRIBUTE_CATEGORY` is not a universal eligibility rule.

### Query to inspect a shipment

After invoking the REST API, inspect the header fields to confirm the update:

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

`ATTRIBUTE1` and `ATTRIBUTE2` merely illustrate DFF storage. Their mapping to screen fields depends on the configuration and must not be assumed.

### Query to estimate volume

Before choosing the schedule frequency, estimate the number of candidate records:

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

This count represents candidates under the simplified conditions, not the number of NF-e documents that will be issued.

## 3. Building the Data Model

In BI Publisher, create a SQL Data Model with a required `P_ORGANIZATION_ID` parameter and XML output.

OIC receives the dataset, parses the returned XML and iterates through the shipments. Validate the actual XML element names, especially after changing column aliases in the SQL.

There is no need for SQL updates against the underlying Fusion table. The report reads data, while a supported REST service performs the transaction.

## 4. Updating the shipment with a REST API

The publicly documented endpoint is:

```http
POST /fscmRestApi/resources/11.13.18.05/shipmentTransactionRequests
Content-Type: application/json
```

Set `ActionCode` to `ShipmentUpdate` and supply the shipment along with its configured DFF attributes. The conceptual JSON structure is:

```json
{
  "ActionCode": "ShipmentUpdate",
  "shipments": [
    {
      "Shipment": "1000001",
      "shipmentDFF": [
        {
          "__FLEX_Context": "<DFF_CONTEXT>",
          "<DFF_SEGMENT_API_NAME>": "<MAPPED_VALUE>"
        }
      ]
    }
  ]
}
```

The shipment number `1000001` is fictitious. Angle-bracket values are placeholders, so this is **not an executable payload**. Segment API names must match deployed DFF metadata, and values must comply with configured validation and value sets.

Do not confuse native shipment fields, such as `FOB_CODE`, with descriptive flexfield segments. Each value must be mapped to the appropriate API attribute.

### Mapping rules

OIC can apply different rules based on the source transaction type:

```text
If SOURCE_LINE_TYPE = SALES_ORDER:
    apply rules for sales
If SOURCE_LINE_TYPE = TRANSFER_ORDER:
    apply rules for transfers
Otherwise:
    skip and log the reason
```

This is logical pseudocode, not a complete functional tax rule. Actual fiscal values cannot be inferred from source type alone. Also distinguish a JSON `null` from the string `"null"`; they have different meanings.

## 5. OIC orchestration

A practical integration can follow these steps:

1. Create a *Scheduled Orchestration* and select a frequency appropriate for the workload.
2. Invoke the BI Publisher Data Model through an authenticated ERP connection.
3. Parse the XML response into a list of shipment records.
4. Iterate using `For-Each`.
5. Within a `Scope`, build the JSON and call `ShipmentUpdate`.
6. Inspect the API's functional result and record success or failure.
7. Use a local fault handler to log the failed shipment and continue with the others.
8. Treat connection or extraction failures as integration-level errors and report them to monitoring.

An HTTP success response alone does not necessarily prove that every intended update was completed. Check the transaction result and, when needed, inspect the updated data in Oracle Fusion.

## 6. Idempotency and safe processing

Scheduled integrations need safeguards:

- Recheck shipment eligibility before an update.
- Do not overwrite DFF contexts or segments owned by other workflows.
- Log shipment identifier, execution time, outcome and correlation reference.
- Keep credentials in OIC connections, not in payloads or application logs.
- Separate transient failures from persistent configuration errors.
- Avoid overlapping executions that may update the same shipment.

Use BI Publisher for read-only queries and supported ERP APIs for transactional updates.

## 7. Validation and monitoring

To validate results, navigate to **Supply Chain Execution > Inventory Management > Manage Shipments**, search by shipment number and review the associated attributes.

OIC monitoring should show the number of identified records, successful updates, failures and cases requiring manual intervention.

Test Sales Orders, Transfer Orders, existing DFF values, shipments already undergoing fiscal processing, invalid payloads and temporary API outages as separate cases.

## Conclusion

The REST POST is the easy part. The main engineering challenge lies in correctly selecting shipments, mapping fiscal attributes and preventing an automated process from modifying records it should leave untouched.

BI Publisher for extraction, OIC for orchestration and REST APIs for updates provide a maintainable architecture, while keeping fiscal document generation and NF-e authorization as separate responsibilities.

## Official references

- [Oracle — WSH_NEW_DELIVERIES (Data Model)](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26a/oedsc/wshnewdeliveries-17278.html)
- [Oracle — REST API: Create Shipment Transaction Request](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fasrp/op-shipmenttransactionrequests-post.html)
- [Oracle — Fiscal Document Generation](https://docs.oracle.com/en/cloud/saas/financials/25d/faufa/fiscal-document-generation.html)
- [Oracle — Manage Brazil Outbound Shipments](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/famlo/how-you-manage-brazil-outbound-shipments.html)
