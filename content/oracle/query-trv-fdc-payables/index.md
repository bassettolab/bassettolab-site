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
area: "TI"
platform: "Oracle"
product: "Cloud"
module: "FDC"
toc: true
type: post
featured: true
draft: false
---

Este artigo complementa [Oracle Cloud: Tax Rate Variance (TRV) no FDC e o impacto no custo do item](/oracle/variance-tax-rate-oracle-cloud/).

Depois de entender como o TRV pode ser gerado, a necessidade prática passa a ser localizar quais invoices do Payables realmente produziram uma linha contábil classificada como Tax Rate Variance.

A proposta é utilizar quatro parâmetros no BI Publisher:

~~~text
Business Unit
Ledger
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
           bu_name,
           TO_NUMBER(primary_ledger_id) primary_ledger_id
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

Todas as datas exibidas no resultado são formatadas como `DD/MM/RRRR` com `TO_CHAR`. Os parâmetros continuam sendo do tipo Date no BI Publisher.

## Parâmetros do BI Publisher

~~~text
P_BU_NAME
P_LEDGER_NAME
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

Para o parâmetro `P_LEDGER_NAME`, eu usaria uma LOV dependente da Business Unit. Assim, depois de selecionar a BU, o usuário pode escolher entre os ledgers relacionados a ela — por exemplo, um ledger **Local** ou **Global**:

~~~sql
SELECT DISTINCT
       gl.name display_value,
       gl.name return_value
  FROM gl_ledgers gl
  JOIN
       (
           SELECT TO_NUMBER(fbu.primary_ledger_id) ledger_id
             FROM fun_all_business_units_v fbu
            WHERE fbu.bu_name = :P_BU_NAME

           UNION

           SELECT glr.target_ledger_id ledger_id
             FROM fun_all_business_units_v fbu
             JOIN gl_ledger_relationships glr
               ON glr.primary_ledger_id = TO_NUMBER(fbu.primary_ledger_id)
            WHERE fbu.bu_name = :P_BU_NAME
       ) bu_ledgers
    ON bu_ledgers.ledger_id = gl.ledger_id
 ORDER BY gl.name
~~~

A Business Unit expõe `PRIMARY_LEDGER_ID` por meio de `FUN_ALL_BUSINESS_UNITS_V`, mas nessa view o valor vem de `ORG_INFORMATION3`. Para evitar `ORA-01790` ao combinar esse valor com os IDs numéricos de `GL_LEDGER_RELATIONSHIPS`, a query converte explicitamente o campo com `TO_NUMBER(PRIMARY_LEDGER_ID)`. `GL_LEDGER_RELATIONSHIPS` mantém os relacionamentos entre o ledger primário e seus ledgers relacionados. A query usa o ledger escolhido para filtrar diretamente `XLA_AE_HEADERS.LEDGER_ID`. [Oracle — FUN_ALL_BUSINESS_UNITS_V](https://docs.oracle.com/en/cloud/saas/financials/26b/oedmf/funallbusinessunitsv-5106.html) [Oracle — GL_LEDGER_RELATIONSHIPS](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/glledgerrelationships-6344.html) [Oracle — XLA_AE_HEADERS](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/xlaaeheaders-7221.html)

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
~~~

A Oracle documenta INVOICE_ID como o identificador da invoice relacionada ao Fiscal Document e TOTAL_AMOUNT como o valor total do documento fiscal. [Oracle — CMF_FISCAL_DOC_HEADERS](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26a/oedsc/cmffiscaldocheaders-16080.html)

A relação mais simples é pelo `INVOICE_ID` armazenado no cabeçalho do FDC. Porém, esse campo é nullable e pode não estar preenchido em todos os registros. Por isso a query usa duas possibilidades: o `INVOICE_ID` do próprio FDC e, como fallback, o `SOURCE_TRX_ID` das linhas do Payables relacionado ao `DOCUMENT_HEADER_ID` do FDC.

Isso evita perder o número, a chave de acesso e o valor total do Fiscal Document quando o vínculo direto pelo `INVOICE_ID` não estiver disponível.

## Purchase Order

Quando existe PO associado à invoice, AP_INVOICE_LINES_ALL.PO_HEADER_ID pode ser relacionado a PO_HEADERS_ALL.PO_HEADER_ID. A Oracle documenta essa foreign key, e SEGMENT1 representa o número do documento de compra. [Oracle — AP_INVOICE_LINES_ALL](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/apinvoicelinesall-16239.html) [Oracle — PO_HEADERS_ALL](https://docs.oracle.com/en/cloud/saas/procurement/26a/oedmp/poheadersall-4361.html)

Como uma invoice pode conter linhas ligadas a mais de um PO, a query utiliza LISTAGG.

## Status do Payables

Além do status de validação retornado por AP_INVOICES_UTILITY_PKG.GET_APPROVAL_STATUS, retornado na coluna AP_STATUS, a saída mantém:

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

XLA_AE_LINES contém o CODE_COMBINATION_ID e os valores contabilizados de débito e crédito usados pelo SLA. [Oracle — XLA_AE_LINES](https://docs.oracle.com/en/cloud/saas/financials/25d/oedmf/xlaaelines-17865.html)

A concatenação de ACCOUNT_COMBINATION deste exemplo considera sete segmentos. Se o Chart of Accounts possuir outra estrutura, basta ajustar a concatenação.

## Resultado esperado

A pergunta que o relatório passa a responder é simples:

Quais invoices originadas no FDC geraram Tax Rate Variance para uma BU e período específicos?

A principal vantagem é identificar primeiro a natureza contábil da linha, TRV, e somente depois mostrar qual conta foi derivada pelo SLA. Isso mantém a consulta útil mesmo que a regra contábil seja alterada.
