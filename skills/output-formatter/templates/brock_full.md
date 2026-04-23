{#-
  Brock-format full pre-read template (Jinja2).
  Consumed by skills.output_formatter.render with an AnalysisResult dict.
  The acceptance test is examples/brock_april_13_2026_prereadhand.md —
  structure and voice must match that artifact.

  Recommended Jinja2 env flags: trim_blocks=True, lstrip_blocks=True.

  Spacing notes:
    - Each for-loop body emits ONE leading blank line + content line + terminating
      newline. The leading blank provides separation from the prior content AND
      between successive iterations (because the prior iteration's terminating
      newline + this iteration's leading blank = one blank line).
    - `{% endfor %}` and other block tags on their own lines have trim_blocks
      swallow their trailing \n — that is intentional; content lines carry the
      visible newlines.
    - Inline `{% if %}` / `{% endif %}` on a content line must NOT be used —
      trim_blocks swallows the trailing \n of the line and collapses
      paragraph separation. Use ternary expressions inside `{{ … }}` instead
      (see the flag-detail rendering below).

  Continuous question numbering across all items is maintained via the
  `_qn` namespace counter, incremented in a `{% set %}` statement on its
  own line (which trim_blocks handles cleanly).
-#}
**{{ meeting_metadata.district_name_upper }}**

Board Meeting Preparation Report

{{ meeting_metadata.meeting_type }}  |  {{ meeting_metadata.meeting_date }}  |  {{ meeting_metadata.meeting_time }}  |  {{ meeting_metadata.location }}

**Deep Analysis of All Agenda Items and Attachments**

Prepared for: Trustee {{ meeting_metadata.trustee_name }}

{{ meeting_metadata.page_count }}-page board book analyzed  |  All attachments reviewed

# **Executive Summary: Top Issues Tonight**

This report analyzes all {{ meeting_metadata.page_count }} pages of the {{ meeting_metadata.meeting_date }} board book. Below are the critical items requiring your attention, ranked by governance significance.

| Agenda Item | Key Finding | Risk Level |
| :---- | :---- | :---- |
{% for row in executive_summary_table -%}
| **{{ row.item_title }}** | {{ row.key_finding }} | **{{ row.risk_level }}** |
{% endfor %}
{%- set _qn = namespace(n=0) %}
{% for item in items %}

# **Item {{ item.item.item_id }}: {{ item.item.title }}**

## **What Is Happening**

{{ item.summary }}
{% if item.key_data %}

## **Key Data from Attachment**

{{ item.key_data }}
{% endif %}
{% if item.legal_framework %}

## **Legal Framework**

{{ item.legal_framework }}
{% endif %}
{% for flag in item.flags %}

**{{ {'RED_FLAG': 'RED FLAG', 'WATCH': 'WATCH', 'POSITIVE': 'POSITIVE'}[flag.severity] }}:** {{ flag.summary }}{{ (' ' ~ flag.detail) if flag.detail else '' }}
{% endfor %}
{% if item.questions %}

## **Governance Questions**
{% for q in item.questions %}
{% set _qn.n = _qn.n + 1 %}

{{ _qn.n }}. *{{ q }}*
{% endfor %}
{% endif %}
{% endfor %}

# **Meeting Preparation Checklist**

Use this checklist to prepare for effective participation in tonight's meeting:
{% for step in prep_checklist %}

{{ step }}
{% endfor %}

*Remember: Under TOMA, all votes must occur in open session. Confirm closed session is properly posted and recorded.*
