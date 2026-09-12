# SupportLens LLM-as-Judge Evaluation Rubric

This file defines the scoring anchors for the pointwise LLM-as-judge evaluation across three separate dimensions on a 1-4 scale.

---

## Groundedness
1: Reply contradicts the retrieved evidence, or invents a specific policy, fact, discount, refund amount, or promise not present anywhere in the retrieved evidence.
2: Reply is generic and could apply to almost any brand or situation; it neither draws on nor contradicts the retrieved evidence — it simply does not engage with the historical pattern shown.
3: Reply's general direction or action matches the pattern in the retrieved evidence (e.g. asks for account details in DM when evidence shows the brand typically does this for similar issues), but omits or alters specific details present in the evidence.
4: Reply's specific action or diagnostic step is directly traceable to a step or fact stated in the retrieved evidence (e.g. the same diagnostic sequence — checking router light color — that evidence shows the brand uses for similar issues).

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
3: Reply matches Verizon's typical short, polite, action-oriented register, but is missing small stylistic markers real agents use (e.g. an empathetic opener, or an implicit invitation to continue the conversation).
4: Reply is indistinguishable in tone, length, and structure from genuine Verizon support replies — concise, polite acknowledgment plus a specific action, with an implicit invitation to continue.
