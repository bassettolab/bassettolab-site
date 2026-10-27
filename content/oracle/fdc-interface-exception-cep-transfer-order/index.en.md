---
title: "Oracle Cloud FDC: Transfer Order source number and line aren't derived because of a postal code mismatch"
date: 2026-10-27
article_id: "008"
description: "How to investigate NF-e lines stuck in FDC Interface Exceptions when the destination location has a postal code mismatch and the Transfer Order isn't derived."
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

In Fiscal Document Capture (FDC), an inbound NF-e for an internal transfer can remain in **Manage Interface Exceptions** without deriving the source document number and source document line.

In this scenario, the identified cause was a mismatch between the recipient address in the NF-e and the destination location address in Oracle. The postal code differed, and the other address details also needed to be checked.

## What to check first

Compare the address on the fiscal document with the registration for the establishment receiving the goods:

- Recipient CNPJ and the corresponding branch.
- Postal code, street, number, additional address details, district, city, and state.
- Delivery address in the NF-e XML, if present.
- Inventory organization and destination location associated with the Transfer Order.

Don't automatically treat the CNPJ's main address as the delivery address. Confirm that the branch and the address on its registration correspond to the delivery location in the NF-e and the destination location used by Oracle.

## How the mismatch affects troubleshooting

In a transfer flow, FDC must relate fiscal document lines to the source document to continue processing. Oracle's documentation explains that a Transfer Order can be the source document and that its information is used to identify the items and line details. The Transfer Orders REST API also exposes destination location and postal code attributes.

Oracle's public documentation doesn't state that postal code alone is the standard key used to derive the Transfer Order number and line. Treat the address mismatch as the observed cause in this scenario. If derivation still fails after correcting the address, also review the exception details and the source mapping in Collaboration Messaging.

## Correct the location in Oracle

Navigate to:

~~~text
Setup and Maintenance
> Manufacturing and Supply Chain Materials Management
> Setup
> Enterprise Profile
> Show: All Tasks
> Manage Locations
~~~

Search for the location associated with the Transfer Order's destination organization. Confirm the code, effective dates, and that it represents the correct receiving address. Update the address and postal code based on the validated branch/delivery address.

A location represents a physical address and can be associated with inventory organizations. The **Manage Locations** task maintains fields such as address, city, state, and postal code. See [Create Locations — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fammi/create-locations.html) and [Update existing setup data — Oracle Applications](https://docs.oracle.com/en/cloud/saas/applications-common/26b/oafsm/update-existing-setup-data.html).

## Review and reprocess in FDC

1. Open the **Fiscal Document Capture** work area.
2. In the task panel, select **Manage Interface Exceptions**.
3. Open the document and review the exception details. Confirm whether the registered location/address is the recorded cause.
4. After correcting the setup, run **Import and Validate Electronic Fiscal Documents** from **Scheduled Processes**. To process documents still in the interface, set **Fiscal Documents to Validate = New**. Use **All** when you also need to validate documents already created in FDC.
5. Return to FDC and confirm whether the source document and line were derived. Then monitor validation and receipt creation.

Oracle describes **Manage Interface Exceptions** as the page for reviewing discrepancies and validation/import errors, which can be resolved automatically or through manual intervention. See [Interface Exceptions — Oracle FDC](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/fafdc/interface-exceptions.html). The import and validation process is documented at [Import and Validate Electronic Fiscal Documents — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faspc/import-and-validate-electronic-fiscal-documents.html). Receipt creation depends on completing fiscal validation, as described in [Inbound Shipments for Brazil — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/famli/inbound-shipments-for-brazil.html).

## If derivation still fails

After confirming the address and reprocessing, also validate:

- Whether the received XML contains the correct recipient and delivery location details.
- Whether the Transfer Order and line are active and match the NF-e item and quantity.
- Whether the number and line are sent in the fields expected by FDC and by the configured Collaboration Messaging XSL/message definition.
- Whether the XML uses `xPed` and `nItemPed` in a way supported by the configured mapping. For a `nItemPed` length-limit case, see [Oracle Cloud: preserving the full nItemPed identifier in internal transfers](/en/oracle/fdc-nitemped-infadprod-transfer-order/).

The [Fiscal Document Capture overview](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fafdc/overview-of-fiscal-document-capture.html) describes the Transfer Order as a possible source document. To review Transfer Order attributes, including destination location and postal code, see the [Transfer Orders REST API — Oracle SCM](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fasrp/op-transferorders-get.html).

## References

- [Oracle — Interface Exceptions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/fafdc/interface-exceptions.html)
- [Oracle — Overview of Fiscal Document Capture](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fafdc/overview-of-fiscal-document-capture.html)
- [Oracle — Create Locations](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fammi/create-locations.html)
- [Oracle — Import and Validate Electronic Fiscal Documents](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faspc/import-and-validate-electronic-fiscal-documents.html)
- [Oracle — Inbound Shipments for Brazil](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/famli/inbound-shipments-for-brazil.html)
