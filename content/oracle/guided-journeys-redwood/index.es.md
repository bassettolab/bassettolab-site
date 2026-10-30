---
title: "Oracle Cloud Redwood: Guided Journeys tradicionales y con agentes de IA"
description: "Guía práctica para configurar Guided Journeys informativos y con agentes de IA en Self Service Procurement Redwood."
date: 2026-10-28
categories: ["TI", "Oracle", "Cloud"]
tags: ["Oracle Fusion Cloud", "Redwood", "Guided Journeys", "Procurement", "AI Agent Studio", "Visual Builder Studio"]
draft: false
featured: true
type: post
toc: true
---

## Dos escenarios de Guided Journey

Un **Guided Journey** ofrece orientación contextual dentro de una página Redwood de Oracle Fusion Cloud. Los siguientes escenarios son dos aplicaciones del mismo recurso.

| Escenario | Objetivo | Contenido |
| --- | --- | --- |
| Journey informativo | Guiar al usuario durante una actividad | Documentos, informes BI Publisher, análisis OTBI, vídeos y enlaces externos |
| Journey con agente de IA | Proporcionar consultas interactivas en la página | Tarea Agent asociada a un agente publicado en AI Agent Studio |

El ejemplo utiliza la página de **Self Service Procurement / Purchase Requisitions** en Redwood. El mismo método puede aplicarse a otras páginas de Procurement y SCM **solo si disponen de la propiedad de Guided Journey correspondiente**. Un Journey no modifica los permisos del usuario.

## Dónde utilizarlo

- **Self Service Procurement:** manuales de solicitudes de compra, informes de aprobaciones pendientes, políticas y vídeos.
- **Purchasing y Procurement:** instrucciones operativas y políticas en páginas compatibles.
- **SCM:** información de apoyo en páginas Redwood compatibles de Inventory, Order Management y otras áreas.
- **Agentes de IA en Procurement:** consultas sobre el estado de solicitudes, aprobadores pendientes y colas de aprobación, según las herramientas y autorizaciones disponibles.

## Flujo 1 — Guided Journey informativo

```text
My Routines > Journeys Setup > Guided Journey
                    |
            Create > Name + Code
                    |
              Create Draft
                    |
           Add Tasks (1..N)
                    |
 Document / Report / Analytics / Video / External URL
                    |
       Guardar > Preview > Traducciones
                    |
        Copiar código del Journey
                    |
 Redwood > Edit Page in Visual Builder Studio
                    |
       Page Properties > Journey Code
                    |
             Preview > Publish
```

### 1. Crear el Journey

1. Acceda a **My Routines > Journeys Setup > Guided Journey**.
2. Seleccione **Create**, informe **Name** y **Code**, y pulse **Create Draft**.
3. En **Tasks**, seleccione **Add** para agregar las tareas.
4. Como ejemplo genérico, utilice `Guia de Solicitudes` y el código `GUIA_SOLICITUDES`.

La documentación de SCM y Procurement también menciona **Setup and Maintenance > Application Extensions > Guided Journeys** dentro de un offering aplicable.

### 2. Configurar los tipos de tarea

- **Document:** `Task Type = Document`; añada instrucciones y un PDF. Utilice **Translation Editor** para traducir los textos disponibles.
- **Report:** `Task Type = Report`; indique la ruta de un informe BI Publisher autorizado, como `/Custom/Procurement/INFORME_EJEMPLO.xdo`.
- **Analytics:** `Task Type = Analytics`, `Type of Analysis = OTBI Analysis`; informe una ruta válida del catálogo, como `/shared/Custom/Procurement/ANALISIS_EJEMPLO`.
- **Video:** `Task Type = Video`, `Video Type = Embedded URL`; utilice una URL de inserción admitida.
- **External URL:** añada una página de referencia, como los [vídeos de Oracle Procurement 26C](https://docs.oracle.com/en/cloud/saas/procurement/26c/videos.html).

Las rutas anteriores son solo ejemplos. Compruebe cada tarea mediante **Preview** y verifique los permisos del público destinatario.

### 3. Asociarlo a la página Redwood

1. Copie el **Code** del Journey y abra la página inicial Redwood de Self Service Procurement.
2. En **Settings and Actions**, seleccione **Edit Page in Visual Builder Studio**.
3. En **Express mode > Page Properties**, localice la propiedad compatible **Guided Journey Code** e introduzca el código.
4. Valide con **Preview** y publique con **Publish**.

Las propiedades pueden llamarse `journeyCode` a nivel de página o `sectionNameJourneyCode` a nivel de sección. **No invente propiedades** si la página no las ofrece.

## Flujo 2 — Guided Journey con agente de IA

```text
Configurar seguridad y roles de AI Agent Studio
                    |
 AI Agent Studio > Marketplace > Copy Template
                    |
  Personalizar / Probar / Publicar agente
                    |
 Habilitar tareas Agent en Guided Journeys
                    |
     Guided Journey > Task Type = Agent
                    |
        Seleccionar agente publicado
                    |
         Save > Activate > Preview
                    |
 Redwood > Visual Builder Studio > Journey Code
                    |
             Preview > Publish
```

### 1. Seguridad y requisitos previos

En **Setup and Maintenance > Manage Administrator Profile Values**, el procedimiento documentado utiliza:

```text
ORA_ASE_SAS_INTEGRATION_ENABLED = Yes (Site)
```

Después, ejecute en **Tools > Scheduled Processes**, en este orden:

1. `Import Resource Application Security Data`
2. `Import User and Role Application Security Data`

Conceda privilegios administrativos solo a perfiles autorizados. El ejemplo incluye las siguientes duties; compruebe su existencia y necesidad en la versión utilizada:

| Área | Duty / privilege |
| --- | --- |
| Roles and Privileges | `ORA_PO_PRC_AI_AGENT_MANAGEMENT_DUTY` |
| Roles and Privileges — variante documentada | `ORA_PO_PRC_AI_AGENT_MANAGEMENT_DUTY_HCM` |
| Roles and Permission Groups | `ORA_DR_FAI_GENERATIVE_AI_AGENT_PRC_ADMINISTRATOR_DUTY` |

La configuración de chat para usuarios finales también menciona `ORA_HCM_VBCS_PWA_ENABLED = Y`, el privilegio `HRC_ACCESS_AI_AGENT_CHAT_PRIV` y la duty `ORA_DR_FAI_GENERATIVE_AI_AGENT_RUNTIME_DUTY`. Son ejemplos técnicos, **no una matriz de seguridad universal**. Aplique mínimos privilegios y pruebe con un usuario no administrador.

### 2. Crear y publicar el agente

1. Abra **AI Agent Studio > Marketplace**.
2. Busque **Purchase Requisition Status Advisor** y seleccione **Copy Template**.
3. Personalice los mensajes iniciales, herramientas y permisos. Pruebe el agente.
4. Seleccione **Publish**.

Preguntas de ejemplo, sin identificadores reales:

```text
What is the status of purchase requisition SAMPLE_REQ?
Who is the pending approver for SAMPLE_REQ?
How many requisitions are pending approval under my account?
```

La respuesta dependerá de las herramientas configuradas, los registros disponibles y los permisos del usuario.

### 3. Habilitar y añadir la tarea Agent

En **Manage Administrator Profile Values**, el procedimiento incluye:

```text
ORA_PER_AGENT_TASK_TYPE_GUIDED_JOURNEYS_ENABLED = Y
```

Cree un Guided Journey, añada una tarea **Task Type = Agent**, seleccione el agente publicado y ejecute **Save > Activate**. Valide con **Preview**.

### 4. Publicar en Redwood

Introduzca el **Code** del Journey en la propiedad disponible en **Edit Page in Visual Builder Studio > Page Properties**, valide y seleccione **Publish**.

### 5. Acceso alternativo por chat

Algunos procedimientos describen un acceso directo creado con un sandbox de **Structure > Create Page Entry**. Estos parámetros requieren validación específica de seguridad y versión:

```text
Name: AI Chat
Group: Shortcuts
Link Type: VB Studio Page
Focus View ID: /index.html
Web Application: ORA_FSCM_UI
Secured Resource Name: /vbcs/hcm/hcmAgentChat/access
Application Stripe: hcm
```

Este acceso es una alternativa de navegación, no un segundo Journey. No lo despliegue sin comprobar la ruta relacionada con HCM y sus políticas de acceso en el contexto SCM/Procurement.

## Puntos de atención

- **Dos niveles de publicación:** activar el Journey no publica automáticamente la extensión de la página Redwood.
- **Compatibilidad:** solo se puede asociar cuando existe una propiedad de Journey compatible.
- **Seguridad:** siguen aplicándose los permisos de informes, documentos, enlaces y agentes.
- **Diferencias entre versiones:** menús, opciones y roles pueden cambiar; valide primero en un entorno de pruebas.

## Documentación oficial de Oracle

- [Guided Journeys en Fusion SCM y Procurement](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faicf/guided-journeys.html)
- [Agentes de IA SCM y Guided Journeys](https://docs.oracle.com/en/cloud/saas/readiness/scm/25a/plm25a/25A-plm-wn-f36914.htm)
- [Extending Redwood Applications Using Visual Builder Studio](https://docs.oracle.com/cd/G55130_01/trans/G34703-05/extending-redwood-applications-for-hcm-and-scm-using-visual-builder-studio.pdf)
- [Adopción de Redwood para SCM y Procurement](https://docs.oracle.com/en/cloud/saas/readiness/redwood-adoption/raoac/rw-scm.html)

Las rutas de catálogo, los roles personalizados, los códigos de Journey y los identificadores de solicitud son ejemplos genéricos. Sustitúyalos únicamente por valores autorizados para su entorno.
