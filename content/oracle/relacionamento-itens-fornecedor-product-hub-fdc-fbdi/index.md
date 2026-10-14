---
title: "Oracle Cloud: relacionamento de itens de fornecedores com Product Hub, FDC e FBDI"
description: "Como criar relacionamentos Supplier Item no Product Hub por FBDI e automatizar a derivação a partir do FDC com LACLS e OIC."
date: 2026-10-14
article_id: "007"
tags: ["Oracle Cloud", "Product Hub", "FDC", "FBDI", "OIC", "LACLS", "Trading Partner Items", "SCM", "SQL"]
categories: ["Oracle"]
toc: true
type: post
featured: true
draft: false
---

O mesmo material pode ter dois códigos: um no cadastro interno da empresa e outro no catálogo do fornecedor. No recebimento de uma nota fiscal, o XML normalmente traz o código utilizado pelo emissor; o Oracle Fusion Cloud precisa identificar o item interno correspondente.

Uma forma de reduzir esse trabalho manual é manter **relacionamentos entre itens de parceiros comerciais** no Product Hub (*Trading Partner Item Relationships*). Para fornecedores, os testes analisados utilizaram o relacionamento **SUPPLIER_ITEM_XREF**.

Neste artigo apresento duas formas complementares de manter esse vínculo: a carga FBDI e a derivação automática a partir do Fiscal Document Capture (FDC).

## 1. O que é um Trading Partner Item?

Um *Trading Partner Item* representa o código com que um parceiro comercial identifica determinado produto. O relacionamento associa esse registro a um item do catálogo Oracle.

| Informação | Exemplo fictício |
|---|---|
| Item no Oracle | ITEM_INTERNO_001 |
| Item do fornecedor | FORN-98765 |
| Tipo do parceiro | SUPPLIER |
| Relacionamento | SUPPLIER_ITEM_XREF |
| Organização | MASTER |

A chave de interpretação não é apenas o código externo. O fornecedor também precisa ser identificado: empresas diferentes podem utilizar o mesmo código para materiais distintos.

### Duas estratégias, um mesmo objetivo

| Estratégia | Quando usar | Componentes |
|---|---|---|
| **FBDI** | Migração, carga inicial e manutenção em massa | Planilha XLSM, CSV/ZIP, Load Interface File for Import, Item Import |
| **LACLS/OIC** | Manutenção contínua a partir de dados operacionais | FDC, BI Publisher, Oracle Integration Cloud e Product Hub |

A primeira antecipa o cadastro; a segunda busca reaproveitar a associação já identificada em um documento fiscal ou no processo de compras.

## 2. Criação por FBDI

O template de importação de itens do Oracle possui várias abas. Duas são relevantes para este cenário:

- **EGP_TRADING_PARTNER_ITEMS_INTF**: cadastra o item identificado pelo fornecedor.
- **EGP_ITEM_RELATIONSHIPS_INTF**: cria o vínculo entre esse item externo e o item Oracle.

### 2.1. Trading Partner Item

Os principais campos são:

| Campo técnico | Exemplo fictício |
|---|---|
| TRANSACTION_TYPE | SYNC |
| BATCH_ID | 90001 |
| TP_ITEM_NUMBER | FORN-98765 |
| TP_ITEM_DESC | MATERIAL EXEMPLO |
| TP_TYPE | SUPPLIER |
| TRADING_PARTNER_NUMBER | 7000123 |

**Atenção ao TRADING_PARTNER_NUMBER.** No teste de pré-produção documentado, o valor aceito para o fornecedor foi **HZ_PARTIES.PARTY_NUMBER**, e não o Supplier Number (POZ_SUPPLIERS_V.SEGMENT1) nem o PARTY_ID. A tentativa de usar o Supplier Number resultou em **EGP_TP_PK_MISSING**.

Essa é uma constatação do ambiente testado, não uma regra que dispense conferir o cadastro e a release em uso.

### 2.2. Item Relationship

Na segunda aba, o relacionamento pode ser descrito assim:

| Campo técnico | Exemplo fictício |
|---|---|
| TRANSACTION_TYPE | SYNC |
| BATCH_ID | 90002 |
| ITEM_RELATIONSHIP_TYPE | SUPPLIER_ITEM_XREF |
| ITEM_NUMBER | ITEM_INTERNO_001 |
| ORGANIZATION_CODE | MASTER |
| MASTER_ORGANIZATION_CODE | MASTER |
| SOURCE_SYSTEM_CODE | PIMDH |
| TP_ITEM_NUMBER | FORN-98765 |
| TRADING_PARTNER_NUMBER | 7000123 |

O código **PIMDH** apareceu no template testado; confirme o *source system* configurado no seu ambiente.

**Os lotes podem ser diferentes.** Nas duas planilhas de referência, a aba de Trading Partner Items tinha um BATCH_ID, e a de relacionamentos tinha outro. Isso permite processar primeiro a criação do item externo e depois seu vínculo, executando o **Item Import para cada lote**. Se optar por uma carga conjunta, planeje os lotes e parâmetros de acordo com o template e com as regras da instância. O BATCH_ID do job deve corresponder ao dos registros que ele pretende processar.

### 2.3. Passo a passo da importação

1. Confirmar que o item Oracle existe na organização desejada.
2. Identificar o fornecedor, seu PARTY_NUMBER e o código externo.
3. Verificar se o item do fornecedor e o relacionamento já existem.
4. Preencher o XLSM original sem alterar nomes de abas, cabeçalhos e macros.
5. Executar **Generate CSV File** e gerar o ZIP.
6. Em **Tools > Scheduled Processes**, executar **Load Interface File for Import** com o ZIP.
7. Executar **Item Import** para o lote correspondente, conferindo parâmetros e logs.
8. Validar os dados no Product Hub ou por consulta autorizada.

O status **Succeeded** em *Load Interface File for Import* confirma a carga para as interfaces, mas **não prova que o relacionamento foi criado**. Isso depende da execução e do resultado do *Item Import*.

> **Observação de versão:** a documentação Oracle de FBDI consultada para 26C enumera MANUFACTURER, COMPETITOR e CUSTOMER nos exemplos de Trading Partner Type; as planilhas e o teste de pré-produção analisados utilizam SUPPLIER. Portanto, o suporte e as validações específicas desse tipo devem ser conferidos na release e na configuração da instância antes de aplicar a carga.

## 3. Derivação automática com FDC, BI Publisher e OIC

A solução **Latin America Cloud Local Solution (LACLS) — Item Relationship Derivation**, descrita em um guia técnico de 2021, propõe criar ou atualizar o relacionamento a partir de informações já tratadas no processo operacional.

Exemplo: ao receber uma nota fiscal, o FDC apresenta um código externo ainda não identificado. O usuário seleciona o item Oracle correto. A integração consulta essa correspondência e a utiliza para manter o relacionamento no Product Hub. Em documentos posteriores, esse cadastro **pode** permitir a derivação automática do item interno, desde que as condições de identificação e as configurações do ambiente sejam atendidas.

~~~text
XML / Compra
     |
Fiscal Document Capture (FDC)
     |
Código externo + item Oracle identificado
     |
BI Publisher (extração)
     |
Oracle Integration Cloud (OIC)
     |
Product Hub
     |
Relacionamento SUPPLIER_ITEM_XREF
~~~

### 3.1. Componentes descritos no guia

| Componente | Identificador |
|---|---|
| Relatório BI Publisher | LACLS_BR_ITEM_RELATIONSHIP_UPDATE |
| Data Model BI Publisher | LACLS_BR_ItemRelationShipsDm |
| Integração agendada | LACLS_BR_FDC_TRADING_RELAT_UPD |
| Lookup OIC | LACLS_FDC_TRADING_REL_LKP |

O guia situa o relatório no catálogo BI Publisher em **Shared Folders / Custom / Local Solution / BR / FDC x Product Info Item**, com o Data Model na subpasta **Data Models**.

O lookup inclui valores de integração, tipo de parceiro e data de corte; o documento usa **Supplier** como tipo do parceiro. A frequência apresentada para a integração agendada é de **um dia**, uma decisão de implementação do exemplo, não uma periodicidade universal exigida pelo Oracle.

O guia também menciona o pacote OIC **LACLS_BR_FDC_TRADING_PARTNER_MGMT.par** e a referência técnica **33210053**. Por ser uma documentação de 2021, a disponibilidade dos artefatos e sua compatibilidade devem ser verificadas no ambiente atual.

### 3.2. Outra origem: Procurement

O documento funcional também menciona o *Supplier Item* informado durante cotação, negociação, acordo ou ordem de compra. Quando essa informação é propagada ao FDC e está disponível para a integração, pode contribuir para a manutenção dos relacionamentos. A derivação exata depende do fluxo implantado.

## 4. Consultas SQL para validação

As queries a seguir foram adaptadas dos manuais analisados. Sua execução depende da exposição dos objetos e das permissões do BI Publisher no ambiente.

### 4.1. Identificar Supplier Number e Party Number

~~~sql
SELECT
    ps.segment1    AS supplier_number,
    ps.vendor_name AS supplier_name,
    ps.vendor_id,
    ps.party_id,
    hp.party_number AS trading_partner_number
FROM poz_suppliers_v ps
JOIN hz_parties hp
  ON hp.party_id = ps.party_id
WHERE ps.segment1 = :P_SUPPLIER_NUMBER
ORDER BY ps.vendor_name
~~~

### 4.2. Consultar Trading Partner Items

~~~sql
SELECT
    tpi.tp_item_id,
    tpi.tp_item_number,
    tpi.tp_item_desc,
    tpi.tp_type,
    hp.party_number AS trading_partner_number
FROM egp_trading_partner_items tpi
JOIN hz_parties hp
  ON hp.party_id = tpi.trading_partner_id
WHERE tpi.tp_type = 'SUPPLIER'
  AND tpi.tp_item_number = :P_SUPPLIER_ITEM
ORDER BY hp.party_number
~~~

### 4.3. Verificar relacionamentos

~~~sql
SELECT
    x.item_relationship_id,
    x.supplier_id,
    x.tp_item_id,
    x.supplier_item_num,
    x.inventory_item_id,
    x.master_organization_id
FROM egp_search_tpi_sup_xrefs_v x
WHERE x.supplier_item_num = :P_SUPPLIER_ITEM
ORDER BY x.supplier_id
~~~

O mesmo código de item externo pode aparecer para vários fornecedores. Para concluir a validação, confira também o parceiro comercial e a organização.

### 4.4. Conferir o lote na interface

~~~sql
SELECT
    transaction_id,
    batch_id,
    tp_item_number,
    tp_type,
    trading_partner_number,
    transaction_type,
    process_status
FROM egp_trading_partner_items_intf
WHERE batch_id = :P_BATCH_ID
ORDER BY transaction_id DESC
~~~

Em um dos testes, **PROCESS_STATUS = 3** indicou registros com erro. Consulte o log detalhado do *Item Import* para determinar a causa; não interprete isoladamente o código numérico.

## 5. Erros frequentes

| Sintoma | Verificação |
|---|---|
| EGP_TP_PK_MISSING | Comparar TRADING_PARTNER_NUMBER com PARTY_NUMBER e validar TP_TYPE |
| Item Oracle inválido | Conferir ITEM_NUMBER e organização |
| Supplier Item não localizado | Confirmar se o Trading Partner Item foi importado antes do relacionamento |
| Relacionamento duplicado | Pesquisar o vínculo existente antes de reenviar |
| Load Interface concluído sem vínculo | Executar e analisar Item Import com o BATCH_ID correto |
| ORA-00942 na SQL | Validar acesso do BI Publisher ao objeto, não presumir ausência de cadastro |

## 6. Qual abordagem utilizar?

Para uma migração inicial ou carga em grande escala, o **FBDI** oferece maior controle sobre os registros que serão importados.

Para manutenção recorrente a partir de recebimentos fiscais, a solução **LACLS/OIC** pode reduzir a necessidade de associações manuais repetitivas.

A combinação das duas abordagens é possível, desde que existam regras para evitar duplicidades, manter os identificadores corretos e acompanhar os erros. **Criar o relacionamento não significa, por si só, que qualquer nota fiscal será automaticamente processada**: o FDC ainda depende das condições e validações do fluxo fiscal.

## Referências

- [Oracle — Overview of Item Relationships](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/fapim/overview-of-item-relationships.html)
- [Oracle — Overview of Import Items](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faicf/overview-of-import-items.html)
- [Oracle — Item Import](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faspc/item-import.html)
- [Oracle — How do I create Trading Partner Items with FBDI?](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26c/faipr/how-do-i-create-trading-partner-items-with-fbdi.html)
- Oracle LACLS — *Item Relationship Derivation, Technical Installation*, versão 1 (2021), referência 33210053, e manuais operacionais de FBDI utilizados como base deste estudo.
