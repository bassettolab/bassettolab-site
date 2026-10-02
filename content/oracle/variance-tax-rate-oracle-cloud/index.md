---
title: "Oracle Cloud: Tax Rate Variance (TRV) no FDC e o impacto no custo do item"
date: 2026-09-30
article_id: "002"
description: "Como diferenças de imposto entre FDC, Receipt Accounting e Payables podem gerar Tax Rate Variance e chegar ao Cost Accounting como ajuste de custo."
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
area: "TI"
platform: "Oracle"
product: "Cloud"
module: "FDC"
toc: true
type: post
featured: true
draft: false
---

A complexidade fiscal brasileira cria alguns cenários no Oracle Cloud em que Tax, Payables, Receipt Accounting e Cost Accounting precisam estar muito bem alinhados.

Um deles é o Tax Rate Variance (TRV).

No Fiscal Document Capture (FDC), os impostos do documento fiscal aprovado pela autoridade fiscal são tratados como referência para contabilização e reporting. Ao mesmo tempo, o Oracle Tax também calcula os impostos conforme a configuração fiscal e compara o resultado com os valores recebidos no documento. Após a validação do FDC, os impostos capturados são levados ao Receipt e à Payables Invoice. [Oracle — Capturing Fiscal Documents of Purchase Orders](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-capturing-fiscal-documents-of-purchase-orders.html)

Esse desenho funciona bem quando as duas referências produzem resultados compatíveis. O problema aparece quando existe uma diferença entre o imposto do documento fiscal e o imposto calculado pelo Oracle.

Fluxo resumido:

~~~text
NF-e XML > FDC > Receipt Accounting > Payables > TRV > Cost Accounting > Item Cost
~~~

## Como nasce o TRV

Para invoices com matching por Receipt, o Oracle calcula Tax Rate Variance quando existe diferença entre a parcela de imposto não recuperável registrada na Receipt Accounting Distribution e a parcela não recuperável da Payables Invoice. [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)

Essa diferença pode estar relacionada, por exemplo, a:

~~~text
Tax Rate
Tax Recovery Rate
Tax Determinants
~~~

Por isso, o TRV normalmente deve ser analisado como consequência de uma diferença de cálculo, e não apenas como um problema isolado de Costing.

Em um cenário de FDC, podemos ter:

~~~text
Imposto aprovado na NF-e
        >
Capturado pelo FDC
        >
Levado ao Receipt / AP

Oracle Tax
        >
Calcula conforme o Tax Setup
        >
Resultado diferente

Diferença > TRV
~~~

Se o Tax Engine não estiver configurado para reproduzir adequadamente os impostos aplicáveis ao documento fiscal, os dois valores podem divergir. A própria documentação do FDC orienta que, quando o imposto calculado estiver incorreto, o tax setup deve ser corrigido. [Oracle — Capturing Fiscal Documents of Purchase Orders](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-capturing-fiscal-documents-of-purchase-orders.html)

## Por que o TRV pode alterar o custo do item

O impacto não termina no Payables.

O Oracle Cost Management trata diferenças importadas do Payables, incluindo Tax Rate Variance, como possíveis acquisition cost adjustments usados no true-up do custo do inventário. [Oracle — Exclude Invoice Cost Variances from Cost Management](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faims/exclude-invoice-cost-variances-from-cost-management.html)

A documentação também mostra que, ao criar Cost Accounting distributions, um TRV contabilizado pode ser tratado como ajuste do custo do item. [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)

O efeito final depende do método de custo utilizado, mas o fluxo conceitual é:

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

Isso é importante porque uma diferença originalmente fiscal pode passar a afetar também estoque, margem e contabilização de custos.

## Configurações que precisam ser verificadas

Para fiscal documents com tratamento de imposto no recebimento, a Oracle documenta a seguinte combinação de Receipt Tax Options:

| Configuração | Valor |
| --- | --- |
| Allow Delivery-Based Tax Calculation | Yes |
| Report Delivery-Based Taxes | Receipt |
| Tax Point Basis | Delivery |
| Purchase Order Invoice Match Option | Receipt |

Nesse desenho, os impostos do fiscal document são distribuídos sobre a quantidade recebida durante o Receipt Accounting. [Oracle — Define Receipt Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/define-receipt-tax-options.html)

Outro parâmetro importante fica em Configuration Owner Tax Options:

~~~text
Allow supplier tax variance calculation
~~~

A Oracle define essa opção como o controle que calcula diferenças nos valores de imposto entre uma invoice e uma purchase order. [Oracle — Configuration Owner Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26a/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)

Isso não significa que simplesmente desabilitar a opção seja automaticamente a solução para todo cenário FDC + Receipt Matching. O comportamento precisa ser validado ponta a ponta, porque uma mudança desse tipo também pode afetar variações legítimas.

## Alternativa 1: alinhar o Oracle Tax Engine

A solução estrutural é fazer com que o cálculo do Oracle Tax seja compatível com o imposto correto do documento fiscal.

~~~text
Fiscal Document Tax = Oracle Tax Calculation
                    >
            Sem divergência indevida
                    >
              Sem TRV indevido
~~~

Esse caminho atua na origem da diferença.

Por outro lado, em implementações brasileiras isso pode exigir manutenção de regimes, taxes, rates, recovery rules e determinantes suficientes para reproduzir corretamente o tratamento fiscal necessário.

## Alternativa 2: revisar o supplier tax variance

Uma alternativa de configuração é avaliar o comportamento de:

~~~text
Allow supplier tax variance calculation
~~~

Como esse controle está associado ao configuration owner e ao event class, ele pode oferecer um escopo mais direcionado do que uma configuração global de Cost Management. [Oracle — Configuration Owner Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26a/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)

Mas essa opção deve ser tratada como candidata a teste, não como solução garantida.

O E2E precisa comprovar pelo menos:

~~~text
FDC Tax correto
Receipt Accounting correto
AP Tax correto
TRV indevido eliminado
Contabilização correta
Variações legítimas preservadas
~~~

## Alternativa 3: impedir que o TRV altere o custo

Outra abordagem possível é permitir que a variância continue visível no Payables, mas impedir que ela seja incorporada ao item cost por meio do desenho de Costing.

Conceitualmente:

~~~text
Payables > TRV
            >
      permanece visível
            >
Cost Accounting
            >
não incorpora o TRV ao Item Cost
~~~

Esse tipo de abordagem protege o custo, mas trata o efeito e não a causa.

Se futuramente existir um TRV legítimo que devesse compor o acquisition cost, ele também pode deixar de ser absorvido. Por isso, qualquer alteração de Cost Mapping ou cost component deve passar por validação de Costing e Contabilidade.

## Alternativa 4: ignorar invoice variances no Cost Management

O Oracle possui o profile:

~~~text
ORA_CMR_IGNORE_AP_INV_VAR_ALL
Ignore Invoice Variances for Inventory Destination Purchase Orders
~~~

Quando configurado como Yes, as invoice variances cobertas pelo profile não são consideradas no true-up da valorização do inventário ou Purchase Price Variance. [Oracle — Exclude Invoice Cost Variances from Cost Management](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faims/exclude-invoice-cost-variances-from-cost-management.html)

O ponto crítico é o escopo: esse profile é configurado em nível Site e se aplica de forma ampla às organizações de Costing e Inventory. [Oracle — Manage Receipt Accounting Profile Options](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/faims/manage-receipt-accounting-profile-options.html)

Por isso, ele não é um controle específico de TRV ou de uma única localização.

Antes de utilizá-lo, é necessário avaliar o impacto sobre outras invoice variances que ainda deveriam participar do custo.

## Sequenciamento dos processos

O sequenciamento dos processos também merece atenção.

Em receipt-matched invoices, a Oracle documenta a dependência das Receipt Accounting Distributions para o processamento correto da invoice. [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)

Um fluxo operacional típico envolve:

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

Controlar o sequenciamento pode reduzir problemas de timing, mas não deve ser usado para esconder uma divergência real entre o imposto fiscal e o cálculo Oracle.

Em ambientes com processamento contínuo e alto volume, depender exclusivamente de uma janela operacional perfeita também pode ser difícil de sustentar.

## Como testar corretamente

Antes de modificar Tax, Payables ou Costing, o ideal é criar um cenário E2E reproduzível.

Para a mesma transação, registre:

~~~text
1. Imposto no XML / FDC
2. Recoverable e Non-Recoverable Tax no Receipt Accounting
3. Imposto da AP Invoice
4. Valor do TRV
5. Accounting do Payables
6. Receipt Accounting Distributions
7. Cost Accounting Distributions
8. Item Cost antes e depois
~~~

Depois repita o teste alterando apenas uma configuração por vez.

Também é importante testar um cenário em que um TRV legítimo deveria existir. Caso contrário, uma solução pode eliminar o problema original e, ao mesmo tempo, eliminar uma variância necessária.

## O ponto principal

O ponto mais importante é separar causa e efeito:

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

Remover o TRV do Costing pode impedir que o custo seja alterado.

Desabilitar um controle de variância pode impedir que determinada diferença seja criada.

Mas nenhuma dessas alternativas, isoladamente, garante que a divergência fiscal original deixou de existir.

Por isso, a análise deve começar comparando o imposto recebido pelo FDC com o imposto calculado pelo Oracle Tax e seguir o valor até Receipt Accounting, Payables e Cost Accounting.

## Referências oficiais

- [Oracle — Capturing Fiscal Documents of Purchase Orders](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-capturing-fiscal-documents-of-purchase-orders.html)
- [Oracle — Define Receipt Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/define-receipt-tax-options.html)
- [Oracle — Configuration Owner Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26a/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)
- [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)
- [Oracle — Accounting for Tax on Payables Transactions](https://docs.oracle.com/en/cloud/saas/financials/25d/fautx/accounting-for-tax-on-payables-transactions.html)
- [Oracle — Exclude Invoice Cost Variances from Cost Management](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faims/exclude-invoice-cost-variances-from-cost-management.html)
