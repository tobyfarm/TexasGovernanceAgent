{#-
  SAMCO-format line-of-questioning template (Jinja2).
  Consumed by skills.output_formatter.render with an AnalysisResult dict
  where output_mode == "SAMCO_LOQ".

  Reference structure (see agents/AGENT_F.md §"SAMCO-format line-of-questioning"):
    1. Header block — "Line of Questioning: <target>" with meeting context
    2. Executive Summary — prose paragraph framing the governance concern
    3. Historical Precedent (optional) — prior-pattern documentation
    4. Documented Timeline of Events — dated chronology
    5. Legal & Governance Framework — authorities with quoted text
    6. Line of Questioning — table: #, question, (internal) strategic purpose
    7. Suggested Closing Statement — prose for the trustee to read aloud
    8. Key Evidence References — documents to bring
    9. Citation Verification Summary — every authority + verification note
   10. Read-Aloud Statement (Short Version) — condensed deliverable

  Recommended Jinja2 env flags: trim_blocks=True, lstrip_blocks=True.
  Same spacing conventions as brock_full.md — avoid inline `{% if %}` on
  content lines; use ternaries inside `{{ … }}` instead.
-#}
**{{ meeting_metadata.district_name_upper }}**

Line of Questioning: {{ loq_target }}

{{ meeting_metadata.meeting_type }}  |  {{ meeting_metadata.meeting_date }}  |  {{ meeting_metadata.meeting_time }}  |  {{ meeting_metadata.location }}

Prepared for: Trustee {{ meeting_metadata.trustee_name }}

# **Executive Summary**

{{ executive_concern }}
{% if historical_precedent %}

# **Historical Precedent**

{{ historical_precedent }}
{% endif %}

# **Documented Timeline of Events**
{% for entry in timeline %}

{{ loop.index }}. **{{ entry.date }}** — {{ entry.event }}
{% endfor %}

# **Legal & Governance Framework**
{% for authority in legal_framework %}

## **{{ authority.authority }}**

> {{ authority.quote }}

{{ authority.application }}
{% endfor %}

# **Line of Questioning**

| # | Question | Strategic Purpose (internal) |
| :---- | :---- | :---- |
{% for q in questions -%}
| **{{ q.n }}** | *{{ q.question }}* | {{ q.purpose }} |
{% endfor %}

# **Suggested Closing Statement**

{{ closing_statement }}

# **Key Evidence References**
{% for doc in evidence_references %}

- {{ doc }}
{% endfor %}

# **Citation Verification Summary**

| Authority | Verified | Note |
| :---- | :---- | :---- |
{% for c in citation_verification -%}
| {{ c.authority }} | {{ "Yes" if c.verified else "**NO**" }} | {{ c.note }} |
{% endfor %}

# **Read-Aloud Statement (Short Version)**

{{ short_read_aloud }}

---

Respectfully,

Trustee {{ meeting_metadata.trustee_name }}

{{ meeting_metadata.district_name_upper }}
