---
title: "Variance Tax Rate en Oracle Cloud: cuando el impuesto del documento fiscal difiere de Oracle Tax"
date: 2026-09-21
description: "Caso de estudio sobre VTR entre FDC/XML, Receipt Accounting, Payables y Cost Accounting en una implementación brasileña."
tags:
  - Oracle Cloud
  - Receipt Accounting
  - Payables
  - Cost Accounting
  - Tax
  - Brazil
categories:
  - Oracle
toc: true
type: post
featured: true
draft: false
discussionURL: "https://github.com/bassettolab/bassettolab-site/issues/1"
---

# Variance Tax Rate en Oracle Cloud

En una implementación brasileña de Oracle Cloud encontramos un problema que, a primera vista, parecía solamente contable: Payables generaba una **Variance Tax Rate (VTR)** y, posteriormente, Receipt/Cost Accounting llevaba esa diferencia al costo del artículo.

El punto más importante del diagnóstico fue entender que la VTR no era el problema original. Era el **efecto contable de dos fuentes de impuestos que no estaban llegando a Oracle con el mismo valor**.

## El escenario

El flujo, de forma simplificada, era:

~~~text
NF-e / XML
    ↓
FDC
    ↓
Receipt / Receipt Accounting
    ↓
Payables
    ↓
Tax Variance
    ↓
Cost Accounting
~~~

El documento fiscal brasileño llegaba con los impuestos correctos en el XML y FDC capturaba esa información.

Al mismo tiempo, Oracle Tax Engine no reproducía completamente esos mismos impuestos. Como resultado, el valor fiscal recibido del documento y el valor utilizado por Oracle en determinados puntos del proceso eran diferentes.

Cuando la factura se conciliaba con la recepción, esa diferencia aparecía como VTR.

## ¿Qué es VTR?

De forma simple, VTR es una diferencia de impuestos identificada durante el matching de la factura.

Oracle documenta que la opción **Allow supplier tax variance calculation** calcula diferencias entre los importes de impuestos de la factura y de la orden de compra.

[Oracle — Configuration Owner Tax Options](https://docs.oracle.com/en/cloud/saas/financials/25d/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)

Por lo tanto, cuando dos etapas del proceso reconocen valores de impuestos diferentes, una variance puede ser una consecuencia esperada del diseño contable.

## ¿Por qué esto afectaba al costo?

El problema era más crítico porque no terminaba en Payables.

La diferencia podía continuar hacia Receipt Accounting y Cost Accounting como un ajuste. Para artículos de inventario, esto significa que una divergencia fiscal puede modificar el valor contabilizado en el costo del artículo.

Oracle explica que, dependiendo de la combinación de **Tax Point Basis** y **Tax Point Date**, las diferencias entre los impuestos estimados en la orden de compra y los impuestos finales de la factura pueden generar tax variance.

[Oracle — Tax Accounting for Receipt Transactions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/fapma/Chunk317596229.html)

En otras palabras:

~~~text
Impuesto esperado en el flujo de compras
                ≠
Impuesto reconocido en la factura
                ↓
          Tax Variance
                ↓
       posible impacto en el costo
~~~

## Un ejemplo simple

Imaginemos este escenario únicamente para ilustrar:

~~~text
Valor del material:      R$ 100.000
Impuesto del XML:        R$ 10.000
Impuesto considerado
por Oracle Tax:          R$ 0
~~~

Desde el punto de vista del documento fiscal, la obligación es de R$ 110.000.

Pero si una etapa de Oracle trabaja con R$ 100.000 y otra recibe R$ 110.000, el sistema necesita contabilizar la diferencia de R$ 10.000 en algún lugar.

Es en este tipo de conciliación donde aparece la tax variance.

## Las configuraciones que revisamos

En el caso analizado, el diseño estaba basado en la recepción:

~~~text
Allow Delivery-Based Tax Calculation = Yes
Report Delivery-Based Taxes on       = Receipt
Tax Point Date                        = Receipt date
Tax Point Basis                       = Delivery
PO Invoice Match Option               = Receipt
Accrue at Receipt                     = Yes
~~~

Esta combinación está alineada con el modelo documentado por Oracle para la contabilización de impuestos basada en la recepción.

Oracle describe específicamente que, cuando **Tax Point Basis = Delivery**, la recepción pasa a ser un evento relevante para el cálculo y la contabilización del impuesto.

[Oracle — Tax Point Basis](https://docs.oracle.com/en/cloud/saas/financials/25c/fautx/tax-point-basis.html)

También existe documentación específica sobre las opciones de impuestos en la recepción:

[Oracle — Define Receipt Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/define-receipt-tax-options.html)

## El detalle más importante: Receipt versus Invoice

Oracle documenta un comportamiento importante cuando la factura utiliza impuestos basados en delivery.

Si Receipt Accounting ya está completo y existe la línea de impuestos correspondiente, el impuesto puede prorratearse en la factura con base en la cantidad conciliada.

Si esa línea correspondiente no está disponible, el comportamiento cambia y el sistema puede utilizar otra información para tratar el impuesto.

Además, Oracle documenta que las diferencias entre los impuestos del receipt y de la invoice se registran mediante tax variance distributions.

Consulte la documentación:

[Oracle — Tax Calculation on Payables Transactions Using Tax Point Basis](https://docs.oracle.com/en/cloud/saas/financials/25d/fautx/tax-calculation-on-payables-transactions-using-tax-point-basis.html)

Este punto ayudó a separar dos aspectos:

1. Oracle estaba realizando una conciliación prevista por el producto;
2. el origen de la diferencia debía investigarse antes de esa conciliación.

## ¿Por qué cambiar solamente el orden de los jobs no resuelve la causa?

Una de las primeras hipótesis fue la secuencia de procesos.

Por ejemplo:

~~~text
Recepción
↓
Receipt Accounting
↓
Invoice Validation
↓
Payables Accounting
↓
Cost Accounting
~~~

La secuencia puede cambiar el momento en el que determinada información está disponible y debe probarse correctamente.

Pero no elimina una diferencia estructural.

Si al final continuamos con:

~~~text
XML/FDC Tax = X
Oracle Tax  = Y

X ≠ Y
~~~

el riesgo de variance continúa existiendo.

Por eso, tratar solamente la secuencia de los jobs puede reducir algunos síntomas, pero no necesariamente corrige el origen.

## Cómo realizamos el diagnóstico

El mejor método fue dejar de mirar solamente el asiento final y comparar el impuesto en cada etapa.

### 1. Documento fiscal

Primero, validar lo que realmente llegó en la NF-e/XML:

~~~text
Base imponible
Tasa
Valor del impuesto
Recuperable / no recuperable
~~~

### 2. FDC

Confirmar si FDC cargó los mismos valores del documento fiscal.

### 3. Receipt Accounting

Validar qué tax lines llegaron a la recepción y qué importes fueron contabilizados.

### 4. Payables

Comparar:

~~~text
Invoice Tax
PO/Receipt Tax
Tax Variance
~~~

### 5. Cost Accounting

Finalmente, verificar si la variance fue absorbida como ajuste de costo.

Este análisis de extremo a extremo evita intentar corregir Cost Accounting cuando la diferencia se originó mucho antes.

## Alternativas evaluadas

### 1. Hacer que Oracle Tax reproduzca el documento fiscal

Es la solución más estructural.

El objetivo es hacer que Oracle reconozca los impuestos de forma consistente con el documento fiscal recibido.

La ventaja es eliminar la diferencia en el origen.

La desventaja es que un Tax Engine brasileño completo exige configuración, gobernanza y mantenimiento.

### 2. Revisar el cálculo de supplier tax variance

La opción **Allow supplier tax variance calculation** controla el cálculo de diferencias de impuestos entre la factura y la orden de compra.

Debe analizarse en el alcance correcto de Configuration Owner y Event Class.

[Oracle — Configuration Owner Tax Options](https://docs.oracle.com/en/cloud/saas/financials/25d/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)

En nuestra prueba, cambiar de forma aislada una configuración no fue suficiente para eliminar el comportamiento. Esto mostró que el escenario debía ejecutarse nuevamente de extremo a extremo, verificando las tax lines producidas en cada etapa.

### 3. Evitar que la VTR modifique el costo

Otra posibilidad es revisar cómo se trata la variance en Cost Accounting.

Esto puede evitar que una diferencia fiscal modifique el costo del artículo, pero no elimina la diferencia existente en Payables.

Por eso debe tratarse con cuidado: neutralizar toda variance también puede ocultar una variance legítima.

### 4. Ajuste manual

También es posible detectar las ocurrencias y realizar ajustes posteriores.

Esta solución puede servir como contingencia, pero tiene una fragilidad importante:

~~~text
Recepción
↓
Costo incorrecto
↓
Pasa el tiempo
↓
Ajuste manual
~~~

Durante ese intervalo, el artículo puede ser consumido, vendido o incluso capitalizado con un costo que después será corregido.

Por lo tanto, el ajuste manual es una mitigación, no una solución estructural.

## Lo que aprendimos

La principal lección de este caso fue:

> No trate la VTR como la causa hasta demostrar que realmente lo es.

La VTR puede simplemente estar revelando que dos puntos diferentes del proceso están reconociendo impuestos distintos.

El diagnóstico correcto debe seguir todo el flujo:

~~~text
Documento fiscal
      ↓
FDC
      ↓
Oracle Tax
      ↓
Purchase Order / Receipt
      ↓
Receipt Accounting
      ↓
Payables
      ↓
Tax Variance
      ↓
Cost Accounting
~~~

Cuando existe una diferencia entre el documento fiscal y el modelo tributario mantenido en Oracle, es necesario definir claramente cuál sistema es la fuente del impuesto y cómo esa información debe atravesar todas las etapas de Procure-to-Pay.

Sin esa definición, la VTR es solamente el punto donde la inconsistencia finalmente se hace visible.

## Referencias oficiales de Oracle

- [Tax Point Basis](https://docs.oracle.com/en/cloud/saas/financials/25c/fautx/tax-point-basis.html)
- [Tax Calculation on Payables Transactions Using Tax Point Basis](https://docs.oracle.com/en/cloud/saas/financials/25d/fautx/tax-calculation-on-payables-transactions-using-tax-point-basis.html)
- [Define Receipt Tax Options](https://docs.oracle.com/en/cloud/saas/financials/26b/faufa/define-receipt-tax-options.html)
- [Configuration Owner Tax Options for Payables and Purchasing](https://docs.oracle.com/en/cloud/saas/financials/25d/faitx/how-you-set-up-configuration-owner-tax-options-for-payables-and.html)
- [Tax Accounting for Receipt Transactions](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/fapma/Chunk317596229.html)
- [Example of Tax Accounting for a Simple Procurement Transaction](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/fapma/example-of-tax-accounting-for-a-simple-procurement-transaction.html)

---

Este artículo describe un caso de estudio de implementación y troubleshooting. El comportamiento exacto puede variar según la configuración tributaria, la versión de Oracle Cloud, recoverability, matching y las reglas contables utilizadas.
