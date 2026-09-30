---
title: "Oracle Cloud: Tax Rate Variance (TRV) en FDC y su impacto en el costo del artículo"
date: 2026-09-30
article_id: "002"
description: "Cómo las diferencias de impuestos entre FDC, Receipt Accounting y Payables pueden generar Tax Rate Variance y llegar a Cost Accounting como un ajuste de costo."
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

La complejidad fiscal brasileña crea algunos escenarios en Oracle Cloud en los que Tax, Payables, Receipt Accounting y Cost Accounting deben estar muy bien alineados.

Uno de ellos es Tax Rate Variance (TRV).

En Fiscal Document Capture (FDC), los impuestos del documento fiscal aprobado por la autoridad fiscal se tratan como referencia para contabilización y reporting. Al mismo tiempo, Oracle Tax también calcula los impuestos de acuerdo con la configuración fiscal y compara el resultado con los valores recibidos en el documento. Después de la validación de FDC, los impuestos capturados se llevan al Receipt y a la Payables Invoice. [Oracle — Capturing Fiscal Documents of Purchase Orders](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-capturing-fiscal-documents-of-purchase-orders.html)

Este diseño funciona bien cuando ambas referencias de impuestos producen resultados compatibles. El problema aparece cuando existe una diferencia entre el impuesto del documento fiscal y el impuesto calculado por Oracle.

Flujo resumido:

~~~text
NF-e XML > FDC > Receipt Accounting > Payables > TRV > Cost Accounting > Item Cost
~~~

## Cómo se genera el TRV

Para invoices con matching por Receipt, Oracle calcula Tax Rate Variance cuando existe una diferencia entre la parte de impuesto no recuperable registrada en la Receipt Accounting Distribution y la parte no recuperable de la Payables Invoice. [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)

Esta diferencia puede estar relacionada, por ejemplo, con:

~~~text
Tax Rate
Tax Recovery Rate
Tax Determinants
~~~

Por eso, TRV normalmente debe analizarse como consecuencia de una diferencia de cálculo y no solamente como un problema aislado de Costing.

En un escenario de FDC, podemos tener:

~~~text
Impuesto aprobado en la NF-e
        >
Capturado por FDC
        >
Llevado al Receipt / AP

Oracle Tax
        >
Calcula según el Tax Setup
        >
Resultado diferente

Diferencia > TRV
~~~

Si Tax Engine no está configurado para reproducir adecuadamente los impuestos aplicables al documento fiscal, los dos valores pueden divergir. La propia documentación de FDC indica que, cuando los impuestos calculados son incorrectos, debe corregirse el tax setup. [Oracle — Capturing Fiscal Documents of Purchase Orders](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-capturing-fiscal-documents-of-purchase-orders.html)

## Por qué el TRV puede cambiar el costo del artículo

El impacto no termina en Payables.

Oracle Cost Management trata las diferencias importadas desde Payables, incluyendo Tax Rate Variance, como posibles acquisition cost adjustments utilizados para hacer el true-up del costo del inventario. [Oracle — Exclude Invoice Cost Variances from Cost Management](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faims/exclude-invoice-cost-variances-from-cost-management.html)

La documentación también muestra que, al crear Cost Accounting distributions, un TRV contabilizado puede tratarse como un ajuste del costo del artículo. [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)

El efecto final depende del método de costo utilizado, pero el flujo conceptual es:

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

Esto es importante porque una diferencia que comienza como un asunto fiscal puede afectar también inventario, margen y contabilización de costos.

## Configuraciones que deben revisarse

Para fiscal documents con tratamiento del impuesto en el receipt, Oracle documenta la siguiente combinación de Receipt Tax Options:

| Configuración | Valor |
| --- | --- |
| Allow Delivery-Based Tax Calculation | Yes |
| Report Delivery-Based Taxes | Receipt |
| Tax Point Basis | Delivery |
| Purchase Order Invoice Match Option | Receipt |

Con este diseño, los impuestos del fiscal document se distribuyen sobre la cantidad recibida durante Receipt Accounting. [Oracle — Define Receipt Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/define-receipt-tax-options.html)

Otro parámetro importante está disponible en Configuration Owner Tax Options:

~~~text
Allow supplier tax variance calculation
~~~

Oracle define esta opción como el control que calcula diferencias en los importes de impuesto entre una invoice y una purchase order. [Oracle — Configuration Owner Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26a/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)

Esto no significa que simplemente deshabilitar la opción sea automáticamente la solución para todos los escenarios FDC + Receipt Matching. El comportamiento debe validarse de extremo a extremo porque un cambio de este tipo también puede afectar variaciones legítimas.

## Alternativa 1: alinear Oracle Tax Engine

La solución estructural es hacer que el cálculo de Oracle Tax sea compatible con el impuesto correcto del documento fiscal.

~~~text
Fiscal Document Tax = Oracle Tax Calculation
                    >
          Sin diferencia no deseada
                    >
              Sin TRV indebido
~~~

Este enfoque actúa sobre el origen de la diferencia.

Por otro lado, en implementaciones brasileñas puede requerir mantener suficientes regimes, taxes, rates, recovery rules y determinantes para reproducir correctamente el tratamiento fiscal requerido.

## Alternativa 2: revisar supplier tax variance

Una alternativa de configuración es evaluar el comportamiento de:

~~~text
Allow supplier tax variance calculation
~~~

Como este control está asociado al configuration owner y al event class, puede ofrecer un alcance más dirigido que una configuración global de Cost Management. [Oracle — Configuration Owner Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26a/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)

Sin embargo, esta opción debe tratarse como candidata para pruebas y no como una solución garantizada.

El E2E debe demostrar al menos:

~~~text
FDC Tax correcto
Receipt Accounting correcto
AP Tax correcto
TRV indebido eliminado
Contabilización correcta
Variaciones legítimas preservadas
~~~

## Alternativa 3: impedir que el TRV cambie el costo

Otro enfoque posible es permitir que la variancia continúe visible en Payables, pero impedir que sea incorporada al item cost mediante el diseño de Costing.

Conceptualmente:

~~~text
Payables > TRV
            >
      permanece visible
            >
Cost Accounting
            >
no incorpora TRV al Item Cost
~~~

Este tipo de enfoque protege el costo, pero trata el efecto y no la causa.

Si en el futuro existe un TRV legítimo que deba formar parte del acquisition cost, también puede dejar de ser absorbido. Por eso, cualquier cambio en Cost Mapping o cost components debe ser validado por Costing y Contabilidad.

## Alternativa 4: ignorar invoice variances en Cost Management

Oracle dispone del profile:

~~~text
ORA_CMR_IGNORE_AP_INV_VAR_ALL
Ignore Invoice Variances for Inventory Destination Purchase Orders
~~~

Cuando se configura como Yes, las invoice variances cubiertas por el profile no se consideran para el true-up de la valorización del inventario o Purchase Price Variance. [Oracle — Exclude Invoice Cost Variances from Cost Management](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faims/exclude-invoice-cost-variances-from-cost-management.html)

El punto crítico es su alcance: este profile se configura a nivel Site y se aplica ampliamente a las organizaciones de Costing e Inventory. [Oracle — Manage Receipt Accounting Profile Options](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/faims/manage-receipt-accounting-profile-options.html)

Por lo tanto, no es un control específico de TRV ni de una única localización.

Antes de utilizarlo, es necesario evaluar el impacto sobre otras invoice variances que aún deberían participar en el costo.

## Secuencia de los procesos

La secuencia de los procesos también merece atención.

Para receipt-matched invoices, Oracle documenta la dependencia de las Receipt Accounting Distributions para el procesamiento correcto de la invoice. [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)

Un flujo operativo típico incluye:

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

Controlar la secuencia puede reducir problemas de timing, pero no debe utilizarse para ocultar una divergencia real entre el impuesto fiscal y el cálculo Oracle.

En ambientes con procesamiento continuo y alto volumen, depender exclusivamente de una ventana operativa perfecta también puede ser difícil de sostener.

## Cómo probarlo correctamente

Antes de modificar Tax, Payables o Costing, lo ideal es crear un escenario E2E reproducible.

Para la misma transacción, registre:

~~~text
1. Impuesto en XML / FDC
2. Recoverable y Non-Recoverable Tax en Receipt Accounting
3. Impuesto de la AP Invoice
4. Valor del TRV
5. Accounting de Payables
6. Receipt Accounting Distributions
7. Cost Accounting Distributions
8. Item Cost antes y después
~~~

Después repita la prueba cambiando solamente una configuración cada vez.

También es importante probar un escenario en el que un TRV legítimo deba existir. De lo contrario, una solución puede eliminar el problema original y al mismo tiempo eliminar una variancia necesaria.

## El punto principal

El punto más importante es separar causa y efecto:

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

Eliminar TRV de Costing puede impedir que el costo sea modificado.

Deshabilitar un control de variancia puede impedir que se genere una determinada diferencia.

Pero ninguna de esas alternativas, por sí sola, garantiza que la divergencia fiscal original haya dejado de existir.

Por eso, el análisis debe comenzar comparando el impuesto recibido por FDC con el impuesto calculado por Oracle Tax y seguir el valor hasta Receipt Accounting, Payables y Cost Accounting.

## Referencias oficiales

- [Oracle — Capturing Fiscal Documents of Purchase Orders](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/overview-of-capturing-fiscal-documents-of-purchase-orders.html)
- [Oracle — Define Receipt Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/define-receipt-tax-options.html)
- [Oracle — Configuration Owner Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26a/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)
- [Oracle — Transactional Flow with Case Study](https://docs.oracle.com/en/cloud/saas/financials/25d/fauap/transactional-flow-with-case-study.html)
- [Oracle — Accounting for Tax on Payables Transactions](https://docs.oracle.com/en/cloud/saas/financials/25d/fautx/accounting-for-tax-on-payables-transactions.html)
- [Oracle — Exclude Invoice Cost Variances from Cost Management](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faims/exclude-invoice-cost-variances-from-cost-management.html)
