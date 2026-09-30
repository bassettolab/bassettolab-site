---
title: "Oracle Cloud: contornando o limite do nItemPed em transferências internas"
date: 2026-09-30
description: "Uma solução prática para relacionar linhas de transferências internas no FDC quando o nItemPed da NF-e não comporta o identificador completo."
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

# Oracle Cloud: contornando o limite do nItemPed em transferências internas

Quero compartilhar um cenário técnico que pode aparecer em implementações de transferência interna no Oracle Cloud e uma alternativa de desenho para tratá-lo.

O cenário é relativamente comum: uma mercadoria sai de uma unidade e vai para outra. Dependendo da operação, essa movimentação precisa de uma NF-e.

Em uma arquitetura com parceiro fiscal, o Oracle pode gerar o documento pelo FDG, enviar os dados para o parceiro fiscal, o parceiro transmitir para a SEFAZ e, depois da autorização, disponibilizar o XML da NF-e.

Na chegada da mercadoria, o fluxo volta para o Oracle: o XML é recebido, transformado pelo Collaboration Messaging e processado pelo FDC.

![Fluxo geral da transferência interna com NF-e](flow-general.svg)

## Onde aparece a limitação

Para o FDC identificar corretamente a transferência, é necessário relacionar a NF-e ao shipment e à linha correspondente.

Um desenho possível é usar:

```xml
<xPed>Shipment Number</xPed>
<nItemPed>Shipment Line Identifier</nItemPed>
```

A dificuldade aparece quando o identificador técnico da linha é maior que o tamanho suportado pelo `nItemPed`.

No leiaute da NF-e, esse campo aceita até 6 dígitos. Em implementações onde o identificador técnico já ultrapassou esse tamanho, o valor completo deixa de caber no campo.

Truncar o número não é uma boa alternativa, porque identificadores diferentes podem acabar produzindo o mesmo valor reduzido.

A pergunta passa a ser: onde transportar o identificador completo?

![Limitação do nItemPed e alternativa com infAdProd](nitemped-infadprod.svg)

## Uma alternativa: infAdProd

Uma opção é usar a tag:

```xml
<infAdProd>
```

Esse campo comporta uma informação maior e pode transportar o identificador completo da linha.

O desenho fica assim:

```text
xPed
  → Shipment Number

nItemPed
  → permanece dentro da limitação do leiaute

infAdProd
  → identificador completo da linha do shipment
```

Isso é uma decisão de implementação. Não significa que a SEFAZ ou a Oracle definam o `infAdProd` especificamente para transportar um identificador técnico. O uso deve ser validado com a equipe fiscal e com o parceiro fiscal.

## Primeiro passo: levar a informação até o XML

No FDG existe o conceito de `LEGAL_MESSAGE_TEXT` em nível de linha.

Em algumas versões ou desenhos de automação, pode ser necessário complementar o Data Model para preencher esse atributo automaticamente na geração do documento.

Uma lógica genérica para `TRANSFER ORDER SHIPMENT` pode buscar o identificador da linha em `ZX_LINES_DET_FACTORS`:

```sql
CASE
    WHEN H.EVENT_CLASS_CODE = 'TRANSFER ORDER SHIPMENT'
    THEN TO_CHAR(
           (
             SELECT NVL(LINK_TO_TRX_LINE_ID, TRX_LINE_ID)
               FROM ZX_LINES_DET_FACTORS
              WHERE TRX_ID           = L.TRX_ID
                AND TRX_LINE_ID      = L.TRX_LINE_ID
                AND APPLICATION_ID   = L.APPLICATION_ID
                AND ENTITY_CODE      = L.ENTITY_CODE
                AND EVENT_CLASS_CODE = L.EVENT_CLASS_CODE
           )
         )
    ELSE L1E_1.LEGAL_MESSAGE_TEXT
END AS LEGAL_MESSAGE_TEXT
```

Assim, para esse tipo de transferência, o identificador completo pode ser disponibilizado para o parceiro fiscal.

O parceiro fiscal pode então mapear o valor para:

```xml
<infAdProd>...</infAdProd>
```

## Segundo passo: fazer o FDC ler infAdProd

Depois que a NF-e é autorizada e o XML retorna para o Oracle, é necessário ajustar o mapeamento de entrada para que, nos casos desejados, o identificador da linha seja lido de `infAdProd` em vez de `nItemPed`.

No Oracle Cloud, o caminho é:

```text
Tools
  → Collaboration Messaging
    → Manage Collaboration Message Definitions
```

A definição utilizada no processamento da NF-e aponta para um XSL responsável pela transformação da mensagem.

O comportamento padrão pode ser semelhante a:

```xml
<n9:SourceDocumentLine>
    <xsl:value-of select="ns3:prod/ns3:nItemPed"/>
</n9:SourceDocumentLine>
```

Para operações específicas, o XSL pode direcionar a leitura para `infAdProd`.

Exemplo genérico:

```xml
<n9:SourceDocumentLine>
    <xsl:choose>

        <xsl:when test="
            (ns3:prod/ns3:CFOP = 6151 or
             ns3:prod/ns3:CFOP = 5151 or
             ns3:prod/ns3:CFOP = 6557 or
             ns3:prod/ns3:CFOP = 5557)
             and normalize-space(ns3:infAdProd) != ''">

            <xsl:value-of select="ns3:infAdProd"/>

        </xsl:when>

        <xsl:otherwise>
            <xsl:value-of select="ns3:prod/ns3:nItemPed"/>
        </xsl:otherwise>

    </xsl:choose>
</n9:SourceDocumentLine>
```

Os CFOPs acima são apenas um exemplo técnico de como estruturar a condição. Cada implementação deve validar quais códigos realmente pertencem ao seu cenário fiscal.

Com isso, somente as operações explicitamente tratadas passam a usar `infAdProd`. Os demais documentos continuam seguindo o comportamento original com `nItemPed`.

## Fluxo final

De forma genérica:

```text
Shipment
   │
   ├── Shipment Number
   │        ↓
   │       xPed
   │
   └── Line Identifier
            ↓
     LEGAL_MESSAGE_TEXT
            ↓
       Parceiro Fiscal
            ↓
         infAdProd
            ↓
          SEFAZ
            ↓
     XML autorizado
            ↓
 Collaboration Messaging
            ↓
   SourceDocumentLine
            ↓
           FDC
            ↓
         Receipt
```

![Fluxo técnico da solução](flow-technical.svg)

## Alguns cuidados

Evite alterar diretamente uma definição seeded do Collaboration Messaging. O mais seguro é trabalhar com uma definição customizada e manter o XSL padrão como referência.

Também vale limitar a regra somente às operações necessárias e manter um `otherwise` usando `nItemPed`. Isso reduz o risco de impactar outras entradas de NF-e.

Antes de colocar a mudança em produção, valide o XML autorizado e confirme que o `infAdProd` está chegando exatamente com o identificador esperado.

Por fim, `infAdProd` é um campo fiscal da NF-e. Neste cenário ele é usado como parte de uma solução técnica para contornar uma limitação de tamanho do `nItemPed`, então a validação fiscal continua sendo necessária.

## Referências públicas

- Oracle Fusion Cloud — Fiscal Document Capture
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — Collaboration Messaging Framework
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — ZX_LINES_DET_FACTORS
  https://docs.oracle.com/en/cloud/saas/financials/

- Portal Nacional da NF-e
  https://www.nfe.fazenda.gov.br/
