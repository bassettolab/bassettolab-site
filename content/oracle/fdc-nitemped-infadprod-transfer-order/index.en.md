---
title: "Oracle Cloud: Working Around the nItemPed Limit in Internal Transfers"
date: 2026-09-30
description: "An alternative for identifying internal transfer lines in FDC when the NF-e nItemPed field cannot hold the complete line identifier."
tags:
  - Oracle Cloud
  - Brazil Localization
  - FDG
  - FDC
  - NF-e
  - Collaboration Messaging
categories:
  - Oracle
toc: true
type: post
featured: true
draft: false
---

# Oracle Cloud: Working Around the nItemPed Limit in Internal Transfers

I want to share a technical scenario that can appear in Oracle Cloud internal-transfer implementations.

In a transfer between units, Oracle can generate the NF-e through FDG and send it to a fiscal partner, which handles the communication with SEFAZ. After authorization, the XML returns to Oracle and is processed by FDC.

## The issue

For FDC to relate the received document to the correct transfer, we normally need to identify the shipment and its corresponding line.

In the NF-e XML, one possible approach is to use `xPed` for the Shipment Number and `nItemPed` for the line identifier.

The limitation is that `nItemPed` accepts only 6 digits. When the Oracle line identifier is already larger than that, the complete value cannot be carried in this field.

Truncating the identifier is also not a good option, because different lines may eventually produce the same shortened value.

## The alternative

The alternative was to use `infAdProd` to carry the complete line identifier.

In FDG, the identifier can be exposed at line level through `LEGAL_MESSAGE_TEXT`. From there, the fiscal partner can map it to `infAdProd` in the NF-e XML.

When the XML returns, Collaboration Messaging is adjusted so that, for the applicable operations, `SourceDocumentLine` is populated from `infAdProd` instead of `nItemPed`.

The message definition used for inbound NF-e processing can be accessed through:

```text
Tools
  → Collaboration Messaging
    → Manage Collaboration Message Definitions
```

The rule can be restricted to the required CFOPs while preserving the standard `nItemPed` behavior for all other documents.

## Result

With this approach, the complete line identifier can travel through the NF-e outbound and inbound process without depending on the 6-digit limitation of `nItemPed`.

It is important to remember that `infAdProd` is a fiscal field in the NF-e. This type of use should therefore be validated with the fiscal team and the fiscal integration partner.

It is also preferable to avoid changing seeded Collaboration Messaging definitions directly and to keep the customization separate whenever possible.

## Public references

- Oracle Fusion Cloud — Fiscal Document Capture  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — Collaboration Messaging Framework  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — ZX_LINES_DET_FACTORS  
  https://docs.oracle.com/en/cloud/saas/financials/

- Brazil NF-e Portal  
  https://www.nfe.fazenda.gov.br/
