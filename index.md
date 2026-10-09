---
title: Labs de Multi-Agentes com Microsoft Foundry
permalink: index.html
layout: default
---

<style>
  .course-intro { max-width:58rem; margin:0 auto 2rem; font-size:1.08rem; line-height:1.7; }
  .course-note { margin:1.5rem 0 2.25rem; padding:1rem 1.25rem; border-left:4px solid #1a45a5; border-radius:0 8px 8px 0; background:#f4f7fc; }
  .course-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(17rem,1fr)); gap:1rem; margin:1.5rem 0 2.5rem; }
  .course-card { display:flex; flex-direction:column; min-height:11rem; padding:1.2rem; border:1px solid #e1e5ec; border-radius:12px; background:#fff; box-shadow:0 2px 8px rgba(20,40,80,.06); transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease; }
  .course-card:hover,.course-card:focus-within { transform:translateY(-3px); border-color:#8ca9df; box-shadow:0 8px 20px rgba(20,40,80,.12); } .course-card h3 { margin:0 0 .55rem; font-size:1.04rem; line-height:1.35; } .course-card h3 a { color:#173f91; text-decoration:none; } .course-card h3 a:hover,.course-card h3 a:focus { text-decoration:underline; }
  .course-meta { margin-top:auto; color:#5d6878; font-size:.82rem; } .course-badge { display:inline-block; margin:.45rem .35rem 0 0; padding:.18rem .55rem; border-radius:999px; background:#eef3fc; color:#173f91; font-weight:600; }
  :root[data-theme="dark"] .course-note { background:var(--brand-soft); } :root[data-theme="dark"] .course-card { background:var(--surface); border-color:var(--line); box-shadow:0 8px 20px rgba(0,0,0,.18); } :root[data-theme="dark"] .course-meta { color:var(--muted); } :root[data-theme="dark"] .course-badge { background:var(--brand-soft); color:var(--brand); } @media (max-width:600px) { .course-grid { grid-template-columns:1fr; } }
</style>

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
