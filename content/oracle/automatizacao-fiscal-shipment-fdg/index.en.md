---
title: "Oracle Cloud: automating shipment fiscal preparation for high-volume NF-e issuance"
description: "Using OIC, BI Publisher and REST APIs to reduce manual fiscal preparation of shipments in Oracle Cloud."
date: 2026-10-12
article_id: "004"
tags: ["Oracle Cloud", "Brazil Localization", "FDG", "OIC", "BI Publisher", "REST API", "NF-e", "SCM"]
categories: ["Oracle"]
toc: true
type: post
featured: true
draft: false
---

Brazil's complex tax and fiscal requirements present a challenge when issuing large volumes of electronic invoices (NF-e) in Oracle Cloud.

For businesses processing many Sales Orders and Transfer Orders, preparing each shipment for Fiscal Document Generation (FDG) may become repetitive. Some fiscal and logistics attributes must be completed before the fiscal process can continue.

The idea is to automate this preparation rather than update hundreds of shipments manually.

## The problem

Creating a shipment does not necessarily mean that every field required by the Brazilian fiscal process is already populated.

Depending on the transaction and configuration, the process may require:

- Nature of operation and supplementary fiscal information.
- Final-consumer and customer-presence indicators.
- Transfer order type.
- Logistics attributes such as the FOB code.
- Brazil-specific fields in the shipment header Descriptive Flexfield (DFF).

Repeated manual entry increases workload and the risk of inconsistent data.

## Proposed automation

The solution combines Oracle Integration Cloud (OIC), BI Publisher and Oracle Fusion SCM REST APIs to update eligible shipments.

```text
Sales Order / Transfer Order
            |
         Shipment
            |
     BI Publisher query
            |
       OIC processing
            |
 REST API: ShipmentUpdate
            |
         DFF update
            |
 Ready for FDG automation
```

BI Publisher retrieves shipments matching defined eligibility rules, including source type, inventory organization and fiscal attribute status. OIC processes the results and invokes the `shipmentTransactionRequests` REST API with the `ShipmentUpdate` action.

The referenced design schedules execution every ten minutes and processes shipments one at a time. That interval is an implementation choice, not an Oracle requirement.

## Error handling

For a batch of shipments, a failure affecting a single record should not prevent the others from being processed.

The design therefore provides record-level error handling, OIC monitoring and the ability to reprocess records after the underlying issue has been resolved.

Eligibility checks also help prevent unnecessary updates.

## Scope and limitations

This integration prepares shipment attributes. It does not replace tax configuration, perform the entire fiscal document generation flow or obtain SEFAZ authorization for the NF-e.

A separate FDG automation process identifies eligible updated shipments and continues the fiscal workflow according to the implemented architecture.

## Conclusion

Automating shipment preparation reduces repetitive work and allows users to focus on exceptions that need attention.

For high-volume NF-e operations, this is one practical way to improve data consistency before fiscal document generation.

## References

- [Oracle Fusion SCM REST API — Shipment Transaction Requests](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fasrp/op-shipmenttransactionrequests-post.html)
- [Oracle — Fiscal Document Generation](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-configuring-fiscal-document-for-brazil.html)
