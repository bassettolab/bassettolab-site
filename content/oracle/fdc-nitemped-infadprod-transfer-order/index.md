---
title: "Oracle Cloud Brasil: contornando o limite do nItemPed em transferências internas"
date: 2026-09-30
description: "Uma solução prática para relacionar linhas de transferências internas no FDC quando o nItemPed da NF-e não comporta o identificador completo do Oracle."
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

# Oracle Cloud Brasil: contornando o limite do nItemPed em transferências internas

Quero compartilhar um problema que apareceu em um fluxo de transferência interna no Oracle Cloud Brasil e a solução que encontramos.

O cenário é relativamente comum: uma mercadoria sai de uma empresa ou filial e vai para outra unidade. Dependendo da operação, essa movimentação precisa de uma NF-e.

No nosso fluxo, o Oracle gera o documento fiscal pelo FDG, envia as informações para o parceiro fiscal, o parceiro envia para a SEFAZ e, depois da autorização, temos o XML da NF-e.

Na chegada da mercadoria, o caminho acontece ao contrário: o parceiro fiscal envia o XML de volta para o Oracle, o Collaboration Messaging transforma a mensagem e o FDC recebe o documento.

De forma simplificada:

```text
Transfer Order
    ↓
Shipment
    ↓
FDG
    ↓
Parceiro Fiscal
    ↓
SEFAZ
    ↓
XML da NF-e
    ↓
Parceiro Fiscal
    ↓
Collaboration Messaging
    ↓
FDC
    ↓
Receipt
```

## Onde apareceu o problema

Para o FDC identificar corretamente a transferência, precisamos relacionar a NF-e com o shipment e com a linha correta.

No nosso desenho, usamos:

```xml
<xPed>Shipment Number</xPed>
<nItemPed>Shipment Line Identifier</nItemPed>
```

O problema está no `nItemPed`.

No leiaute da NF-e esse campo aceita apenas 6 dígitos. Só que o identificador que precisávamos enviar do Oracle, relacionado à linha do shipment, já estava com 8 dígitos e continua crescendo por ser sequencial.

Truncar o número não era uma boa opção. Em algum momento poderíamos ter colisão entre identificadores diferentes terminando com os mesmos seis dígitos.

Então a pergunta passou a ser: onde colocar o identificador completo?

## A alternativa: infAdProd

A solução foi usar a tag:

```xml
<infAdProd>
```

Esse campo comporta uma informação maior e pode ser usado para levar o identificador completo da linha.

O desenho ficou assim:

```text
xPed
  → Shipment Number

nItemPed
  → permanece dentro da limitação do leiaute

infAdProd
  → identificador completo da linha do shipment
```

Importante: isso é uma solução de implementação. Não significa que a SEFAZ ou a Oracle definam o `infAdProd` especificamente para transportar um identificador técnico do Oracle. O uso precisa ser alinhado com a equipe fiscal e com o parceiro fiscal.

## Primeiro passo: levar a informação do Oracle até o XML

No FDG existe o conceito de `LEGAL_MESSAGE_TEXT` em nível de linha.

O ponto que encontramos foi que o fluxo de FDG Automation utilizado não disponibilizava esse campo no Data Model da automação da forma que precisávamos.

Esse comportamento foi levado para o Oracle Support. O caso resultou no Enhancement Request:

```text
40078092 - FDG_AUTOMATION INCLUDE LEGAL MESSAGE TEXT TREATMENT
```

Enquanto isso, precisávamos de uma solução prática.

Para `TRANSFER ORDER SHIPMENT`, passamos a preencher o `LEGAL_MESSAGE_TEXT` com o identificador da linha usando `ZX_LINES_DET_FACTORS`.

A lógica ficou semelhante a esta:

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

Assim, para transferências internas, conseguimos levar o identificador completo até o parceiro fiscal.

O parceiro fiscal então faz o mapeamento desse valor para:

```xml
<infAdProd>...</infAdProd>
```

## Segundo passo: fazer o FDC ler infAdProd

Depois que a NF-e é autorizada e o XML retorna para o Oracle, precisamos dizer ao FDC que, para esses casos, o identificador da linha não deve vir do `nItemPed`, mas do `infAdProd`.

É aqui que entra o Collaboration Messaging.

No Oracle Cloud, o caminho é:

```text
Tools
  → Collaboration Messaging
    → Manage Collaboration Message Definitions
```

Depois, buscamos a definição usada para processar a NF-e de entrada.

No nosso ambiente, a definição estava associada a um XSL semelhante a:

```text
SEFAZ-procNFe-3_10-To-CMF-ProcessFiscalDoc.xsl
```

O comportamento padrão era basicamente:

```xml
<n9:SourceDocumentLine>
    <xsl:value-of select="ns3:prod/ns3:nItemPed"/>
</n9:SourceDocumentLine>
```

A alteração foi fazer com que alguns CFOPs de transferência passassem a buscar o valor de `infAdProd`.

Exemplo simplificado:

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

Com isso, somente os CFOPs definidos para esse cenário usam o `infAdProd`. Os demais documentos continuam seguindo o comportamento original com `nItemPed`.

## Fluxo final

No fim, ficou assim:

```text
Oracle Shipment
      │
      ├── Shipment Number
      │        ↓
      │       xPed
      │
      └── LINK_TO_TRX_LINE_ID / TRX_LINE_ID
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

## Alguns cuidados

Eu evitaria alterar diretamente uma definição seeded do Collaboration Messaging. O mais seguro é trabalhar com uma definição customizada e manter o XSL padrão como referência.

Também vale limitar a regra somente aos CFOPs necessários e manter um `otherwise` usando `nItemPed`. Isso reduz bastante o risco de impactar outras entradas de NF-e.

Antes de colocar a mudança em produção, o ideal é validar o XML autorizado e confirmar que o `infAdProd` está chegando exatamente com o identificador esperado.

Por fim, vale reforçar que `infAdProd` é um campo fiscal da NF-e. Neste cenário ele está sendo usado como parte de uma solução técnica para contornar uma limitação de tamanho do `nItemPed`, então a validação com a área fiscal continua sendo importante.

## Referências

- Oracle Fusion Cloud — Fiscal Document Capture  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — Collaboration Messaging Framework  
  https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/

- Oracle Fusion Cloud — ZX_LINES_DET_FACTORS  
  https://docs.oracle.com/en/cloud/saas/financials/

- Portal Nacional da NF-e  
  https://www.nfe.fazenda.gov.br/
