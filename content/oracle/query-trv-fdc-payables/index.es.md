---
title: "Oracle Cloud: query para identificar Tax Rate Variance (TRV) originada en FDC"
date: 2026-10-01
article_id: "005"
description: "Una query de auditoría para localizar invoices de Payables originadas en FDC que generaron contabilización de Tax Rate Variance, incluyendo FDC, PO, cuenta, importe y estado."
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

Este artículo complementa [Oracle Cloud: Tax Rate Variance (TRV) en FDC y su impacto en el costo del artículo](/es/oracle/variance-tax-rate-oracle-cloud/).

Después de entender cómo puede generarse el TRV, la necesidad práctica es identificar qué invoices de Payables produjeron realmente una línea contable clasificada como Tax Rate Variance.

El modelo de BI Publisher utiliza tres parámetros:

~~~text
Business Unit
Fecha inicial
Fecha final
~~~

y devuelve, cuando esté disponible:

~~~text
Invoice
FDC
Purchase Order
Importe total de la invoice
Importe total del FDC
Importe contabilizado como TRV
Cuenta contable
Estado de Payables
~~~

Oracle documenta ACCOUNTING_CLASS_CODE en XLA_AE_LINES como la clasificación de una línea de Subledger Accounting, y TRV se utiliza para Tax Rate Variance. [Oracle — XLA_AE_LINES](https://docs.oracle.com/en/cloud/saas/financials/25d/oedmf/xlaaelines-17865.html) [Oracle — Event Cost Source Type](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fabsm/enum_oraScmCoreReceiptAcctgReviewDistribution_EventCostSourceType.html)

## Restricción para invoices de FDC

En el escenario analizado, las invoices creadas por Fiscal Document Capture llegan a Payables con:

~~~text
SOURCE = ORA_CMF
~~~

Por eso la query aplica explícitamente:

~~~sql
AND ai.source = 'ORA_CMF'
~~~

Esto evita mezclar invoices creadas por otras fuentes de Payables.

Oracle documenta SOURCE como el feeder system de la invoice. En el flujo CMF, CMF_AP_INVOICES_GT también expone una columna SOURCE. [Oracle — CMF_AP_INVOICES_GT](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/oedsc/cmfapinvoicesgt-10390.html)

## Query

~~~sql
WITH bu AS
(
    SELECT bu_id,
           bu_name
      FROM fun_all_business_units_v
     WHERE bu_name = :P_BU_NAME
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
fdc_info AS
(
    SELECT invoice_id,
           LISTAGG(document_number, ', ')
             WITHIN GROUP (ORDER BY document_number) fdc_number,
           LISTAGG(access_key_number, ', ')
             WITHIN GROUP (ORDER BY access_key_number) fdc_access_key,
           SUM(total_amount) fdc_total_amount
      FROM cmf_fiscal_doc_headers
     WHERE invoice_id IS NOT NULL
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

Todas las fechas mostradas en el resultado se formatean como `DD/MM/RRRR` con `TO_CHAR`. Los parámetros de BI Publisher siguen siendo de tipo Date.

## Parámetros de BI Publisher

~~~text
P_BU_NAME
P_DATE_FROM
P_DATE_TO
~~~

LOV de Business Unit:

~~~sql
SELECT bu_name display_value,
       bu_name return_value
  FROM fun_all_business_units_v
 WHERE status = 'A'
 ORDER BY bu_name
~~~

## Cómo se encuentra la invoice

AP_INVOICE_DISTRIBUTIONS_ALL.ACCOUNTING_EVENT_ID identifica el evento contable que contabilizó la distribución de la invoice. [Oracle — AP_INVOICE_DISTRIBUTIONS_ALL](https://docs.oracle.com/en/cloud/saas/financials/26b/oedmf/apinvoicedistributionsall-29565.html)

La query relaciona:

~~~sql
aid.accounting_event_id = trv.event_id
~~~

y conserva únicamente las líneas de SLA donde:

~~~sql
xal.accounting_class_code = 'TRV'
~~~

Así el informe no depende de una cuenta fija.

## Relación con FDC

CMF_FISCAL_DOC_HEADERS contiene el INVOICE_ID de Payables, además de DOCUMENT_NUMBER, ACCESS_KEY_NUMBER y TOTAL_AMOUNT. [Oracle — CMF_FISCAL_DOC_HEADERS](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26a/oedsc/cmffiscaldocheaders-16080.html)

La relación FDC → Payables puede hacerse directamente por:

~~~sql
fdc.invoice_id = ai.invoice_id
~~~

## Purchase Order

Cuando existe PO, AP_INVOICE_LINES_ALL.PO_HEADER_ID puede relacionarse con PO_HEADERS_ALL.PO_HEADER_ID. Oracle documenta esa foreign key, y SEGMENT1 representa el número del documento de compra. [Oracle — AP_INVOICE_LINES_ALL](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/apinvoicelinesall-16239.html) [Oracle — PO_HEADERS_ALL](https://docs.oracle.com/en/cloud/saas/procurement/26a/oedmp/poheadersall-4361.html)

Se utiliza LISTAGG porque una invoice puede contener líneas relacionadas con más de un PO.

## Estado de Payables

Además de AP_INVOICES_UTILITY_PKG.GET_APPROVAL_STATUS, devuelto como AP_STATUS, la salida mantiene WFAPPROVAL_STATUS, PAYMENT_STATUS_FLAG, SLA_STATUS y GL_TRANSFER_STATUS.

## Importe y cuenta del TRV

El importe contabilizado es:

~~~sql
NVL(accounted_dr, 0) - NVL(accounted_cr, 0)
~~~

XLA_AE_LINES contiene la combinación contable y los importes contabilizados de débito/crédito utilizados por SLA. [Oracle — XLA_AE_LINES](https://docs.oracle.com/en/cloud/saas/financials/25d/oedmf/xlaaelines-17865.html)

El ejemplo de ACCOUNT_COMBINATION considera siete segmentos del Chart of Accounts y puede ajustarse si se utiliza otra estructura.

## Resultado esperado

El informe responde:

~~~text
¿Qué invoices originadas en FDC
generaron Tax Rate Variance
para una BU y un período determinados?
~~~

La principal ventaja es identificar primero la naturaleza contable de la línea y después mostrar la cuenta derivada por SLA.
