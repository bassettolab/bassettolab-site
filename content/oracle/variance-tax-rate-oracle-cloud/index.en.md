---
title: "Oracle Cloud: Tax Rate Variance (TRV) in FDC and Its Impact on Item Cost"
date: 2026-09-30
article_id: "002"
description: "How tax differences between FDC, Receipt Accounting, and Payables can generate Tax Rate Variance and reach Cost Accounting as a cost adjustment."
tags:
  - Oracle Cloud
  - Brazil Localization
  - FDC
  - Tax
  - Payables
  - Receipt Accounting
  - Cost Accounting
  - TRV
categories:
  - Oracle
toc: true
type: post
featured: true
draft: false
---

Brazilian fiscal complexity creates scenarios in Oracle Cloud where Tax, Payables, Receipt Accounting, and Cost Accounting need to be closely aligned.

One of them is Tax Rate Variance (TRV).

In Fiscal Document Capture (FDC), taxes from the fiscal document approved by the tax authority are treated as the reference for accounting and reporting. At the same time, Oracle Tax also calculates taxes according to the tax configuration and compares the result with the values received in the document. After FDC validation, the captured taxes are carried to the Receipt and the Payables Invoice. [Oracle — Capturing Fiscal Documents of Purchase Orders](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-capturing-fiscal-documents-of-purchase-orders.html)

This design works well when both tax references produce compatible results. The problem appears when there is a difference between the fiscal-document tax and the tax calculated by Oracle.

Summary flow:

~~~text
NF-e XML > FDC > Receipt Accounting > Payables > TRV > Cost Accounting > Item Cost
~~~

## How TRV is generated

For receipt-matched invoices, Oracle calculates Tax Rate Variance when there is a difference between the non-recoverable tax amount recorded in the Receipt Accounting Distribution and the non-recoverable amount on the Payables Invoice. [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)

This difference can be related, for example, to:

~~~text
Tax Rate
Tax Recovery Rate
Tax Determinants
~~~

For this reason, TRV should normally be analyzed as the consequence of a calculation difference rather than only as an isolated Costing issue.

In an FDC scenario, we can have:

~~~text
Tax approved in the NF-e
        >
Captured by FDC
        >
Carried to Receipt / AP

Oracle Tax
        >
Calculates according to Tax Setup
        >
Different result

Difference > TRV
~~~

If the Tax Engine isn't configured to adequately reproduce the taxes applicable to the fiscal document, the two values can diverge. The FDC documentation itself states that when calculated taxes are incorrect, the tax setup should be corrected. [Oracle — Capturing Fiscal Documents of Purchase Orders](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-capturing-fiscal-documents-of-purchase-orders.html)

## Why TRV can change item cost

The impact doesn't end in Payables.

Oracle Cost Management treats differences imported from Payables, including Tax Rate Variance, as potential acquisition cost adjustments used to true up inventory cost. [Oracle — Exclude Invoice Cost Variances from Cost Management](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faims/exclude-invoice-cost-variances-from-cost-management.html)

The documentation also shows that when Cost Accounting distributions are created, accounted TRV can be treated as an adjustment to item cost. [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)

The final effect depends on the cost method, but the conceptual flow is:

~~~text
Payables
   >
Tax Rate Variance
   >
Cost Accounting
   >
Acquisition Cost Adjustment
   >
Item Cost / Inventory Value
~~~

This matters because a difference that starts as a fiscal issue can also affect inventory, margin, and cost accounting.

## Configurations that should be reviewed

For fiscal documents with receipt-based tax treatment, Oracle documents the following Receipt Tax Options combination:

| Configuration | Value |
| --- | --- |
| Allow Delivery-Based Tax Calculation | Yes |
| Report Delivery-Based Taxes | Receipt |
| Tax Point Basis | Delivery |
| Purchase Order Invoice Match Option | Receipt |

With this design, taxes from the fiscal document are distributed across the received quantity during Receipt Accounting. [Oracle — Define Receipt Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/define-receipt-tax-options.html)

Another important parameter is available in Configuration Owner Tax Options:

~~~text
Allow supplier tax variance calculation
~~~

Oracle defines this option as the control that calculates differences in tax amounts between an invoice and a purchase order. [Oracle — Configuration Owner Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26a/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)

This doesn't mean that simply disabling the option is automatically the solution for every FDC + Receipt Matching scenario. The behavior must be validated end to end because such a change can also affect legitimate variances.

## Alternative 1: align Oracle Tax Engine

The structural solution is to make the Oracle Tax calculation compatible with the correct tax on the fiscal document.

~~~text
Fiscal Document Tax = Oracle Tax Calculation
                    >
            No undesired difference
                    >
              No undesired TRV
~~~

This approach addresses the source of the difference.

On the other hand, in Brazilian implementations it can require maintaining enough regimes, taxes, rates, recovery rules, and determinants to correctly reproduce the required fiscal treatment.

## Alternative 2: review supplier tax variance

A configuration alternative is to evaluate the behavior of:

~~~text
Allow supplier tax variance calculation
~~~

Because this control is associated with the configuration owner and event class, it can offer a more targeted scope than a global Cost Management setting. [Oracle — Configuration Owner Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26a/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)

However, this option should be treated as a test candidate, not as a guaranteed solution.

The E2E should prove at least:

~~~text
Correct FDC Tax
Correct Receipt Accounting
Correct AP Tax
Undesired TRV eliminated
Correct accounting
Legitimate variances preserved
~~~

## Alternative 3: prevent TRV from changing cost

Another possible approach is to allow the variance to remain visible in Payables while preventing it from being incorporated into item cost through the Costing design.

Conceptually:

~~~text
Payables > TRV
            >
      remains visible
            >
Cost Accounting
            >
doesn't incorporate TRV into Item Cost
~~~

This type of approach protects cost but addresses the effect rather than the cause.

If a legitimate TRV should later be part of acquisition cost, it may also stop being absorbed. For this reason, any change to Cost Mapping or cost components should be validated by Costing and Accounting.

## Alternative 4: ignore invoice variances in Cost Management

Oracle provides the profile:

~~~text
ORA_CMR_IGNORE_AP_INV_VAR_ALL
Ignore Invoice Variances for Inventory Destination Purchase Orders
~~~

When configured as Yes, invoice variances covered by the profile aren't considered for inventory valuation true-up or Purchase Price Variance. [Oracle — Exclude Invoice Cost Variances from Cost Management](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faims/exclude-invoice-cost-variances-from-cost-management.html)

The key point is its scope: this profile is configured at the Site level and applies broadly across Costing and Inventory organizations. [Oracle — Manage Receipt Accounting Profile Options](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/faims/manage-receipt-accounting-profile-options.html)

It is therefore not a TRV-specific or single-location control.

Before using it, you need to evaluate the impact on other invoice variances that should still participate in cost.

## Process sequencing

Process sequencing also deserves attention.

For receipt-matched invoices, Oracle documents the dependency on Receipt Accounting Distributions for correct invoice processing. [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)

A typical operational flow involves:

~~~text
Receipt
   >
Receipt Accounting Distributions
   >
Payables Invoice
   >
Invoice Accounting
   >
Transfer Costs to Cost Management
   >
Cost Accounting Distributions
~~~

Controlling sequence can reduce timing issues, but it shouldn't be used to hide a real difference between fiscal tax and Oracle calculation.

In continuous, high-volume environments, relying exclusively on a perfect operational window can also be difficult to sustain.

## How to test it correctly

Before changing Tax, Payables, or Costing, the best approach is to build a reproducible E2E scenario.

For the same transaction, capture:

~~~text
1. Tax in XML / FDC
2. Recoverable and Non-Recoverable Tax in Receipt Accounting
3. AP Invoice Tax
4. TRV amount
5. Payables accounting
6. Receipt Accounting Distributions
7. Cost Accounting Distributions
8. Item Cost before and after
~~~

Then repeat the test while changing only one configuration at a time.

It is also important to test a scenario where legitimate TRV should exist. Otherwise, a solution may eliminate the original problem while also eliminating a required variance.

## The key point

The most important point is to separate cause and effect:

~~~text
Fiscal Document Tax
        ≠
Oracle Tax Calculation
        >
Tax Difference
        >
TRV
        >
Acquisition Cost Adjustment
        >
Item Cost
~~~

Removing TRV from Costing can prevent cost from changing.

Disabling a variance control can prevent a certain difference from being generated.

But neither alternative, by itself, guarantees that the original fiscal divergence no longer exists.

For this reason, the analysis should start by comparing the tax received by FDC with the tax calculated by Oracle Tax and then following the value through Receipt Accounting, Payables, and Cost Accounting.

## Official references

- [Oracle — Capturing Fiscal Documents of Purchase Orders](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-capturing-fiscal-documents-of-purchase-orders.html)
- [Oracle — Define Receipt Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/define-receipt-tax-options.html)
- [Oracle — Configuration Owner Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26a/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)
- [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)
- [Oracle — Accounting for Tax on Payables Transactions](https://docs.oracle.com/en/cloud/saas/financials/25d/fautx/accounting-for-tax-on-payables-transactions.html)
- [Oracle — Exclude Invoice Cost Variances from Cost Management](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faims/exclude-invoice-cost-variances-from-cost-management.html)
