---
title: "Oracle Cloud: atualização automatizada do DFF de Shipments com BI Publisher, OIC e REST"
description: "Exemplo técnico de extração SQL, mapeamento de DFF, API ShipmentUpdate, rastreabilidade e tratamento de erros antes do FDG."
date: 2026-10-12
article_id: "005"
tags:
  - Oracle Cloud
  - Brazil Localization
  - SCM
  - Shipping
  - BI Publisher
  - OIC
  - REST API
  - FDG
  - SQL
categories:
  - Oracle
toc: true
type: post
featured: true
draft: false
---

No [artigo anterior](/oracle/automatizacao-fiscal-shipment-fdg/), expliquei por que o preenchimento manual de atributos fiscais nos shipments pode se tornar um gargalo na emissão de NF-e em volume. Aqui, o objetivo é detalhar a arquitetura e apresentar exemplos técnicos de como automatizar essa preparação no Oracle Fusion Cloud SCM.

> **Nota:** os SQLs, os identificadores e o JSON abaixo são exemplos didáticos, construídos com objetos públicos da Oracle. Não são a reprodução de código de produção. O contexto e os segmentos do DFF devem ser definidos e validados em cada ambiente.

## 1. Arquitetura

A solução separa a consulta dos registros, a orquestração e a atualização no ERP:

```text
Oracle SCM / Shipping
        |
        | Shipment criado
        v
BI Publisher Data Model (SQL)
        |
        | Lista de shipments elegíveis
        v
Oracle Integration Cloud (OIC)
        |
        +--> Leitura do resultado
        +--> Validação e mapeamento por operação
        +--> For-Each (um shipment por vez)
                 |
                 v
          REST API ShipmentUpdate
                 |
                 +--> Sucesso: registrar resultado
                 +--> Falha: registrar erro e continuar
        |
        v
Shipment com DFF preparado
        |
        v
Processo independente de geração fiscal (FDG)
```

O BI Publisher identifica *candidatos* à atualização. O OIC aplica as regras de mapeamento, chama a API e acompanha as respostas. A geração do documento fiscal é uma etapa separada.

## 2. Extração dos shipments elegíveis via BI Publisher

Uma fonte de consulta é a tabela pública `WSH_NEW_DELIVERIES`, que contém informações do cabeçalho do shipment. Entre suas colunas estão `DELIVERY_NAME`, `ORGANIZATION_ID`, `SOURCE_LINE_TYPE`, `ATTRIBUTE_CATEGORY` e `FD_PROCESSING_STATUS`.

Para o exemplo, considerei apenas Sales Orders e Transfer Orders de uma organização informada por parâmetro, com o contexto do DFF vazio e sem status de processamento fiscal.

```sql
SELECT
    wnd.delivery_id,
    wnd.delivery_name       AS shipment_number,
    wnd.organization_id,
    wnd.source_line_type,
    wnd.attribute_category  AS dff_context,
    wnd.fd_processing_status,
    CASE
        WHEN wnd.source_line_type = 'SALES_ORDER'
            THEN 'SALE'
        WHEN wnd.source_line_type = 'TRANSFER_ORDER'
            THEN 'TRANSFER'
    END AS operation_type
FROM
    wsh_new_deliveries wnd
WHERE
    wnd.organization_id = :P_ORGANIZATION_ID
    AND wnd.source_line_type IN (
        'SALES_ORDER',
        'TRANSFER_ORDER'
    )
    AND wnd.attribute_category IS NULL
    AND wnd.fd_processing_status IS NULL
ORDER BY
    wnd.delivery_id
```

O parâmetro `P_ORGANIZATION_ID` é definido no Data Model; não existe um ID de organização fixado no artigo. O `CASE` gera um valor lógico de apoio ao mapeamento e **não** representa uma classificação fiscal oficial.

Esses filtros são um ponto de partida: em uma implementação real, é necessário verificar a unidade fiscal vinculada à organização, os estados operacionais permitidos, a necessidade de documento fiscal e a existência de DFF já utilizado por outro processo. `ATTRIBUTE_CATEGORY IS NULL` não deve ser tratado como uma regra universal.

### Consulta para conferir um shipment

Após a chamada REST, podemos consultar os campos do cabeçalho para verificar a atualização:

```sql
SELECT
    wnd.delivery_name,
    wnd.organization_id,
    wnd.source_line_type,
    wnd.attribute_category,
    wnd.attribute1,
    wnd.attribute2,
    wnd.fob_code,
    wnd.fd_processing_status,
    wnd.last_update_date
FROM
    wsh_new_deliveries wnd
WHERE
    wnd.organization_id = :P_ORGANIZATION_ID
    AND wnd.delivery_name = :P_SHIPMENT_NUMBER
```

Os campos `ATTRIBUTE1` e `ATTRIBUTE2` são mostrados apenas como exemplo de armazenamento de segmentos do DFF. Sua correspondência com campos da tela depende da configuração e não deve ser presumida.

### Consulta para medir o volume

Antes de definir a periodicidade da integração, também é útil estimar quantos registros estão pendentes:

```sql
SELECT
    wnd.source_line_type,
    COUNT(*) AS total_shipments,
    SUM(
        CASE
            WHEN wnd.attribute_category IS NULL
             AND wnd.fd_processing_status IS NULL
            THEN 1 ELSE 0
        END
    ) AS candidates_for_review
FROM
    wsh_new_deliveries wnd
WHERE
    wnd.organization_id = :P_ORGANIZATION_ID
    AND wnd.source_line_type IN (
        'SALES_ORDER',
        'TRANSFER_ORDER'
    )
GROUP BY
    wnd.source_line_type
ORDER BY
    wnd.source_line_type
```

Esse total mede candidatos pelos critérios simplificados. Não equivale à quantidade de NF-e que será emitida.

## 3. Construção do Data Model

No BI Publisher, o Data Model pode ser configurado com uma consulta SQL, o parâmetro obrigatório `P_ORGANIZATION_ID` e saída XML.

A execução do OIC recebe o conjunto retornado, interpreta os elementos e percorre os registros. É importante validar os nomes das tags efetivamente geradas pelo Data Model, especialmente quando os aliases do SQL são alterados.

Não é necessário atualizar a tabela via SQL. No Oracle Fusion SaaS, a consulta é realizada pelo recurso de relatórios, enquanto a alteração do shipment utiliza o serviço suportado.

## 4. Atualização via REST API

O recurso público da Oracle para esse padrão é:

```http
POST /fscmRestApi/resources/11.13.18.05/shipmentTransactionRequests
Content-Type: application/json
```

Com `ActionCode = ShipmentUpdate`, enviamos o shipment e os atributos configurados no DFF. A estrutura conceitual é:

```json
{
  "ActionCode": "ShipmentUpdate",
  "shipments": [
    {
      "Shipment": "1000001",
      "shipmentDFF": [
        {
          "__FLEX_Context": "<CONTEXTO_DFF>",
          "<NOME_API_DO_SEGMENTO>": "<VALOR_MAPEADO>"
        }
      ]
    }
  ]
}
```

O número `1000001` é fictício. Os valores entre `< >` são placeholders: esse payload **não está pronto para execução**. Os nomes dos segmentos precisam corresponder ao DFF configurado e publicado, e os valores devem obedecer às respectivas listas de valores e regras.

Um cuidado importante é não confundir campos nativos do shipment, como `FOB_CODE`, com segmentos de DFF. Cada informação deve ser enviada ao atributo correto suportado pela API.

### Regra de mapeamento

A transformação no OIC pode diferenciar a operação de origem:

```text
Se SOURCE_LINE_TYPE = SALES_ORDER:
    selecionar as regras fiscais para venda
Se SOURCE_LINE_TYPE = TRANSFER_ORDER:
    selecionar as regras fiscais para transferência
Caso contrário:
    ignorar e registrar o motivo
```

Essa é uma representação lógica; os valores fiscais concretos dependem do desenho funcional e não devem ser deduzidos apenas do tipo do shipment. Também é necessário distinguir `null` JSON de uma string `"null"`, pois não produzem o mesmo resultado.

## 5. Orquestração no OIC

Uma implementação prática pode seguir estes passos:

1. Criar uma integração *Scheduled Orchestration* com frequência adequada ao volume.
2. Invocar o Data Model do BI Publisher por uma conexão autenticada ao ERP.
3. Ler a resposta XML e transformá-la em uma lista de shipments.
4. Executar um `For-Each` para cada registro.
5. Dentro de um `Scope`, montar o JSON e chamar `ShipmentUpdate`.
6. Inspecionar a resposta funcional da API e registrar sucesso ou erro.
7. No tratamento de falha local, registrar o shipment afetado e prosseguir com os demais.
8. Em falhas de conectividade ou da própria extração, encerrar a execução com erro e encaminhar o evento ao monitoramento.

A resposta HTTP, isoladamente, não é prova suficiente de que todos os dados foram processados como esperado. É necessário analisar o resultado da transação e, nos casos importantes, confirmar os atributos no ERP.

## 6. Evitando reprocessamento e alterações indevidas

Um processo agendado precisa considerar idempotência. Para isso:

- Consultar apenas shipments realmente elegíveis e verificar novamente o estado antes da atualização.
- Não sobrescrever contextos ou segmentos de DFF preenchidos por outros fluxos.
- Registrar o identificador do shipment, horário, resultado e uma referência da execução.
- Proteger as credenciais no gerenciador de conexões, nunca no payload ou nos logs.
- Tratar separadamente falhas temporárias e erros de configuração fiscal.
- Controlar concorrência para evitar duas execuções atualizando o mesmo shipment.

Em ambientes SaaS, o BI Publisher deve ser usado para leitura; alterações transacionais devem seguir APIs e funcionalidades suportadas.

## 7. Validação e monitoramento

A conferência pode ser feita em **Supply Chain Execution > Inventory Management > Manage Shipments**, pesquisando pelo número do shipment e consultando seus atributos.

O monitoramento do OIC deve permitir responder: quantos registros foram identificados, quantos receberam atualização, quais falharam e quais precisam de intervenção.

É recomendável testar, separadamente, Sales Order, Transfer Order, shipment com DFF preenchido, shipment já em processamento fiscal, payload inválido e indisponibilidade temporária da API.

## Conclusão

A parte técnica mais importante não é o POST em si, mas selecionar corretamente os shipments, mapear os segmentos fiscais e impedir que uma execução em volume altere dados que não deveria.

Com BI Publisher para seleção, OIC para orquestração e API REST para atualização, temos uma arquitetura que separa responsabilidades e facilita observabilidade e manutenção — sem confundir a preparação do shipment com a emissão e autorização da NF-e.

## Referências oficiais

- [Oracle — WSH_NEW_DELIVERIES (Data Model)](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26a/oedsc/wshnewdeliveries-17278.html)
- [Oracle — REST API: Create Shipment Transaction Request](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25c/fasrp/op-shipmenttransactionrequests-post.html)
- [Oracle — Fiscal Document Generation](https://docs.oracle.com/en/cloud/saas/financials/25d/faufa/fiscal-document-generation.html)
- [Oracle — Manage Brazil Outbound Shipments](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/famlo/how-you-manage-brazil-outbound-shipments.html)
