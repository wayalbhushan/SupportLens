# SupportLens Labeling Guide

> **Version:** 1.2  
> **Effective Date:** 2026-09-12  
> **Domain Scope:** Verizon FiOS / Home Services (Broadband, TV, Home Phone) & Brand Reputation.  
> **Upstream Exclusions:** Wireless-only products (cellular data, mobile handsets, SIMs, towers) are filtered out upstream prior to evaluation (measured 4.78% corpus drop).

---

## 1. Scope & Residual Rules

SupportLens evaluates an AI customer support agent on real-world customer inbound tweets.
The assignment's governing thesis is:
> *"Whether you can turn a messy real-world dataset into a working AI system and prove it works. The proof is worth more than the system."*

### Scope Boundaries
1. **FiOS / Home Services Only (Decision 13):** The dataset is scoped to home broadband, television, landlines, set-top equipment, and general brand reputation management. Purely wireless issues (dropped mobile signal, SIM provisioning, handset trade-ins) are filtered prior to sampling.
2. **Residual Wireless Rule:** If a wireless-only message slips past the upstream keyword filter (~0.4% measured residual rate, e.g. an iPhone delivery inquiry with no FiOS mention):
   - **Label:** **`other`**
   - **Flag:** Add `out_of_scope = True` in annotator notes.
   - **Escalation:** Default to `escalate = False` (do not escalate unsupported out-of-scope products to human support queues).
3. **Evaluation Policy for `other`:** Because the agent is deliberately scoped to FiOS/Home, messages classified as `other` are **excluded from LLM judge reply-quality scoring**. Only intent classification accuracy and escalation decisions are evaluated for `other`.

---

## 2. The Stated-Defect Operational Test

> [!IMPORTANT]
> **The Stated-Defect Test (Governing Boundary Rule):**  
> Roughly half the corpus contains venting, hostility, or sarcasm. To prevent subjective "vibes-based" annotation, apply this single mechanical test:
> 
> **Does the message state a specific, currently occurring service defect (a named symptom, product component, error, or quantitative measurement)?**
> - **YES:** Label the appropriate technical or account intent (`connectivity_issue`, `tv_content_access`, `billing_dispute`, `account_access`, `appointment_installation`), **regardless of how angry, hostile, sarcastic, or demanding the tone is.**
> - **NO:** If the message contains only dissatisfaction, insults, hold-time anger, corporate criticism, threats to switch/cancel, or vague claims with no named defect (*"your service is trash"*, *"worst company ever"*), label **`complaint_no_request`**.

---

## 3. Intent Taxonomy Definitions

The taxonomy comprises **7 core intents** plus **`other`**.

```
                         Inbound Message
                                │
        ┌───────────────────────┴───────────────────────┐
  Actionable / Stated Defect                      No Stated Defect
        │                                               │
  ┌─────┴───────────────┐                         ┌─────┴───────────────┐
Technical / Service   Account / Financial     Venting / Criticism    Gratitude
  │                     │                       │                      │
  ├─ connectivity_issue ├─ billing_dispute      └─ complaint_no_request└─ praise_thanks
  ├─ tv_content_access  ├─ account_access
  └─ [other/unsupported]├─ appointment_installation
```

---

### 1. `connectivity_issue`
- **Description:** Complete loss of internet service, network performance degradation, intermittent drops, slow speeds, packet loss, home gateway/router/ONT hardware errors, or physical line defects. (Merged from outage + degradation due to shared tier-1 diagnostic procedures).
- **Inclusions:** Total outages, slow download/upload speeds, Wi-Fi signal range, router blinking lights (red globe, blinking white), ONT power failures, DNS/gateway timeouts, downed lines causing connectivity loss.
- **Exclusions:** Television channel blackouts where broadband is functional (use `tv_content_access`); vague complaints about speed without naming the service or product (use `complaint_no_request`).
- **Default Action:** **Auto-handle** (Triage: query zip status, prompt power cycle, check ONT status).
- **Real Examples:**
  - `[150177]` *"@115722 our WiFi hasn’t been working for almost 24 Hours now. Help."*
  - `[271112]` *"@115722 I hate y’all slow ass cable"* *(Passes Stated-Defect Test: names specific symptom 'slow' and product 'cable/broadband').*

---

### 2. `tv_content_access`
- **Description:** Television programming, video playback, channel subscription disputes, On Demand / Pay-Per-View errors, DVR scheduling/playback, or set-top box video output issues.
- **Inclusions:** Missing channels, contract blackout disputes (e.g. Univision removal), On Demand purchase/playback errors, guide sync failures, secondary TV box connection errors, DVR recording failures.
- **Exclusions:** General internet connectivity loss affecting third-party streaming apps on laptops (use `connectivity_issue`).
- **Default Action:** **Auto-handle** (Triage: STB reboot command, blackout policy explanation, channel activation signal).
- **Real Examples:**
  - `[2452012]` *"First full Sunday with @115722 and Red Zone isn't working...greatttt"*
  - `[2451122]` *"@VerizonSupport none of my widgets are playing sound but fios cable is playing sound. Help please"*

---

### 3. `billing_dispute`
- **Description:** Disputes regarding monthly bill amounts, unexpected rate increases, charges differing from promotional quotes, equipment return charges, unexpected fees, or payment processing errors.
- **Inclusions:** "Why is my bill higher?", double-billing, failure to apply promised discounts, unreturned equipment fee disputes, demand for bill credits, rate discrepancies.
- **Exclusions:** General jokes or venting about bill complexity with no specific charge or dispute named (use `complaint_no_request`, see Near-Miss 7).
- **Default Action:** **Escalate** (Reason: *"Requires secure customer account authentication and CRM billing lookup"*).
- **Real Examples:**
  - `[236125]` *"@VerizonSupport You sent me a flyer with a price which prompted me to purchase your services. When I purchased them, you charged me a different rate."*
  - `[1752143]` *"Lower my cable bill @115722 !"*

---

### 4. `account_access`
- **Description:** Inability to access My Verizon web portal or mobile app, password reset loops, login credential failures, two-factor authentication issues, or account profile management errors.
- **Inclusions:** Password reset failures, "locked out of my account", portal page returning blank/500 errors during login, authentication loop errors.
- **Exclusions:** General complaints about website navigation or chat agents after successful login (use `complaint_no_request`).
- **Default Action:** **Escalate / Secure Auth Flow** (Reason: *"Authentication credentials cannot be exchanged on public Twitter"*).
- **Real Examples:**
  - `[201886]` *"@VerizonSupport Cannot log into https://t.co/28DyKmSRmu or mobile apps"*
  - `[36298]` *"@VerizonSupport is your site & app down again? Trying to pay my bill and am getting a blank screen on Chrome and app won't pass home screen!"*

---

### 5. `appointment_installation`
- **Description:** Existing customer dispatch logistics, technician arrival windows, missed appointments / technician no-shows, service setup visits, or rescheduling dispatches.
- **Inclusions:** "Where is the tech?", rescheduling an install date, technician canceled without notice, setup visit scheduling.
- **Exclusions:** Prospective non-customers asking if FiOS is built out in their neighborhood (use `other`, see Near-Miss 2).
- **Default Action:** **Escalate** (Reason: *"Requires internal technician dispatch schedule lookup and re-routing"*).
- **Real Examples:**
  - `[2619078]` *"@115725 whats going on? Service problems on Long Island & you dont show up for appointments?"*
  - `[1684967]` *"@115722 cant get in touch with anyone via phone or web to reschedule installation today."*

---

### 6. `complaint_no_request`
- **Description:** Emotional venting, hold-time anger, dissatisfaction with corporate practices, sarcasm, or customer service criticism containing **no specific, actionable service defect**.
- **Inclusions:** Insults, threats to cancel/switch without describing a current technical defect, rants about hold times, sarcastic jabs at brand advertising, jokes about bill complexity.
- **Exclusions:** Rants that contain a specific, currently occurring service defect (e.g. "Day 7 no internet" -> `connectivity_issue` + Severity Override; "slow ass cable" -> `connectivity_issue`).
- **Default Action:** **Auto-handle (Acknowledge Only)** (Empathize politely, do not troubleshoot, do not escalate).
- **Real Examples:**
  - `[561334]` *"@115722 is the worst company I have ever dealt with and the service isn't even activated yet"*
  - `[488128]` *"Going to need to go back to school, get my PHD so I can understand my @115725 bill."* *(Fails Stated-Defect Test: joke about bill complexity, no dispute or specific charge).*
  - `[1910518]` *"@VerizonSupport your website sucks ass. inaccurate/inconsistent information, chat agents put you through the wringer for authentication after I logged in... Why so fucking difficult?"* *(Logged in successfully; complaint about agent process).*

---

### 7. `praise_thanks`
- **Description:** Genuine positive feedback, praise for a technician or support agent, appreciation for service recovery, or general brand enthusiasm.
- **Inclusions:** Sincere thank you notes, compliments on fast resolution, praising helpful staff.
- **Exclusions:** **Sarcastic "thanks"** (e.g. "Thanks for ruining my Sunday with no internet" -> classify by defect: `connectivity_issue`).
- **Operational Rule (Prior Negative Experience):** If the message states or implies a prior negative experience (delay, difficulty, past failure) alongside the thanks, and the negative experience is the more prominent element (*"finally got someone that helped me after 3 hours on hold, thanks!"*), classify by the complaint content instead (`complaint_no_request`).
- **Default Action:** **Auto-handle (Acknowledge & Close)** (Polite sign-off, close thread).
- **Real Examples:**
  - `[1347708]` *"@115725 has the best customer service hands down"*
  - `[10480]` *"@VerizonSupport Thank you!"*

---

### 8. `other`
- **Description:** Messages that are completely off-topic, directed primarily at competitors, pre-sales coverage inquiries, third-party promotional broadcasts, or residual wireless leaks.
- **Inclusions:** Inquiries about whether FiOS will expand to an unserved city, chatter directed to `@Ask_Spectrum` mentioning Verizon in passing, unrelated personal status updates, sports broadcast tweets.
- **Exclusions:** Actionable requests regarding existing FiOS services.
- **Default Action:** **Auto-handle / Out of Scope** (Reply quality not scored; only classification and escalation evaluated).
- **Real Examples:**
  - `[464813]` *"@115722 there is a Historic District in Baltimore. Zip code 21205. Homes are being redone, can you offer FIOS?... Gigabit internet FTW!"* *(Pre-sales coverage inquiry).*
  - `[1797104]` *"Game time coming up in one hour! Tune in to #NYIvsNSH: 📺 MSG+2 💻📲 MSG GO... 🎧 88.7FM"* *(Third-party promotional broadcast).*

---

## 4. Escalation Policy & Severity Override

### Default Escalation Mapping
| Intent Class | Default Policy | Default Escalation Reason |
| :--- | :--- | :--- |
| `connectivity_issue` | **Auto-handle** | Public troubleshooting script available |
| `tv_content_access` | **Auto-handle** | Public troubleshooting script available |
| `billing_dispute` | **Escalate** | Account authentication & billing ledger access required |
| `account_access` | **Escalate** | Secure credential handling required |
| `appointment_installation` | **Escalate** | Dispatch calendar & tech routing required |
| `complaint_no_request` | **Auto-handle** | Acknowledge only; no actionable resolution path |
| `praise_thanks` | **Auto-handle** | Close conversation |
| `other` | **Auto-handle** | Out of scope / unhandled |

---

### Critical: Severity Override Rules
> [!IMPORTANT]
> **Rule 1: Severity overrides the ACTION, never the INTENT.**  
> A high-severity message keeps its underlying intent classification (e.g. `connectivity_issue`), but the escalation decision is flipped to `escalate = True`.
> 
> **Rule 2: Evidence Rule for Severity.**  
> Severity triggers MUST be judged **solely from what the customer explicitly states in the text**. Annotators must **never infer, guess, or assume** severity (e.g., do not assume a medical issue exists unless explicitly named; do not assume an outage is multi-day unless a duration of $\ge 48$ hours is explicitly stated).

Regardless of the default intent mapping (even for `complaint_no_request` or `connectivity_issue`), the agent **MUST ESCALATE IMMEDIATELY** if any of the following explicit triggers are present:

1. **Life Safety / Medical Dependency:**
   - Explicit mentions of medical alert systems (LifeAlert), home dialysis, in-home oxygen, emergency medical dependencies, or emergency services (911 access).
2. **Physical Infrastructure Hazard / Property Damage:**
   - Downed utility wires in roads/driveways, low-hanging wires, snapped telephone poles, smoking or sparking equipment.
3. **Prolonged Complete Outage:**
   - Total service disruption **explicitly stated as lasting $\ge 48$ hours** (e.g. *"Day 3 without internet"*, *"no wifi for 5 days"*).
4. **Legal / Regulatory Escalation Threat:**
   - Formal declarations of filing with the **FCC**, **FTC**, State Public Utility Commission (**PUC**), Better Business Bureau (**BBB**), or retention of legal counsel / lawsuit.
5. **Business-Critical Revenue Stoppage:**
   - Commercial / business customer stating ongoing downtime is actively halting business operations, POS card transactions, or payroll.

---

## 5. Near-Miss Boundaries & Disambiguation

### Near-Miss 1: Sarcastic Praise vs. Sincere Gratitude
- **Text:** *"@115725 You've got great customer service (that's said sarcastically) 20+ minutes on hold and the rep can't solve my issue..."* `[2231552]`
- **Classification:** `complaint_no_request`
- **Rule:** Do not match keywords blindly. Ironic or sarcastic "praise" with no stated technical defect is `complaint_no_request`. If an actionable technical defect is named, classify by the defect.

### Near-Miss 2: Coverage / Availability Inquiry vs. Appointment Installation
- **Text:** *"Will Fios hit the chicago land area? When will fios be in zip 20036?"*
- **Classification:** `other` (Coverage Inquiry)
- **Rule:** `appointment_installation` is strictly reserved for **existing customers** managing dispatches, technician visits, or service orders. Prospective non-customers inquiring about regional network buildout belong in `other`.

### Near-Miss 3: Physical Safety Hazard vs. Normal Connectivity Outage
- **Text:** *"4 hours ago I reported pole broken and WIRES DOWN in my front yard... STILL NO RESPONSE"*
- **Classification:** `connectivity_issue` + **Physical Hazard Severity Override: Escalate**
- **Rule:** The intent remains `connectivity_issue` (infrastructure failure), but triggers the **Physical Hazard Severity Override** to immediately escalate for emergency dispatch.

### Near-Miss 4: Venting with Buried Defect vs. Pure Complaint
- **Text:** *"Day 7 without Internet. @115725 nightmare continues. Elderly mom can't access #LifeAlert. @VerizonSupport what is the problem?"*
- **Classification:** `connectivity_issue` + **Medical / Prolonged Outage Severity Override: Escalate**
- **Rule:** Passes the Stated-Defect Test (named defect: internet outage). Contains explicit medical dependency and multi-day duration. Never mark this `complaint_no_request`.

### Near-Miss 5: Content Dispute vs. Connectivity Outage
- **Text:** *"@VerizonSupport internet works fine but Univision channel 540 is showing black screen with contract notice."*
- **Classification:** `tv_content_access`
- **Rule:** Missing channels, contract blackout notices, or guide sync errors are content access issues, not broadband connection drops.

### Near-Miss 6: Residual Wireless Leak
- **Text:** *"my #iPhoneX orders says Nov 3 but no tracking info"*
- **Classification:** `other`
- **Rule:** Wireless-only product issue that bypassed upstream filtering. Label as `other`, flag `out_of_scope = True` in annotator notes, and set `escalate = False`.

### Near-Miss 7: Joke / Rant About Bill vs. Actionable Billing Dispute
- **Text:** *"Going to need to go back to school, get my PHD so I can understand my @115725 bill."* `[488128]`
- **Classification:** `complaint_no_request`
- **Rule:** Fails the Stated-Defect Test. Venting about bill readability or pricing structure without disputing a specific charge, rate change, or fee belongs in `complaint_no_request`.

---

## 6. Deterministic Tie-Break Hierarchy

When a single message touches multiple areas, apply this exact 4-step sequence:

1. **Severity Override Triggers (Safety / Hazard / Legal / Outage $\ge 48$h):** Always sets `escalate = True`.
2. **Stated-Defect Priority (Actionable Issue > Venting):** If a customer vents emotional frustration and names a specific service defect (*"Your service is trash, my router has a red globe for 3 hours"*), classify by the defect (`connectivity_issue`), NOT the venting.
3. **Authentication / Billing Blocker > Technical Issue:** If a customer cannot troubleshoot technical service because they are blocked by login or account locks (*"Can't log into My Verizon to reset my router"*), classify as `account_access`. Credential access is a hard prerequisite.
4. **Earliest Mentioned Actionable Intent:** If two distinct actionable technical issues appear in the same message (*"Router is red and DVR won't record"*), classify by the first mentioned actionable issue (`connectivity_issue`).

---

## 7. Version History

| Version | Date | Changes & Annotations |
| :--- | :--- | :--- |
| **v0.1** | 2026-09-09 | Initial stub. |
| **v1.0** | 2026-09-12 | Initial draft: 7 intents + other, merged `connectivity_issue`, pre-filtered wireless, initial severity override list. |
| **v1.1** | 2026-09-12 | Fixed 4 critical blockers: (1) resolved example-exclusion contradictions in `connectivity_issue`, `billing_dispute`, `account_access`; (2) added mechanical Stated-Defect Operational Test; (3) unified severity behavior (severity flips `escalate`, never changes intent label; fixed Near-Miss 3); (4) added explicit Residual Wireless rule (`other` + `out_of_scope=True`) and Stated-Content-Only Evidence Rule; (5) added `other` reply-quality evaluation exclusion. |
| **v1.2** | 2026-09-12 | **Frozen for Golden Set Labelling.** Added mechanical operational rule for `praise_thanks`: if prior negative experience is stated/implied and prominent, classify by complaint content (`complaint_no_request`). Ready for 200-item labeling. |
