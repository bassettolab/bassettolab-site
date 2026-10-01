---
title: "Oracle Cloud: query para identificar Tax Rate Variance (TRV) originada no FDC"
date: 2026-10-01
article_id: "005"
description: "Uma query de auditoria para localizar invoices do Payables originadas no FDC que geraram contabilização de Tax Rate Variance, incluindo FDC, PO, conta, valor e status."
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

Este artigo complementa [Oracle Cloud: Tax Rate Variance (TRV) no FDC e o impacto no custo do item](/oracle/variance-tax-rate-oracle-cloud/).

Depois de entender como o TRV pode ser gerado, a necessidade prática passa a ser localizar quais invoices do Payables realmente produziram uma linha contábil classificada como Tax Rate Variance.

A proposta é utilizar três parâmetros no BI Publisher:

~~~text
Business Unit
Data inicial
Data final
~~~

e retornar, sempre que possível:

~~~text
Invoice
FDC
Purchase Order
Valor total da invoice
Valor total do FDC
Valor contabilizado como TRV
Conta contábil
Status do Payables
Status do FDC
~~~

A Oracle documenta ACCOUNTING_CLASS_CODE em XLA_AE_LINES como a classificação da linha do Subledger Accounting, e o código TRV é utilizado para Tax Rate Variance. [Oracle — XLA_AE_LINES](https://docs.oracle.com/en/cloud/saas/financials/25d/oedmf/xlaaelines-17865.html) [Oracle — Event Cost Source Type](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/fabsm/enum_oraScmCoreReceiptAcctgReviewDistribution_EventCostSourceType.html)

## Somente invoices originadas no FDC

No cenário analisado, as invoices criadas pelo Fiscal Document Capture chegam ao Payables com:

~~~text
SOURCE = ORA_CMF
~~~

Por isso a query restringe explicitamente:

~~~sql
AND ai.source = 'ORA_CMF'
~~~

Isso evita misturar no mesmo relatório transações criadas por outras origens do Payables.

A Oracle documenta SOURCE como o feeder system da invoice. No fluxo CMF, a tabela de staging CMF_AP_INVOICES_GT também possui a coluna SOURCE. [Oracle — CMF_AP_INVOICES_GT](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/oedsc/cmfapinvoicesgt-10390.html)

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
           SUM(total_amount) fdc_total_amount,
           MAX(document_status) fdc_document_status,
           MAX(validation_status) fdc_validation_status
      FROM cmf_fiscal_doc_headers
     WHERE invoice_id IS NOT NULL
     GROUP BY invoice_id
),
trv_accounting AS
(
    SELECT xah.ae_header_id,
           xah.event_id,
           xah.accounting_date,
           xah.period_name,
           xah.accounting_entry_status_code,
           xah.gl_transfer_status_code,
           xal.ae_line_num,
           xal.code_combination_id,
           xal.accounting_class_code,
           xal.entered_dr,
           xal.entered_cr,
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
SELECT bu.bu_name business_unit,
       trv.accounting_date,
       trv.period_name,
       ai.invoice_num,
       ai.invoice_date,
       ai.invoice_currency_code,
       ai.invoice_amount ap_invoice_amount,
       ai.source ap_source,
       ap_invoices_utility_pkg.get_approval_status
       (
           ai.invoice_id,
           ai.invoice_amount,
           ai.payment_status_flag,
           ai.invoice_type_lookup_code
       ) ap_validation_status,
       ai.wfapproval_status ap_workflow_status,
       ai.payment_status_flag ap_payment_status,
       po.po_number,
       fdc.fdc_number,
       fdc.fdc_access_key,
       fdc.fdc_total_amount,
       fdc.fdc_document_status,
       fdc.fdc_validation_status,
       trv.accounting_class_code,
       NVL(trv.accounted_dr, 0)
         - NVL(trv.accounted_cr, 0) trv_accounted_amount,
       NVL(trv.entered_dr, 0)
         - NVL(trv.entered_cr, 0) trv_entered_amount,
       trv.code_combination_id,
       gcc.segment1 || '.' ||
       gcc.segment2 || '.' ||
       gcc.segment3 || '.' ||
       gcc.segment4 || '.' ||
       gcc.segment5 || '.' ||
       gcc.segment6 || '.' ||
       gcc.segment7 account_combination,
       trv.accounting_entry_status_code sla_status,
       trv.gl_transfer_status_code gl_transfer_status,
       trv.ae_header_id,
       trv.ae_line_num,
       trv.event_id,
       ai.invoice_id
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

## Parâmetros do BI Publisher

~~~text
P_BU_NAME
P_DATE_FROM
P_DATE_TO
~~~

Para a LOV da Business Unit:

~~~sql
SELECT bu_name display_value,
       bu_name return_value
  FROM fun_all_business_units_v
 WHERE status = 'A'
 ORDER BY bu_name
~~~

## Como a invoice é encontrada

A ligação entre Payables e SLA é feita pelo evento contábil.

AP_INVOICE_DISTRIBUTIONS_ALL.ACCOUNTING_EVENT_ID identifica o accounting event que contabilizou a distribuição da invoice. [Oracle — AP_INVOICE_DISTRIBUTIONS_ALL](https://docs.oracle.com/en/cloud/saas/financials/26b/oedmf/apinvoicedistributionsall-29565.html)

A query relaciona:

~~~sql
aid.accounting_event_id = trv.event_id
~~~

e seleciona somente as linhas em que:

~~~sql
xal.accounting_class_code = 'TRV'
~~~

Com isso, o relatório não depende de uma conta contábil fixa. A regra de SLA pode mudar a conta e a transação continuará sendo identificada pela sua classe contábil.

## Relação com o FDC

CMF_FISCAL_DOC_HEADERS possui o INVOICE_ID da invoice criada no Payables e também informações úteis para auditoria:

~~~text
DOCUMENT_NUMBER
ACCESS_KEY_NUMBER
TOTAL_AMOUNT
DOCUMENT_STATUS
VALIDATION_STATUS
~~~

A Oracle documenta INVOICE_ID como o identificador da invoice relacionada ao Fiscal Document e TOTAL_AMOUNT como o valor total do documento fiscal. [Oracle — CMF_FISCAL_DOC_HEADERS](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26a/oedsc/cmffiscaldocheaders-16080.html)

Por isso a relação pode ser feita diretamente por:

~~~sql
fdc.invoice_id = ai.invoice_id
~~~

## Purchase Order

Quando existe PO associado à invoice, AP_INVOICE_LINES_ALL.PO_HEADER_ID pode ser relacionado a PO_HEADERS_ALL.PO_HEADER_ID. A Oracle documenta essa foreign key, e SEGMENT1 representa o número do documento de compra. [Oracle — AP_INVOICE_LINES_ALL](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/apinvoicelinesall-16239.html) [Oracle — PO_HEADERS_ALL](https://docs.oracle.com/en/cloud/saas/procurement/26a/oedmp/poheadersall-4361.html)

Como uma invoice pode conter linhas ligadas a mais de um PO, a query utiliza LISTAGG.

## Status do Payables

Além do status de validação retornado por AP_INVOICES_UTILITY_PKG.GET_APPROVAL_STATUS, a saída mantém:

~~~text
WFAPPROVAL_STATUS
PAYMENT_STATUS_FLAG
SLA_STATUS
GL_TRANSFER_STATUS
~~~

Assim é possível diferenciar validação, workflow, pagamento e contabilização.

## Valor e conta da TRV

O valor contabilizado é calculado a partir da própria linha de SLA:

~~~sql
NVL(accounted_dr, 0) - NVL(accounted_cr, 0)
~~~

Também é retornado o valor em moeda da transação:

~~~sql
NVL(entered_dr, 0) - NVL(entered_cr, 0)
~~~

XLA_AE_LINES contém o CODE_COMBINATION_ID e os valores de débito e crédito usados pelo SLA. [Oracle — XLA_AE_LINES](https://docs.oracle.com/en/cloud/saas/financials/25d/oedmf/xlaaelines-17865.html)

A concatenação de ACCOUNT_COMBINATION deste exemplo considera sete segmentos. Se o Chart of Accounts possuir outra estrutura, basta ajustar a concatenação.

## Resultado esperado

A pergunta que o relatório passa a responder é simples:

Quais invoices originadas no FDC geraram Tax Rate Variance para uma BU e período específicos?

A principal vantagem é identificar primeiro a natureza contábil da linha, TRV, e somente depois mostrar qual conta foi derivada pelo SLA. Isso mantém a consulta útil mesmo que a regra contábil seja alterada.
