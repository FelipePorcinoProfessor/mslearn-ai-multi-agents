---
title: Labs de Multi-Agentes com Microsoft Foundry
permalink: index.html
layout: default
---

<div class="course-intro"><p>Este site reúne laboratórios práticos sobre desenvolvimento, orquestração, segurança, governança, observabilidade e operação de soluções multi-agentes com <strong>Microsoft Foundry</strong> e serviços do Azure.</p></div>

<div class="course-note"><strong>Importante:</strong> cada lab inclui código e recursos de apoio no diretório <code>Allfiles</code>. Consulte os pré-requisitos descritos no início de cada exercício antes de começar.</div>

## Labs {#labs}

<div class="course-grid">
  {%- assign labs = site.pages | where_exp: "page", "page.path contains 'Instructions/Labs/'" | sort: "path" -%}
  {%- for activity in labs -%}
    {%- if activity.lab.title -%}
    <article class="course-card"><h3><a href="{{ activity.url | relative_url }}">{{ activity.lab.title }}</a></h3><div class="course-meta">{%- if activity.lab.level -%}<span class="course-badge">Nível {{ activity.lab.level }}</span>{%- endif -%}{%- if activity.lab.duration -%}<span class="course-badge">{{ activity.lab.duration }} min</span>{%- endif -%}</div>{%- if activity.lab.description -%}<p>{{ activity.lab.description }}</p>{%- endif -%}</article>
    {%- endif -%}
  {%- endfor -%}
</div>

> **Dica:** consulte também o [Microsoft Learn](https://learn.microsoft.com/training/), que oferece conteúdo conceitual associado às tecnologias usadas nestes labs.
