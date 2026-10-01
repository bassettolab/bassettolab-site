---
title: "Oracle Cloud: query to identify Tax Rate Variance (TRV) originating from FDC"
date: 2026-10-01
article_id: "005"
description: "An audit query to find Payables invoices originating from FDC that generated Tax Rate Variance accounting, including FDC, PO, account, amount, and status."
tags:
  - Oracle Cloud
  - Brazil Localization
  - FDC
  - Payables
  - SLA
  - TRV
  - SQL
categories:
  - Oracle
toc: true
type: post
featured: true
draft: false
---

This article complements [Oracle Cloud: Tax Rate Variance (TRV) in FDC and Its Impact on Item Cost](/en/oracle/variance-tax-rate-oracle-cloud/).

After understanding how TRV can be generated, the practical need is to identify which Payables invoices actually produced an accounting line classified as Tax Rate Variance.

The BI Publisher model uses four parameters:

~~~text
Business Unit
Ledger
Start date
End date
~~~

and returns, whenever available:

~~~text
Invoice
FDC
Purchase Order
Invoice total
FDC total
TRV accounted amount
Accounting combination
Payables status
~~~

Oracle documents ACCOUNTING_CLASS_CODE in XLA_AE_LINES as the classification of a Subledger Accounting line, and TRV is used for Tax Rate Variance. [Oracle — XLA_AE_LINES](https://docs.oracle.com/en/cloud/saas/financials/25d/oedmf/xlaaelines-17865.html) [Oracle — Event Cost Source Type](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fabsm/enum_oraScmCoreReceiptAcctgReviewDistribution_EventCostSourceType.html)

## Restricting the query to FDC invoices

In the scenario analyzed, invoices created by Fiscal Document Capture reach Payables with:

~~~text
SOURCE = ORA_CMF
~~~

The query therefore explicitly applies:

~~~sql
AND ai.source = 'ORA_CMF'
~~~

This prevents invoices created by other Payables sources from being mixed into the same report.

Oracle documents SOURCE as the feeder system for the invoice. In the CMF flow, CMF_AP_INVOICES_GT also exposes a SOURCE column. [Oracle — CMF_AP_INVOICES_GT](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/oedsc/cmfapinvoicesgt-10390.html)

## Query

~~~sql
WITH bu AS
(
    SELECT bu_id,
           bu_name,
           primary_ledger_id
      FROM fun_all_business_units_v
     WHERE bu_name = :P_BU_NAME
),
ledger AS
(
    SELECT DISTINCT
           gl.ledger_id,
           gl.name ledger_name
      FROM gl_ledgers gl
      JOIN
           (
               SELECT primary_ledger_id ledger_id
                 FROM bu

               UNION

               SELECT glr.target_ledger_id ledger_id
                 FROM gl_ledger_relationships glr
                 JOIN bu
                   ON bu.primary_ledger_id = glr.primary_ledger_id
           ) bu_ledgers
        ON bu_ledgers.ledger_id = gl.ledger_id
     WHERE gl.name = :P_LEDGER_NAME
),
po_base AS
(
    SELECT DISTINCT
           ail.invoice_id,
           poh.segment1 po_number
      FROM ap_invoice_lines_all ail
      JOIN po_headers_all poh
        ON poh.po_header_id = ail.po_header_id
     WHERE ail.po_header_id IS NOT NULL
),
po_info AS
(
    SELECT invoice_id,
           LISTAGG(po_number, ', ')
             WITHIN GROUP (ORDER BY po_number) po_number
      FROM po_base
     GROUP BY invoice_id
),
fdc_base AS
(
    /* Preferred relationship when the FDC header already stores the AP invoice. */
    SELECT DISTINCT
           fdh.invoice_id,
           fdh.document_header_id,
           fdh.document_number,
           fdh.access_key_number,
           fdh.total_amount
      FROM cmf_fiscal_doc_headers fdh
     WHERE fdh.invoice_id IS NOT NULL

    UNION

    /* Fallback through the source transaction carried to AP invoice lines. */
    SELECT DISTINCT
           ail.invoice_id,
           fdh.document_header_id,
           fdh.document_number,
           fdh.access_key_number,
           fdh.total_amount
      FROM ap_invoice_lines_all ail
      JOIN cmf_fiscal_doc_headers fdh
        ON fdh.document_header_id = ail.source_trx_id
     WHERE ail.source_trx_id IS NOT NULL
),
fdc_info AS
(
    SELECT invoice_id,
           LISTAGG(document_number, ', ')
             WITHIN GROUP (ORDER BY document_number) fdc_number,
           LISTAGG(access_key_number, ', ')
             WITHIN GROUP (ORDER BY access_key_number) fdc_access_key,
           SUM(total_amount) fdc_total_amount
      FROM fdc_base
     GROUP BY invoice_id
),
trv_accounting AS
(
    SELECT xah.event_id,
           xah.accounting_date,
           xah.period_name,
           xah.accounting_entry_status_code,
           xah.gl_transfer_status_code,
           xal.ae_line_num,
           xal.code_combination_id,
           xal.accounting_class_code,
           xal.accounted_dr,
           xal.accounted_cr
      FROM xla_ae_headers xah
      JOIN ledger
        ON ledger.ledger_id = xah.ledger_id
      JOIN xla_ae_lines xal
        ON xal.application_id = xah.application_id
       AND xal.ae_header_id   = xah.ae_header_id
     WHERE xah.application_id = 200
       AND xal.accounting_class_code = 'TRV'
       AND xah.accounting_date >= :P_DATE_FROM
       AND xah.accounting_date <  :P_DATE_TO + 1
)
SELECT TO_CHAR(trv.accounting_date, 'DD/MM/RRRR') accounting_date,
       trv.period_name,
       ai.invoice_num,
       TO_CHAR(ai.invoice_date, 'DD/MM/RRRR') invoice_date,
       ai.invoice_currency_code currency,
       ai.invoice_amount ap_invoice_amount,
       ap_invoices_utility_pkg.get_approval_status
       (
           ai.invoice_id,
           ai.invoice_amount,
           ai.payment_status_flag,
           ai.invoice_type_lookup_code
       ) ap_status,
       ai.wfapproval_status ap_workflow_status,
       ai.payment_status_flag ap_payment_status,
       po.po_number,
       fdc.fdc_number,
       fdc.fdc_access_key,
       fdc.fdc_total_amount,
       NVL(trv.accounted_dr, 0)
         - NVL(trv.accounted_cr, 0) trv_amount,
       gcc.segment1 || '.' ||
       gcc.segment2 || '.' ||
       gcc.segment3 || '.' ||
       gcc.segment4 || '.' ||
       gcc.segment5 || '.' ||
       gcc.segment6 || '.' ||
       gcc.segment7 account_combination,
       trv.accounting_entry_status_code sla_status,
       trv.gl_transfer_status_code gl_transfer_status
  FROM trv_accounting trv
  JOIN ap_invoices_all ai
    ON EXISTS
       (
           SELECT 1
             FROM ap_invoice_distributions_all aid
            WHERE aid.invoice_id = ai.invoice_id
              AND aid.accounting_event_id = trv.event_id
       )
  JOIN bu
    ON bu.bu_id = ai.org_id
  JOIN gl_code_combinations gcc
    ON gcc.code_combination_id = trv.code_combination_id
  LEFT JOIN po_info po
    ON po.invoice_id = ai.invoice_id
  LEFT JOIN fdc_info fdc
    ON fdc.invoice_id = ai.invoice_id
 WHERE ai.source = 'ORA_CMF'
 ORDER BY trv.accounting_date,
          ai.invoice_num,
          trv.ae_line_num
~~~

All dates displayed in the result are formatted as `DD/MM/RRRR` with `TO_CHAR`. The BI Publisher parameters remain Date parameters.

## BI Publisher parameters

~~~text
P_BU_NAME
P_LEDGER_NAME
P_DATE_FROM
P_DATE_TO
~~~

Business Unit LOV:

~~~sql
SELECT bu_name display_value,
       bu_name return_value
  FROM fun_all_business_units_v
 WHERE status = 'A'
 ORDER BY bu_name
~~~

For `P_LEDGER_NAME`, use a LOV dependent on the Business Unit. After selecting the BU, the user can choose among its related ledgers, for example a **Local** or **Global** ledger:

~~~sql
SELECT DISTINCT
       gl.name display_value,
       gl.name return_value
  FROM gl_ledgers gl
  JOIN
       (
           SELECT fbu.primary_ledger_id ledger_id
             FROM fun_all_business_units_v fbu
            WHERE fbu.bu_name = :P_BU_NAME

           UNION

           SELECT glr.target_ledger_id ledger_id
             FROM fun_all_business_units_v fbu
             JOIN gl_ledger_relationships glr
               ON glr.primary_ledger_id = fbu.primary_ledger_id
            WHERE fbu.bu_name = :P_BU_NAME
       ) bu_ledgers
    ON bu_ledgers.ledger_id = gl.ledger_id
 ORDER BY gl.name
~~~

The Business Unit exposes `PRIMARY_LEDGER_ID`, while `GL_LEDGER_RELATIONSHIPS` stores the relationships between primary, secondary, and reporting ledgers. The selected value is then used to filter `XLA_AE_HEADERS.LEDGER_ID`. [Oracle — FUN_ALL_BUSINESS_UNITS_V](https://docs.oracle.com/en/cloud/saas/financials/26b/oedmf/funallbusinessunitsv-5106.html) [Oracle — GL_LEDGER_RELATIONSHIPS](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/glledgerrelationships-6344.html) [Oracle — XLA_AE_HEADERS](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/xlaaeheaders-7221.html)

## How the invoice is found

AP_INVOICE_DISTRIBUTIONS_ALL.ACCOUNTING_EVENT_ID identifies the accounting event that accounted for the invoice distribution. [Oracle — AP_INVOICE_DISTRIBUTIONS_ALL](https://docs.oracle.com/en/cloud/saas/financials/26b/oedmf/apinvoicedistributionsall-29565.html)

The query relates:

~~~sql
aid.accounting_event_id = trv.event_id
~~~

and keeps only SLA lines where:

~~~sql
xal.accounting_class_code = 'TRV'
~~~

This avoids depending on a fixed account.

## FDC relationship

CMF_FISCAL_DOC_HEADERS contains the Payables INVOICE_ID plus DOCUMENT_NUMBER, ACCESS_KEY_NUMBER, and TOTAL_AMOUNT. [Oracle — CMF_FISCAL_DOC_HEADERS](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26a/oedsc/cmffiscaldocheaders-16080.html)

The simplest relationship uses the `INVOICE_ID` stored on the FDC header. However, that column is nullable and may not be populated for every record. The query therefore uses two paths: the FDC `INVOICE_ID` and, as a fallback, `AP_INVOICE_LINES_ALL.SOURCE_TRX_ID` related to the FDC `DOCUMENT_HEADER_ID`.

This prevents losing the fiscal document number, access key, and total amount when the direct invoice link isn't available.

## Purchase Order

When a PO exists, AP_INVOICE_LINES_ALL.PO_HEADER_ID can be related to PO_HEADERS_ALL.PO_HEADER_ID. Oracle documents that foreign key, and SEGMENT1 represents the purchase document number. [Oracle — AP_INVOICE_LINES_ALL](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/apinvoicelinesall-16239.html) [Oracle — PO_HEADERS_ALL](https://docs.oracle.com/en/cloud/saas/procurement/26a/oedmp/poheadersall-4361.html)

LISTAGG is used because a single invoice may contain lines associated with more than one PO.

## Payables status

Besides AP_INVOICES_UTILITY_PKG.GET_APPROVAL_STATUS, returned as AP_STATUS, the output keeps WFAPPROVAL_STATUS, PAYMENT_STATUS_FLAG, SLA_STATUS, and GL_TRANSFER_STATUS.

## TRV amount and account

The accounted value is:

~~~sql
NVL(accounted_dr, 0) - NVL(accounted_cr, 0)
~~~

XLA_AE_LINES contains the code combination and accounted debit/credit amounts used by SLA. [Oracle — XLA_AE_LINES](https://docs.oracle.com/en/cloud/saas/financials/25d/oedmf/xlaaelines-17865.html)

The ACCOUNT_COMBINATION example assumes seven Chart of Accounts segments and can be adjusted when another structure is used.

## Expected result

The report answers:

~~~text
Which FDC-originated invoices
generated Tax Rate Variance
for a specific BU and date range?
~~~

The main benefit is that it identifies the accounting nature of the line first and only then shows the account derived by SLA.
