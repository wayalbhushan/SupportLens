# SupportLens LLM-as-Judge Evaluation Rubric

This file defines the scoring anchors for the pointwise LLM-as-judge evaluation across three separate dimensions on a 1-4 scale.

---

## Groundedness
1: Reply contradicts the retrieved evidence, or invents a specific policy, fact, discount, refund amount, or promise not present anywhere in the retrieved evidence.
2: Reply is generic and could apply to almost any brand or situation; it neither draws on nor contradicts the retrieved evidence — it simply does not engage with the historical pattern shown.
3: Reply's action matches the GENERAL PROCEDURE shown in evidence (e.g. asks for the same type of information, follows the same troubleshooting sequence), but does not repeat a specific checkable fact (number, URL, named policy, named timeframe) from evidence.
4: Reply contains a SPECIFIC, CHECKABLE FACT (a phone number, URL, dollar figure, named policy, or named timeframe) that is directly copied or paraphrased from the retrieved evidence.

*Note on Groundedness Boundaries*: Tone, phrasing, or empathetic language matching the brand's voice (e.g. matching greeting style or exclamations like 'Whoa!') does NOT by itself qualify for Score 3 or 4 here — that is scored under Brand Appropriateness instead.

---

## Actionability
1: Reply gives no next step at all — pure acknowledgment or empathy with no action (e.g. "We're sorry to hear that.").
2: Reply gestures at needing more information or action but is vague about what specifically the customer should do (e.g. "let us know more" without stating what "more" means).
3: Reply gives one clear next step, but it is generic across intents (e.g. "please DM us your account details") without engaging with the specific symptom or defect the customer described.
4: Reply gives a specific, actionable step tailored to the exact defect or symptom mentioned in the message (e.g. "please check if the light on your router is red or blinking, and try unplugging it for 30 seconds").

---

## Brand Appropriateness
1: Reply's tone is inappropriate for a public brand support account — hostile or dismissive toward the customer, broken/robotic phrasing, or formality wildly mismatched to the brand's real voice (e.g. overly casual slang, or corporate press-release tone).
2: Reply is understandable but noticeably off in length or tone compared to real Verizon replies (e.g. far longer than any real example, or curt to the point of seeming dismissive).
3: Reply matches Verizon's typical short, polite, action-oriented register, but is missing small stylistic markers real agents use (e.g. an empathetic opener, or an implicit invitation to continue the conversation). Formally correct but 'corporate-polite' replies belong at Score 3.
4: Reply is indistinguishable in tone, length, and structure from genuine Verizon support replies. Real VerizonSupport replies are typically under ~25 words, favor casual empathy openers (e.g. 'Oh no', 'Yikes', 'Whoa!') over formal apology structures (e.g. 'We apologize for the inconvenience'), and avoid corporate vocabulary (e.g. 'exemplary', 'high-quality support you deserve'). Score 4 requires this register.
