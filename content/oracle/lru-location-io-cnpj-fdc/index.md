---
title: "Oracle Cloud: CNPJ, LRU, Location e Inventory Organization no FDC"
description: "Configurando e auditando a relação entre LRU, localizações e organizações de inventário para o FDC."
date: 2026-10-13
article_id: "006"
tags: ["Oracle Cloud", "Brazil Localization", "FDC", "LRU", "CNPJ", "Inventory Organization", "Location", "SQL"]
categories: ["Oracle"]
toc: true
type: post
featured: true
draft: false
---

O registro do CNPJ na Legal Reporting Unit (LRU) não encerra a configuração fiscal do Oracle Cloud. A localização e a Inventory Organization (IO) também devem estar coerentes, com associações fiscais adequadas à operação.

## Triangulação dos cadastros

~~~text
Legal Entity
  └── Legal Reporting Unit (LRU)
       ├── CNPJ Registration
       ├── Associated Inventory Organization
       └── Associated Inventory/Ship-to Location
Inventory Organization ─── Location Address
Location ─── Inventory Organization (when applicable)
~~~

O desenho é conceitual, não uma exigência de relacionamento um-para-um. Para transferências internas, a Oracle documenta a associação da IO com a LRU para derivar o ship-from e a associação da localização com a LRU para o ship-to. As associações necessárias variam conforme o fluxo.

## Entendendo com um exemplo simples: dois depósitos

### 1. Exemplo prático

<style>
.bl-lru-example { margin: 1.25rem 0; border: 1px solid rgba(150, 150, 150, .38); border-radius: 10px; padding: 1.35rem 1.15rem 1.05rem; color: inherit; }
.bl-lru-example .bl-lru-depots { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.bl-lru-example .bl-lru-depot { text-align: center; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: .25rem; }
.bl-lru-example .bl-lru-icon { width: 26px; height: 26px; margin-bottom: .15rem; opacity: .9; }
.bl-lru-example .bl-lru-name { font-size: .96rem; font-weight: 600; }
.bl-lru-example .bl-lru-taxid, .bl-lru-example .bl-lru-action { font-size: .8rem; line-height: 1.5; opacity: .85; overflow-wrap: anywhere; }
.bl-lru-example .bl-lru-transfer { display: flex; align-items: center; justify-content: center; gap: .55rem; margin-top: 1.4rem; font-size: .85rem; }
.bl-lru-example .bl-lru-transfer svg { width: 18px; height: 18px; }
@media (max-width: 480px) {
  .bl-lru-example { padding: 1rem .65rem; }
  .bl-lru-example .bl-lru-depots { gap: .45rem; }
  .bl-lru-example .bl-lru-name { font-size: .85rem; }
  .bl-lru-example .bl-lru-taxid, .bl-lru-example .bl-lru-action { font-size: .68rem; }
}
</style>
<figure class="bl-lru-example" aria-label="Transferência de estoque">
  <div class="bl-lru-depots">
    <div class="bl-lru-depot">
      <svg class="bl-lru-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 20V8l9-5 9 5v12H3Z"/><path d="M7 20v-9h10v9M7 14h10M7 17h10M9 8h6"/></svg>
      <span class="bl-lru-name">Depósito A</span>
      <span class="bl-lru-taxid">CNPJ 12.345.678/0001-XX</span>
      <span class="bl-lru-action">Envia mercadorias</span>
    </div>
    <div class="bl-lru-depot">
      <svg class="bl-lru-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 20V8l9-5 9 5v12H3Z"/><path d="M7 20v-9h10v9M7 14h10M7 17h10M9 8h6"/></svg>
      <span class="bl-lru-name">Depósito B</span>
      <span class="bl-lru-taxid">CNPJ 12.345.678/0002-XX</span>
      <span class="bl-lru-action">Recebe mercadorias</span>
    </div>
  </div>
  <figcaption class="bl-lru-transfer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 17H3V6h12v11h-1M15 10h4l3 3v4h-2"/><circle cx="7.5" cy="17.5" r="2"/><circle cx="17.5" cy="17.5" r="2"/></svg><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg><span>Transferência de estoque</span></figcaption>
</figure>

Quando o depósito A transfere mercadorias para o depósito B, a Oracle precisa saber:

- Qual CNPJ será o remetente da nota fiscal?
- Qual CNPJ será o destinatário?

### Como o Oracle identifica o remetente e o destinatário?

Para **transferências internas**, a [documentação oficial Oracle 26D](https://docs.oracle.com/en/cloud/saas/financials/26d/faufa/define-ship-from-and-ship-to-legal-reporting-units.html) descreve duas associações distintas:

~~~text
REMETENTE (Ship-From)
Inventory Organization do Depósito A
                |
                v
        LRU da filial A
                |
                v
          CNPJ de A

DESTINATÁRIO (Ship-To)
Location de destino do Depósito B
                |
                v
        LRU da filial B
                |
                v
          CNPJ de B
~~~

- Para definir o **Ship-From**, entre em `Manage Associated Business Entities`, selecione a Legal Entity e a LRU do remetente e adicione uma linha do tipo `Inventory organization` com a IO correspondente. Para transferências internas e devoluções a fornecedor, essa associação ajuda a preencher a LRU remetente na tela `Update Fiscal Attributes`.
- Para definir o **Ship-To** de transferências internas, selecione a Legal Entity e a LRU do destinatário e adicione uma linha do tipo `Ship-from or to location` com a Location de destino. O destino é informado na tela `Edit Shipment`.

Em outras palavras: **o Oracle usa a IO para encontrar a LRU de origem e a Location de destino para encontrar a LRU de destino**, nos fluxos cobertos por essa regra. Não é necessário haver uma LRU exclusiva para cada IO; a estrutura fiscal deve refletir os estabelecimentos reais.

### Como isso se relaciona ao FDC?

Essas instruções da Oracle explicam principalmente a determinação de LRUs no **Fiscal Document Generation (FDG)**, durante a geração de documentos fiscais de embarque. Elas não afirmam que os mesmos relacionamentos, isoladamente, garantem a seleção de CNPJ no **Fiscal Document Capture (FDC)**.

No FDC, acesse `Create Fiscal Document` e pesquise pelo CNPJ em `Receiver Taxpayer ID`. Se ele estiver disponível, você confirmou que o cadastro fiscal pode ser encontrado nessa lista; ainda será necessário testar uma operação completa. Se não aparecer, confira o registro da LRU, a vigência e os vínculos relevantes, além do contexto e das permissões do usuário.

## Configuração passo a passo

1. Em Manage Legal Reporting Units, confira Legal Entity, LRU e vigência.
2. Em Manage Registrations, confirme jurisdição brasileira, Registration Code CNPJ, número, identificação e vigência.
3. Em Manage Inventory Organizations, confira Legal Entity, status e Location Address.
4. Em Manage Locations, confira endereço, status, datas e Inventory Organization atribuída, quando aplicável.
5. Em Manage Associated Business Entities, selecione Legal Entity e LRU e vincule a IO como Inventory organization e a Location conforme o tipo fiscal pertinente (Ship-from or to location, Inventory location etc.).
6. Valide o resultado no FDC e com um documento de teste.

## Exemplo fictício

| Object | Example |
|---|---|
| LRU | FISCAL BRANCH 02 |
| CNPJ | 12.345.678/0002-90 |
| Inventory Organization | WH02 |
| Location | WAREHOUSE LOCATION 02 |

## Query 1 — CNPJ duplicado entre LRUs

Busca CNPJs de registros fiscais vigentes em mais de uma LRU e informa o status calculado pelas datas de vigência da LRU.

~~~sql
WITH base AS (
 SELECT DISTINCT e.establishment_id lru_id, e.name lru_name,
 REGEXP_REPLACE(r.registration_number,'[^0-9]','') cnpj,
 e.effective_from,e.effective_to
 FROM xle_etb_profiles e, xle_registrations r, xle_jurisdictions_b j
 WHERE r.source_table='XLE_ETB_PROFILES'
 AND r.source_id=e.establishment_id
 AND r.jurisdiction_id=j.jurisdiction_id
 AND UPPER(j.registration_code_etb) LIKE '%CNPJ%'
 AND TRUNC(SYSDATE) BETWEEN NVL(TRUNC(r.effective_from),TRUNC(SYSDATE))
 AND NVL(TRUNC(r.effective_to),TRUNC(SYSDATE))
)
SELECT b.cnpj,b.lru_id,b.lru_name,
 CASE WHEN TRUNC(SYSDATE) BETWEEN
 NVL(TRUNC(b.effective_from),TRUNC(SYSDATE))
 AND NVL(TRUNC(b.effective_to),TRUNC(SYSDATE))
 THEN 'ACTIVE' ELSE 'INACTIVE' END lru_status,
 COUNT(*) OVER(PARTITION BY b.cnpj) qtd_lrus
FROM base b
WHERE b.cnpj IN (
 SELECT cnpj FROM base WHERE cnpj IS NOT NULL
 GROUP BY cnpj HAVING COUNT(DISTINCT lru_id)>1
)
ORDER BY b.cnpj,b.lru_name;
~~~

## Query 2 — Vínculos de IO e Location por LRU

Crie o parâmetro opcional P_CNPJ (texto) no BI Publisher. A consulta retorna as associações fiscais vigentes da LRU, identifica a IO e apresenta a Inventory Organization informada no cadastro da Location. Compare os vínculos com a configuração esperada.

~~~sql
WITH lru AS (
 SELECT DISTINCT e.establishment_id lru_id,e.name lru_name,
 REGEXP_REPLACE(r.registration_number,'[^0-9]','') cnpj
 FROM xle_etb_profiles e, xle_registrations r, xle_jurisdictions_b j
 WHERE r.source_table='XLE_ETB_PROFILES'
 AND r.source_id=e.establishment_id
 AND r.jurisdiction_id=j.jurisdiction_id
 AND UPPER(j.registration_code_etb) LIKE '%CNPJ%'
 AND TRUNC(SYSDATE) BETWEEN NVL(TRUNC(r.effective_from),TRUNC(SYSDATE))
 AND NVL(TRUNC(r.effective_to),TRUNC(SYSDATE))
)
SELECT l.lru_name,l.cnpj,a.entity_type,a.context,
 a.entity_name,a.entity_id,
 io.organization_code io_code,
 loc.location_code,
 loc.inventory_organization_id location_io_id,
 a.effective_from,a.effective_to
FROM lru l, xle_associations_v a,
 inv_org_parameters io, hr_locations_all_f_vl loc
WHERE a.legal_construct_id=l.lru_id
 AND io.organization_id(+)=CASE WHEN a.entity_type='INVENTORY_ORGANIZATION'
 THEN a.entity_id END
 AND loc.location_id(+)=CASE WHEN a.entity_type IN
 ('INVENTORY_LOCATION','SHIP_TO_LOCATION','BILL_TO_LOCATION')
 THEN a.entity_id END
 AND (loc.location_id IS NULL OR TRUNC(SYSDATE) BETWEEN
 loc.effective_start_date AND loc.effective_end_date)
 AND a.entity_type IN ('INVENTORY_ORGANIZATION','INVENTORY_LOCATION',
 'SHIP_TO_LOCATION','BILL_TO_LOCATION')
 AND TRUNC(SYSDATE) BETWEEN NVL(TRUNC(a.effective_from),TRUNC(SYSDATE))
 AND NVL(TRUNC(a.effective_to),TRUNC(SYSDATE))
 AND (:P_CNPJ IS NULL OR l.cnpj=REGEXP_REPLACE(:P_CNPJ,'[^0-9]',''))
ORDER BY l.cnpj,l.lru_name,a.entity_type,a.entity_name;
~~~

A consulta não retorna LRUs sem associação. Ela não comprova a Location Address atribuída à própria IO; valide-a no cadastro. Os tipos INVENTORY_LOCATION, SHIP_TO_LOCATION e BILL_TO_LOCATION representam associações distintas.

## Teste funcional no FDC

Abra Fiscal Document Capture → Create Fiscal Document → Receiver Taxpayer ID. Procure o CNPJ e confirme a entidade legal exibida. Caso não apareça, revise registro, vigência, localização, associações, BU e permissões. A aparição na lista verifica a visibilidade do Taxpayer ID; não garante, isoladamente, importação de XML, impostos ou contabilização.

## Pontos de atenção

CNPJ duplicado entre LRUs exige investigação, mas não comprova erro por si só. As datas, associações e o tipo de operação devem ser analisados antes de modificar um cadastro fiscal.

Não utilize telas reais, CNPJs reais ou endereços de produção em documentação pública. Altere parâmetros fiscais em produção apenas após testes e aprovação.

## Referências

- [Oracle — Define Ship-From and Ship-To Legal Reporting Units](https://docs.oracle.com/en/cloud/saas/financials/26d/faufa/define-ship-from-and-ship-to-legal-reporting-units.html)
- [Oracle — XLE_ASSOCIATIONS_V](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/xleassociationsv-8641.html)
- [Oracle — XLE_REGISTRATIONS](https://docs.oracle.com/en/cloud/saas/financials/26a/oedmf/xleregistrations-28020.html)
- [Oracle — HR_LOCATIONS_ALL_F_VL](https://docs.oracle.com/en/cloud/saas/human-resources/oedmh/hrlocationsallfvl-8019.html)
