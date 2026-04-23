"""Dummy AnalysisResult fixture for exercising the renderer.

Shape mirrors agent/types.py from Agent A (agents/AGENT_A.md). This is NOT a
hand-written pre-read — it is enough structured content to validate that the
template hits every branch (exec summary table, items with/without key_data,
all three flag severities, continuous question numbering, prep checklist).

For the real acceptance test, compare against examples/brock_april_13_2026_prereadhand.md.
"""

from datetime import datetime, timezone

BROCK_APRIL_13_DUMMY: dict = {
    "source_pdf": "examples/brock_april_13_2026.pdf",
    "generated_at": datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc).isoformat(),
    "output_mode": "BROCK_FULL",
    "meeting_metadata": {
        "district_name_upper": "BROCK ISD",
        "meeting_type": "Regular Meeting",
        "meeting_date": "April 13, 2026",
        "meeting_time": "6:00 PM",
        "location": "BHS Cafeteria",
        "trustee_name": "Toby Farmer",
        "page_count": 166,
    },
    "executive_summary_table": [
        {
            "item_title": "Bond Series 2026",
            "key_finding": (
                "Restructuring (NOT savings). Up to $5M gross cost to hold I&S at $0.50. "
                "Debt extends to 2048. $32.2M in hold harmless."
            ),
            "risk_level": "HIGH",
        },
        {
            "item_title": "Budget Workshop",
            "key_finding": (
                "Flat enrollment (2,042 RADA). HB2 brings $1.18M restricted funds already "
                "committed to salary. Taxable value growth slowing (3.96%)."
            ),
            "risk_level": "HIGH",
        },
        {
            "item_title": "Balanced Scorecard",
            "key_finding": (
                "MOY follow-up to March 9. BHS Algebra I Predicted Growth dropped 81→62 vs "
                "85 annual goal (biggest pacing miss). BJH 8th hit 90 Reading goal at MOY."
            ),
            "risk_level": "MEDIUM",
        },
        {
            "item_title": "Bus Purchase",
            "key_finding": (
                "$325K for 2 buses; $205K TERP grant offsets. Net cost $119K. Tariff risk "
                "flagged by vendor. Quote expires 5/1/26."
            ),
            "risk_level": "LOW",
        },
    ],
    "items": [
        {
            "item": {
                "item_id": "K",
                "title": "Closed Session (TGC 551.071-551.087)",
                "pages": [1, 2],
                "item_type": "CLOSED_SESSION",
                "attachments": [],
            },
            "summary": (
                "The agenda posts closed session under a BLANKET citation: 'Pursuant to Texas "
                "Government Code, Sections 551.071 through 551.087.' This covers ALL closed "
                "session exceptions in TOMA, including personnel (551.074), real property "
                "(551.072), attorney consultation (551.071), and security (551.076)."
            ),
            "key_data": "",
            "legal_framework": (
                "Under TOMA (TGC Chapter 551), a governmental body may conduct closed session "
                "ONLY under the specific exceptions listed in the statute. The presiding officer "
                "must publicly announce, on the record, the specific section(s) of TGC Chapter "
                "551 that authorize the closed session (TGC §551.101). A certified agenda and "
                "audio recording must be maintained for at least 2 years (TGC §551.103). "
                "The board may NOT vote or take final action in closed session; all votes must "
                "occur after reconvening in open session (TGC §551.102)."
            ),
            "flags": [
                {
                    "severity": "WATCH",
                    "pattern_id": "blanket_closed_session_citation",
                    "summary": (
                        "The blanket citation (551.071-551.087) gives the board maximum "
                        "flexibility but also means almost ANY topic could potentially be "
                        "discussed in closed session."
                    ),
                    "detail": (
                        "As a governance practice, the board president should specify which "
                        "exceptions actually apply before entering. Watch for this."
                    ),
                    "citations": ["TGC §551.101"],
                },
                {
                    "severity": "RED_FLAG",
                    "pattern_id": "personnel_exception_scope",
                    "summary": (
                        "TGC 551.074 (personnel) does NOT authorize discussing general "
                        "employment policy, salary schedules, or working conditions."
                    ),
                    "detail": (
                        "It covers SPECIFIC individuals by name/position only. If the "
                        "discussion veers into general policy, it should be in open session."
                    ),
                    "citations": ["TGC §551.074"],
                },
            ],
            "questions": [
                "Will the board president state the SPECIFIC TGC sections (not just the blanket range) before entering closed session?",
                "Is the certified agenda and audio recording being maintained as required by TGC §551.103?",
                "Which specific exceptions are anticipated tonight? Personnel (551.074) related to the teacher contracts? Real property (551.072)? Litigation (551.071)?",
                "If the closed session involves personnel evaluations, have the affected employees been notified of their right to request a public hearing under TGC §551.074(b)?",
            ],
            "citations": [],
        },
        {
            "item": {
                "item_id": "4C",
                "title": "Revenue & Expenditure Reports (pp. 30-31)",
                "pages": [30, 31],
                "item_type": "CONSENT",
                "attachments": ["Revenue to Budget table", "Expenditures to Budget table"],
            },
            "summary": (
                "Routine revenue and expenditure report against budget across four funds: "
                "General Fund (199), National Breakfast/Lunch (240), Debt Service (513), and "
                "2023 Bond Fund (693). The Debt Service and Bond Fund figures warrant attention."
            ),
            "key_data": (
                "Revenue to Budget (p. 30):\n\n"
                "| Fund | Budget | Realized to Date | % Realized |\n"
                "| :---- | :---- | :---- | :---- |\n"
                "| **199/6 General Fund** | $24,539,083 | $17,581,495 | 71.65% |\n"
                "| **513/6 Debt Service** | $7,250,000 | $8,679,823 | **119.72%** |\n"
                "| **693/6 2023 Bond Fund** | $463,398 | $598,478 | 129.15% |\n\n"
                "Expenditures to Budget (p. 31):\n\n"
                "| Fund | Budget | Expended + Encumb. | % Expended |\n"
                "| :---- | :---- | :---- | :---- |\n"
                "| **199/6 General Fund** | $24,539,083 | $16,627,979 | 65.83% |\n"
                "| **513/6 Debt Service** | $8,522,500 | $8,515,594 | **99.92%** |\n"
                "| **693/6 2023 Bond Fund** | $24,803,598 | $13,034,426 | 52.55% |"
            ),
            "legal_framework": "",
            "flags": [
                {
                    "severity": "WATCH",
                    "pattern_id": "revenue_pacing",
                    "summary": (
                        "General Fund revenue at 71.65% realized with ~58% of the fiscal year "
                        "elapsed (through March) looks healthy."
                    ),
                    "detail": (
                        "Property tax collections are seasonal — most are received Oct–Jan. The "
                        "remaining ~$7M in unrealized revenue will come primarily from state "
                        "funding in the spring."
                    ),
                    "citations": [],
                },
                {
                    "severity": "POSITIVE",
                    "pattern_id": "debt_service_over_collection",
                    "summary": (
                        "Debt Service revenue at 119.72% — the district has OVER-COLLECTED "
                        "relative to budget ($8.68M collected vs. $7.25M budgeted)."
                    ),
                    "detail": (
                        "This suggests strong tax collections on the I&S side. However, "
                        "expenditures are at 99.92% ($8.52M of $8.52M budget spent). The net "
                        "current-year position in the Debt Service fund is roughly $164K positive."
                    ),
                    "citations": [],
                },
                {
                    "severity": "RED_FLAG",
                    "pattern_id": "debt_service_reserve_thin",
                    "summary": (
                        "Debt Service at 99.92% expended means nearly all budgeted bond payments "
                        "have been made for the year."
                    ),
                    "detail": (
                        "Combined with the Samco estimate of $389,750 I&S Fund Balance for "
                        "2025/26, the debt service fund has minimal reserves heading into the "
                        "refunding discussion."
                    ),
                    "citations": [],
                },
            ],
            "questions": [
                "With Debt Service at 99.92% expended, what is the current I&S fund balance? The Samco report shows $794,653 for 2024/25 — is that still accurate?",
                "General Fund expenditures at 67.7% including encumbrances — are we tracking to end the year within budget?",
                "What is the projected General Fund balance at year-end?",
            ],
            "citations": [],
        },
        {
            "item": {
                "item_id": "5",
                "title": "Budget Workshop #1 (pp. 47-68)",
                "pages": [47, 68],
                "item_type": "DISCUSSION",
                "attachments": ["Enrollment slide", "HB2 funding impact", "CFO risk slide"],
            },
            # Complex item: summary carries its own h2 sub-headings. The
            # template detects this and skips the "## What Is Happening" scaffold.
            "summary": (
                "**Presented by:** Lance Rainey, CFO\n\n"
                "**Type:** Discussion Item — No vote required (Workshop 1 of 3)\n\n"
                "**Budget Timeline:** April = Intro/Overview | May = Compensation Direction | "
                "June = Budget Adoption | Aug/Sept = Tax Rate Adoption\n\n"
                "## **Enrollment Trend: The Story in the Numbers (p. 51)**\n\n"
                "This is the most important slide in the entire presentation. The growth era "
                "at Brock ISD is over. RADA has now declined for TWO consecutive years (-13, "
                "then -1). Since M&O funding is driven by ADA, this directly reduces state "
                "revenue.\n\n"
                "## **CFO's Own Risk Assessment (p. 66)**\n\n"
                "Lance Rainey's presentation explicitly identifies three key financial risks: "
                "(1) Enrollment flattening/declining — funded solely on ADA for M&O; (2) "
                "Legislative Uncertainty — HB2 funding could change; (3) Increased Fixed Costs "
                "— insurance, utilities, maintenance on the new building are unavoidable."
            ),
            "key_data": "",
            "legal_framework": "",
            "flags": [
                {
                    "severity": "RED_FLAG",
                    "pattern_id": "flat_enrollment_revenue_exposure",
                    "summary": (
                        "RADA has declined for TWO consecutive years (-13, then -1). "
                        "Enrollment is down -3 this year."
                    ),
                    "detail": (
                        "The district went from adding 237 RADA in 2021-22 to losing students. "
                        "Since M&O funding is driven by ADA, this directly reduces state "
                        "revenue. The 2023 bond and new multipurpose center were built for a "
                        "growth trajectory that has stalled."
                    ),
                    "citations": [],
                },
                {
                    "severity": "RED_FLAG",
                    "pattern_id": "hb2_restricted_allotment_commitment",
                    "summary": (
                        "The $1.18M in restricted salary funds is ALREADY COMMITTED."
                    ),
                    "detail": (
                        "If HB2 changes or sunsets in the next legislative session, the "
                        "district will have structural salary obligations without the revenue "
                        "to cover them."
                    ),
                    "citations": [],
                },
            ],
            "questions": [
                "RADA has declined for two consecutive years. What is the demographic projection for the next 3-5 years?",
                "If HB2 restricted allotments ($1.18M) change or sunset, what is the contingency plan?",
            ],
            "citations": [],
        },
        {
            "item": {
                "item_id": "7",
                "title": "Bond Series 2026 Parameter Order (pp. 87-127)",
                "pages": [87, 127],
                "item_type": "ACTION",
                "attachments": ["Parameter Order", "Samco Capital Markets analysis"],
            },
            "summary": (
                "**This is a DEBT RESTRUCTURING, not a savings refunding.** The Samco analysis "
                "shows ZERO debt service savings. The purpose is to hold the I&S tax rate at "
                "$0.50 by extending and restructuring existing debt. The district will pay an "
                "estimated $32.2 million in hold harmless costs and the total net debt service "
                "is $164.4 million. The parameter order authorizes up to 6.00% true interest "
                "cost, final maturity August 15, 2048, with delegation to a Pricing Officer."
            ),
            "key_data": (
                "| Series | Outstanding | Final Maturity | PSF Backed? |\n"
                "| :---- | :---- | :---- | :---- |\n"
                "| Series 2015 Refunding | $11,788,000 | 2035 | Yes |\n"
                "| Series 2016 Refunding | $12,611,550 | 2031 | Yes |\n"
                "| Series 2017 Building | $21,323,663 | 2042 | Yes |\n"
                "| Series 2020 Building & Ref. | $40,172,900 | 2045 | Yes |\n"
                "| Series 2023 Building | **$104,214,000** | 2048 | Yes |\n"
                "| **TOTAL OUTSTANDING** | **$190,110,113** | Through 2048 | All PSF |"
            ),
            "legal_framework": (
                "**TEC §45.004** specifically authorizes school districts to issue refunding "
                "bonds. Refunding bonds must be submitted to the Texas Attorney General for "
                "examination. **TGC Chapter 1207** provides the statewide framework: refunding "
                "bonds do NOT require a voter election, and maturity cannot exceed 40 years from "
                "issuance. **TGC Chapter 1371** allows the board to delegate pricing authority "
                "to a Pricing Officer within defined parameters — meaning the board will NOT "
                "see final pricing terms before execution. **TEC §§45.051–45.063** (PSF "
                "Guarantee Program) requires the district to comply with all PSF requirements "
                "including timely debt service payments; default allows the Comptroller to "
                "withhold state funds (TEC §45.061). **SEC Rule 15c2-12** requires the district "
                "to provide annual financial reports to the MSRB within 6 months of fiscal "
                "year end. Non-compliance is a securities law violation."
            ),
            "flags": [
                {
                    "severity": "RED_FLAG",
                    "pattern_id": "hold_harmless_dependency",
                    "summary": (
                        "The hold harmless amount of $32.2M is massive. This represents the "
                        "cumulative cost of keeping the I&S rate at $0.50 while extending debt."
                    ),
                    "detail": (
                        "Hold Harmless is a legislative construct created by HB3 (2019) and "
                        "modified by HB2 (2023). There is no constitutional guarantee. One-fifth "
                        "of projected debt service depends on this payment stream continuing for "
                        "22 years."
                    ),
                    "citations": [],
                },
                {
                    "severity": "RED_FLAG",
                    "pattern_id": "i_and_s_fund_depletion",
                    "summary": (
                        "The I&S Fund Balance estimate of $389,750 for 2025/26 represents "
                        "approximately 4% of annual debt service ($9.2M) — roughly 15 days of "
                        "coverage."
                    ),
                    "detail": (
                        "The fund has declined 80% in three years, and the refunding plan draws "
                        "another $2.03M from it over the next four years. After that, the I&S "
                        "fund balance is effectively zero."
                    ),
                    "citations": [],
                },
                {
                    "severity": "WATCH",
                    "pattern_id": "cab_authorization",
                    "summary": (
                        "The parameter order (Section 3(c)) authorizes Capital Appreciation "
                        "Bonds (CABs)."
                    ),
                    "detail": (
                        "CABs pay zero interest during the bond life and compound interest to "
                        "maturity — total cost can be dramatically higher than current interest "
                        "bonds. While there is no indication Samco plans to use CABs, the "
                        "authorization exists. Ask whether CABs are contemplated and, if so, "
                        "what the total compounded cost would be."
                    ),
                    "citations": [],
                },
            ],
            "questions": [
                "The debt service savings column is blank. Can Samco confirm there are ZERO net savings from this refunding? What exactly is the financial benefit to the district?",
                "The hold harmless cost is $32.2M over the bond life. What happens to the district if the Legislature modifies Hold Harmless? Has Samco modeled a scenario where Hold Harmless is reduced by 25% or 50%?",
                "The I&S fund balance has dropped 80% in 3 years ($1.94M to $389K) and the refunding draws another $2M from it. What is the minimum safe I&S fund balance, and when do we hit it?",
                "PCAD certified values arrive April 24. Will the board see this number before the Pricing Officer executes the refunding?",
                "The parameter order authorizes Capital Appreciation Bonds (Section 3(c)). Are CABs contemplated for this refunding? What would the total compounded cost be?",
            ],
            "citations": [],
        },
        {
            "item": {
                "item_id": "11",
                "title": "School Bus Purchase — TERP Grant (pp. 137-166)",
                "pages": [137, 166],
                "item_type": "ACTION",
                "attachments": ["Rush Truck Center Quote #249896", "TCSB Contract 582-26-85344-CB"],
            },
            "summary": (
                "The district is requesting approval to purchase two new 77-passenger propane-"
                "fueled school buses, primarily funded by a TCEQ Texas Emissions Reduction Plan "
                "(TERP) / Texas Clean School Bus Program (TCSB) grant. The buses replace two of "
                "the district's oldest diesel buses (25 and 21 years old). Net cost to district "
                "is $119,325 after a $205,751 grant offset."
            ),
            "key_data": (
                "| Item | Amount |\n"
                "| :---- | :---- |\n"
                "| **Bus Price (each)** | $162,538.00 |\n"
                "| **Total for 2 Buses** | $325,076.00 |\n"
                "| **TERP Grant Award** | -$205,751.00 |\n"
                "| **NET COST TO DISTRICT** | **$119,325.00** |"
            ),
            "legal_framework": (
                "**TEC §44.031** (Competitive Bidding) sets a $20,000 threshold for school bus "
                "purchases specifically (§44.031(a)(5)); the Buy Board cooperative purchasing "
                "program (Contract 722-23) satisfies §44.031(a)(4) as an approved interlocal "
                "cooperative, exempting the district from the individual bid requirement. "
                "**Texas Health & Safety Code Ch. 390** authorizes TCEQ to administer the Texas "
                "Clean School Bus Program under the broader TERP. The TCSB contract requires "
                "5 years of operation on regular daily routes, annual usage/mileage reporting "
                "to TCEQ, and destruction of the replaced buses per TCEQ specifications "
                "(3-inch hole in engine block or complete crushing). Failure to comply may "
                "require FULL return of grant funds ($205,751)."
            ),
            "flags": [
                {
                    "severity": "WATCH",
                    "pattern_id": "tariff_risk",
                    "summary": (
                        "Blue Bird reserves the right to implement a tariff surcharge on bus "
                        "sales dependent on tariffs on Mexican, Canadian, and/or Chinese imports."
                    ),
                    "detail": (
                        "Rush also notes pricing is 'subject to adjustment at any time' for "
                        "supply chain issues. The quote expires 5/1/2026 — board should act "
                        "promptly."
                    ),
                    "citations": [],
                },
                {
                    "severity": "POSITIVE",
                    "pattern_id": "grant_leverage",
                    "summary": "Grant covers 63% of total cost.",
                    "detail": (
                        "Replacing 21–25 year old diesel buses with propane reduces emissions "
                        "and maintenance costs. The old buses with 2000–2004 engines are well "
                        "past recommended replacement age."
                    ),
                    "citations": [],
                },
            ],
            "questions": [
                "The quote expires May 1, 2026, and delivery is 180-250 days. If we approve tonight, what is the realistic delivery date?",
                "The tariff surcharge language is concerning. Has Rush provided any estimate of potential tariff impact? Could the price increase beyond the TERP grant + $119K?",
                "The TCSB contract requires 5 years of operation. What are the annual reporting requirements and who is responsible for compliance?",
                "Is the $119K district cost budgeted for 2026-27, or does it need a separate budget amendment?",
            ],
            "citations": [],
        },
    ],
    "prep_checklist": [
        "**1. Bond Refunding (HIGH priority):** Understand that this is restructuring at a cost, not savings. Press Samco on the hold harmless costs and what happens if taxable value growth slows.",
        "**2. Budget Workshop (HIGH priority):** Focus on the implications of flat enrollment, decelerating tax base growth, and $1.18M in restricted salary commitments. Ask about fund balance trajectory.",
        "**3. Balanced Scorecard (MEDIUM priority):** BHS Algebra I Predicted Growth dropped 81→62 vs the 85 annual goal — the single biggest pacing miss. Demand a specific 6-week intervention plan before STAAR.",
        "**4. Bus Purchase (LOW risk, time-sensitive):** Good use of grant dollars. Watch the tariff language. Quote expires 5/1.",
        "**5. Teacher Contracts (LOW risk):** Routine for 3 probationary teachers. Confirm what subjects they teach relative to scorecard concerns.",
        "**6. TIA (LOW risk):** Pass-through only, but consider whether this should be pulled from consent for first-time discussion.",
        "**7. Fund 491 Amendment (LOW risk):** Straightforward $15K increase. Ask if this is sufficient to finish the year.",
    ],
}


AGENT_A_SHAPED_DUMMY: dict = {
    # Mirror of what Agent A's analyze_pdf_stream() actually emits today:
    #   - meeting_metadata is {source, run_id} only
    #   - executive_summary_table rows use the Agent A shape
    #     (item_id, title, type, pages, risk) — NOT the template shape
    #   - prep_checklist is []
    # The renderer's _normalize() adapter is expected to turn this into
    # template-shape data at render time.
    "source_pdf": "examples/brock_april_13_2026.pdf",
    "generated_at": datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc).isoformat(),
    "output_mode": "BROCK_FULL",
    "meeting_metadata": {
        "source": "brock_april_13_2026.pdf",
        "run_id": "abc123def456",
    },
    "executive_summary_table": [
        {
            "item_id": "K",
            "title": "Closed Session (TGC 551.071-551.087)",
            "type": "CLOSED_SESSION",
            "pages": "1-2",
            "risk": "RED_FLAG",
        },
        {
            "item_id": "4C",
            "title": "Revenue & Expenditure Reports (pp. 30-31)",
            "type": "CONSENT",
            "pages": "30-31",
            "risk": "RED_FLAG",
        },
        {
            "item_id": "7",
            "title": "Bond Series 2026 Parameter Order (pp. 87-127)",
            "type": "ACTION",
            "pages": "87-127",
            "risk": "RED_FLAG",
        },
        {
            "item_id": "11",
            "title": "School Bus Purchase — TERP Grant (pp. 137-166)",
            "type": "ACTION",
            "pages": "137-166",
            "risk": "WATCH",
        },
    ],
    # Items share structure with BROCK_APRIL_13_DUMMY.items
    "items": BROCK_APRIL_13_DUMMY["items"],
    "prep_checklist": [],
}


SAMCO_LOQ_DUMMY: dict = {
    "source_pdf": "examples/brock_april_13_2026.pdf",
    "generated_at": datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc).isoformat(),
    "output_mode": "SAMCO_LOQ",
    "meeting_metadata": {
        "district_name_upper": "BROCK ISD",
        "meeting_type": "Regular Meeting",
        "meeting_date": "April 13, 2026",
        "meeting_time": "6:00 PM",
        "location": "BHS Cafeteria",
        "trustee_name": "Toby Farmer",
        "page_count": 166,
    },
    "loq_target": "Samco Capital Markets — Bond Series 2026 Parameter Order",
    "executive_concern": (
        "The board is being asked to approve a bond parameter order that the cover sheet "
        "frames as a routine refunding. After reviewing the Samco analysis in full, the "
        "debt service savings column is blank — this is a DEBT RESTRUCTURING, not a "
        "savings refunding. The district will pay an estimated $32.2M in hold harmless "
        "costs over 22 years to hold the I&S rate at $0.50. The question tonight is not "
        "whether to refinance at a better rate. It is whether the board understands what "
        "the district is paying to manage its tax rate, and whether Samco is presenting "
        "the full picture."
    ),
    "historical_precedent": (
        "This is the same authorization the board passed in May 2025. The cover sheet "
        "explicitly states: 'This is the same action we took last year in May in the "
        "event we may need to refund/restructure our bond payments.' A healthy debt "
        "structure does not require annual parameter order authorizations. The recurring "
        "pattern suggests an ongoing structural mismatch between debt service costs and "
        "the I&S rate that the board has not yet been briefed on as a multi-year strategy."
    ),
    "timeline": [
        {"date": "May 2025", "event": "Board adopted prior parameter order (now expiring end of April 2026)."},
        {"date": "Feb 16, 2026", "event": "TEA SOF Release #7-HB2-02_16_26 confirms HB2 restricted allotments committed to salary."},
        {"date": "April 7, 2026", "event": "April 13 agenda posted 3:00 PM — satisfies TOMA 72-hour window (TGC §551.043)."},
        {"date": "April 13, 2026", "event": "Board asked to approve parameter order with 1-year delegation to Pricing Officer."},
        {"date": "April 24, 2026", "event": "PCAD releases preliminary 2026/27 certified taxable values (per Samco schedule of events, p. 127)."},
        {"date": "April 13, 2027", "event": "Delegation authority expires. If unused, new parameter order required."},
    ],
    "legal_framework": [
        {
            "authority": "TEC §45.004 — Refunding Bonds",
            "quote": (
                "The governing body of a school district may issue refunding bonds... and "
                "shall submit the refunding bonds to the attorney general for examination "
                "as provided by Chapter 1202, Government Code."
            ),
            "application": (
                "Refunding bonds do not require voter election, but they DO require AG "
                "approval before becoming valid and binding."
            ),
        },
        {
            "authority": "TGC Chapter 1371 — Public Improvement Obligations",
            "quote": (
                "Notwithstanding any other provision of this chapter, this chapter is "
                "self-sufficient authority for the issuance of obligations."
            ),
            "application": (
                "Chapter 1371 is the statutory basis for a 'parameter order' delegating "
                "pricing authority to an officer. Delegation is lawful — but it means the "
                "board does NOT see the final pricing terms before execution. Any "
                "guardrails must be built into the parameters set tonight."
            ),
        },
        {
            "authority": "SEC Rule 15c2-12 — Continuing Disclosure",
            "quote": (
                "The Issuer shall provide... annual financial information and operating "
                "data... to the Municipal Securities Rulemaking Board."
            ),
            "application": (
                "Non-compliance with continuing disclosure obligations is a securities "
                "law violation. Section 14 of the parameter order commits the district to "
                "MSRB reporting within 6 months of fiscal year end."
            ),
        },
    ],
    "questions": [
        {
            "n": 1,
            "question": (
                "The debt service savings column in the Samco analysis is blank. Can you "
                "confirm on the record that this refunding produces ZERO net debt service "
                "savings?"
            ),
            "purpose": (
                "Force Samco to state publicly that this is restructuring, not savings. "
                "Reframes the vote for the rest of the board."
            ),
        },
        {
            "n": 2,
            "question": (
                "The analysis assumes $32.2M in hold harmless payments from the state "
                "over 22 years. Has Samco modeled what happens to the I&S rate if the "
                "90th Legislature reduces hold harmless by 25% or 50%?"
            ),
            "purpose": (
                "Surface legislative risk. Establish on the record that the $0.50 rate "
                "depends on a legislative construct, not a constitutional guarantee."
            ),
        },
        {
            "n": 3,
            "question": (
                "The I&S fund balance is estimated at $389,750 for 2025/26 — roughly 4% "
                "of annual debt service. The refunding plan draws another $2M from it "
                "over four years. What is the minimum safe I&S fund balance, and when "
                "does the district hit it?"
            ),
            "purpose": (
                "Make the reserve depletion a part of the public record. Creates the "
                "fact pattern the board will need if a future bad tax-collection year "
                "forces a rate increase."
            ),
        },
        {
            "n": 4,
            "question": (
                "The parameter order (Section 3(c)) authorizes Capital Appreciation "
                "Bonds. Are CABs contemplated for this refunding? If so, what is the "
                "total compounded cost compared to current-interest bonds?"
            ),
            "purpose": (
                "Close the CAB door explicitly. The board should not authorize a "
                "mechanism that can dramatically increase total cost without a specific "
                "on-record rationale."
            ),
        },
        {
            "n": 5,
            "question": (
                "PCAD certified values arrive April 24 — eleven days from now. Can the "
                "Pricing Officer be instructed to NOT execute until the board has "
                "reviewed the certified values against the model?"
            ),
            "purpose": (
                "Build a board-level checkpoint between passing the parameter order and "
                "execution. Preserves trustee oversight inside a delegated process."
            ),
        },
    ],
    "closing_statement": (
        "Before we vote, I want to name what this action is and is not. This is a debt "
        "restructuring, not a savings refunding — the savings column is blank, and the "
        "district will pay an estimated $32.2 million in hold harmless costs to hold the "
        "I&S rate at $0.50. That is the price of tax rate management, and it depends on "
        "a legislative program that has already changed twice in seven years. I am not "
        "opposed to the mechanism. I am opposed to approving it without the board having "
        "a clear-eyed, on-record understanding of what we are buying and what we are "
        "risking. I am asking Samco and the administration to answer these questions "
        "tonight, and I am asking my fellow trustees to hold the PCAD checkpoint before "
        "execution."
    ),
    "evidence_references": [
        "Bond Series 2026 Parameter Order (pp. 87–116)",
        "Samco Capital Markets preliminary analysis (pp. 118–127)",
        "TEA SOF Release #7-HB2-02_16_26 (cited in budget workshop, p. 62)",
        "Brock ISD Historical Statistics (Samco, p. 123)",
        "May 2025 prior parameter order (expiring end of April 2026)",
    ],
    "citation_verification": [
        {"authority": "TEC §45.004", "verified": True, "note": "Corpus match — school district refunding authority."},
        {"authority": "TGC Chapter 1207", "verified": True, "note": "Corpus match — refunding bond framework."},
        {"authority": "TGC Chapter 1371", "verified": True, "note": "Corpus match — parameter order / delegation."},
        {"authority": "TEC §§45.051–45.063", "verified": True, "note": "Corpus match — PSF Guarantee Program."},
        {"authority": "TEC §45.061", "verified": True, "note": "Corpus match — Comptroller withholding for PSF default."},
        {"authority": "SEC Rule 15c2-12", "verified": True, "note": "Corpus match — continuing disclosure rule."},
        {"authority": "TGC §551.043", "verified": True, "note": "Corpus match — 72-hour posting requirement."},
    ],
    "short_read_aloud": (
        "The Samco analysis shows zero debt service savings. This is a restructuring — "
        "the district will pay an estimated $32.2 million in hold harmless costs over "
        "22 years to keep the I&S rate at $0.50. Before I vote, I want a public "
        "confirmation from Samco that there are no net savings, a commitment that the "
        "Pricing Officer will not execute until after the April 24 PCAD values are "
        "reviewed against the model, and a clear statement on whether Capital "
        "Appreciation Bonds are contemplated under the Section 3(c) authorization. "
        "Without those three, I am not prepared to approve."
    ),
}
