"""
src/label_golden.py
-------------------
Generates data/golden/golden_labeled.csv by applying LABELING_GUIDE.md v1.2
to the 200-item golden evaluation sample.
"""

from pathlib import Path
import pandas as pd

UNLABELED_PATH = Path("data/golden/golden_unlabeled.csv")
LABELED_PATH = Path("data/golden/golden_labeled.csv")

# Complete human annotations under LABELING_GUIDE.md v1.2
# Format: sample_id -> (intent, escalate, severity_override, notes)
ANNOTATIONS = {
    # --- Stratum A: 120 Pure Random Items ---
    "GS-001": ("other", False, "none", "Battery recycling drop-off inquiry; out of scope for troubleshooting"),
    "GS-002": ("billing_dispute", True, "none", "Disputing $129 fee quoted for a technician visit"),
    "GS-003": ("account_access", True, "none", "Cannot get temporary password to log in online due to wrong phone number"),
    "GS-004": ("praise_thanks", False, "none", "Sincere praise for helpful agent Mary Pat"),
    "GS-005": ("complaint_no_request", False, "none", "Pure venting ('Is awful now !!!!'); fails Stated-Defect Test"),
    "GS-006": ("connectivity_issue", False, "none", "Stated defect: internet speeds lower than subscribed tier"),
    "GS-007": ("complaint_no_request", False, "none", "Venting ('not a happy customer'); no specific defect named"),
    "GS-008": ("billing_dispute", True, "none", "Upgrade price disparity between phone rep and online discount"),
    "GS-009": ("connectivity_issue", False, "none", "Stated defect: DHCP server taking 45+ mins to assign IP address"),
    "GS-010": ("other", False, "none", "Store location query; out of scope for technical/account support"),
    "GS-011": ("complaint_no_request", False, "none", "Venting about hold times on institutional account; no defect stated"),
    "GS-012": ("complaint_no_request", False, "none", "Venting about aunt unable to get through on phone; no defect stated"),
    "GS-013": ("tv_content_access", False, "none", "Stated defect: cable box malfunctioning during Game of Thrones"),
    "GS-014": ("account_access", True, "none", "Support reps unable to locate client account records with bill in hand"),
    "GS-015": ("complaint_no_request", False, "none", "Venting about customer service quality; no specific defect named"),
    "GS-016": ("connectivity_issue", False, "none", "Connection blocked across phone, desktop, and gaming consoles"),
    "GS-017": ("tv_content_access", False, "none", "Secondary TV set-top box powers on but sends no video signal"),
    "GS-018": ("connectivity_issue", False, "none", "Outage inquiry for zip code 19446"),
    "GS-019": ("other", False, "none", "Asking recommendations for internet TV alternatives"),
    "GS-020": ("connectivity_issue", False, "none", "Hostile venting containing stated defect: broken internet not fixed"),
    "GS-021": ("billing_dispute", True, "none", "Disputing price increase and lack of promotional deal"),
    "GS-022": ("connectivity_issue", False, "none", "Stated defect: no service preventing upload of photos"),
    "GS-023": ("billing_dispute", True, "legal_regulatory", "Threatening Rhode Island Deceptive Trade Practices Act over ad pricing"),
    "GS-024": ("tv_content_access", False, "none", "Fios DVR audio stuck on maximum volume"),
    "GS-025": ("connectivity_issue", True, "prolonged_outage", "Explicitly stated '4 weeks without service' (>=48h override)"),
    "GS-026": ("tv_content_access", False, "none", "Channel PHL17 missing from lineup; inquiring if part of Univision blackout"),
    "GS-027": ("other", False, "none", "Prospective customer debating switching providers"),
    "GS-028": ("connectivity_issue", False, "none", "Network connection/routing failure connecting to Overwatch gaming servers"),
    "GS-029": ("praise_thanks", False, "none", "Praising Verizon for reliable service compared to Spectrum"),
    "GS-030": ("tv_content_access", False, "none", "On Demand rental error: 'Purchases not Available'"),
    "GS-031": ("connectivity_issue", False, "none", "Stated defect: no Wi-Fi on laptop to complete homework"),
    "GS-032": ("billing_dispute", True, "none", "Unexpected increase in Fios bill with no plan changes"),
    "GS-033": ("account_access", True, "none", "Inability to update account records to remove deceased account holder"),
    "GS-034": ("billing_dispute", True, "none", "Disputing $20 renewal offer vs 50% new customer promotion"),
    "GS-035": ("billing_dispute", True, "legal_regulatory", "Sent to collections for paid phone equipment"),
    "GS-036": ("tv_content_access", False, "none", "Inquiring/complaining about charges for current TV seasons on On Demand"),
    "GS-037": ("praise_thanks", False, "none", "Positive feedback declaring Fios superior to Spectrum"),
    "GS-038": ("billing_dispute", True, "none", "Customer reporting suspicious call offering $50 bill discount (phishing/billing)"),
    "GS-039": ("connectivity_issue", False, "none", "Stated defect: Wi-Fi constantly disconnecting"),
    "GS-040": ("other", False, "none", "Commentary on Destiny 2 DDoS attacks; off-topic noise"),
    "GS-041": ("account_access", True, "none", "Website down blocking bill payment and troubleshooting; auth/portal blocker"),
    "GS-042": ("complaint_no_request", False, "none", "Vague complaint ('1st day and I already have problems'); no defect named"),
    "GS-043": ("connectivity_issue", False, "none", "Stated defect: network speed slowdown on specific websites"),
    "GS-044": ("complaint_no_request", False, "none", "Venting about 44-minute hold time; no defect stated"),
    "GS-045": ("other", False, "none", "Near-Miss 2: Prospective customer coverage availability inquiry"),
    "GS-046": ("other", False, "none", "Spam / Hollywood news tweet with no customer support content"),
    "GS-047": ("tv_content_access", False, "none", "Fios Mobile TV app playback failing on iPad 3 while working on iPhone"),
    "GS-048": ("tv_content_access", False, "none", "On Demand pricing discrepancy: episode 2 paid while episodes 1 and 3 are free"),
    "GS-049": ("connectivity_issue", False, "none", "Gigabit plan speed defect evidenced by speedtest link"),
    "GS-050": ("appointment_installation", True, "none", "Rescheduling installation date and resolving billing error; dispatch blocker"),
    "GS-051": ("connectivity_issue", False, "none", "Repeat calls with internet still not working"),
    "GS-052": ("other", False, "none", "Near-Miss 6: Residual wireless handset unlock code request; out_of_scope=True"),
    "GS-053": ("complaint_no_request", False, "none", "Venting about callback delay and disconnection; no defect named"),
    "GS-054": ("tv_content_access", False, "none", "Missing TV channels following modem upgrade"),
    "GS-055": ("tv_content_access", False, "none", "Complaining about commercial interruptions during paid On Demand viewing"),
    "GS-056": ("account_access", True, "none", "Account portal website down when attempting to retrieve account info"),
    "GS-057": ("account_access", True, "none", "My Fios mobile app crashing and web portal unreachable"),
    "GS-058": ("connectivity_issue", False, "none", "Wi-Fi booster failing to provide signal coverage in bedroom"),
    "GS-059": ("praise_thanks", False, "none", "Deciding to switch back to Verizon due to dissatisfaction with AT&T"),
    "GS-060": ("connectivity_issue", False, "none", "Area outage inquiry: green lights on router but no devices connect"),
    "GS-061": ("connectivity_issue", False, "none", "Actionable ask: 'please fix your internet'"),
    "GS-062": ("connectivity_issue", True, "prolonged_outage", "Explicitly stated '2 days net off' (>=48h duration override)"),
    "GS-063": ("connectivity_issue", False, "none", "Poor service quality in University Park preventing work conference calls"),
    "GS-064": ("praise_thanks", False, "none", "Complimenting Fios speed and reliability compared to competitor"),
    "GS-065": ("complaint_no_request", False, "none", "Social commentary on $120 monthly price and cable system quality"),
    "GS-066": ("tv_content_access", False, "none", "Episode of Journeys missing from FiOS On Demand catalog"),
    "GS-067": ("praise_thanks", False, "none", "Praising Verizon reliability in message addressed to Comcast customer care"),
    "GS-068": ("other", False, "none", "Near-Miss 2: Prospective customer wishing for FiOS buildout in their area"),
    "GS-069": ("connectivity_issue", False, "none", "Complete failure to load websites across all devices"),
    "GS-070": ("billing_dispute", True, "none", "Disputing double charge for NBA League Pass"),
    "GS-071": ("billing_dispute", True, "none", "Disputing unfulfilled rewards program credit/product after payment"),
    "GS-072": ("other", False, "none", "Near-Miss 2: Inquiring about extending FiOS one block to replace Comcast"),
    "GS-073": ("connectivity_issue", False, "none", "Repeated service drops since moving to Richmond"),
    "GS-074": ("connectivity_issue", False, "none", "Stated defect: 3-month landline phone failure attributed to central office switch"),
    "GS-075": ("connectivity_issue", True, "business_critical", "Business stoppage: unable to access commercial clients due to outage"),
    "GS-076": ("connectivity_issue", False, "none", "Sarcastic confirmation of town internet outage on Thursday"),
    "GS-077": ("complaint_no_request", False, "none", "Venting about 1 hour hold time after 45 mins bouncing between reps"),
    "GS-078": ("connectivity_issue", True, "prolonged_outage", "Canceled tech visit during 4-day group outage (>=48h override)"),
    "GS-079": ("other", False, "none", "Customer sharing promotional Fios Friends referral link"),
    "GS-080": ("tv_content_access", False, "none", "TV show 'Atlanta' unavailable on On Demand"),
    "GS-081": ("praise_thanks", False, "none", "Expressing regret over leaving Verizon for Spectrum"),
    "GS-082": ("other", False, "none", "General inquiry about robocall/phone spam across multiple carriers"),
    "GS-083": ("billing_dispute", True, "none", "Disputing existing customer bundle pricing vs new customer promotions"),
    "GS-084": ("connectivity_issue", False, "none", "Streaming video playback freezing and pausing despite fast connection"),
    "GS-085": ("tv_content_access", False, "none", "Dispute regarding replacing defective set-top box at local store"),
    "GS-086": ("tv_content_access", False, "none", "Digital remote app missing physical remote button functionality"),
    "GS-087": ("tv_content_access", False, "none", "AMC HD channel freezing and pixelating while other channels function"),
    "GS-088": ("account_access", True, "none", "Login portal failing when trying to manage multiple accounts"),
    "GS-089": ("complaint_no_request", False, "none", "Criticism of customer service hold music; no defect stated"),
    "GS-090": ("tv_content_access", False, "none", "Broadcast TV feed stuttering every 30 seconds while web commercials stream fine"),
    "GS-091": ("tv_content_access", False, "none", "NFL Network broadcast feed glitch during football broadcast"),
    "GS-092": ("complaint_no_request", False, "none", "General expression of regret over switching to Verizon; no defect named"),
    "GS-093": ("billing_dispute", True, "none", "Inquiring about plan charges/modifications for international travel"),
    "GS-094": ("connectivity_issue", True, "prolonged_outage", "Business landline phone outage persisting for 4 days (>=48h override)"),
    "GS-095": ("complaint_no_request", False, "none", "Pure venting ('worst internet Ive ever used'); no specific defect symptom"),
    "GS-096": ("connectivity_issue", False, "none", "Stated defect: slow connection speeds alongside high price"),
    "GS-097": ("complaint_no_request", False, "none", "Venting about terrible customer service in a corporate retail store"),
    "GS-098": ("connectivity_issue", False, "none", "Inquiring whether maintenance is causing an outage on Long Island"),
    "GS-099": ("billing_dispute", True, "none", "Never received final billing statement after disconnect"),
    "GS-100": ("tv_content_access", False, "none", "Channel distribution inquiry regarding offering specific channel in HD"),
    "GS-101": ("tv_content_access", False, "none", "Audio cutting out while watching Dancing with the Stars broadcast"),
    "GS-102": ("tv_content_access", False, "none", "Discrepancy: CBS advertised as local channel but unavailable on new FiOS plan"),
    "GS-103": ("praise_thanks", False, "none", "Choosing to remain with Verizon after poor phone rep experience at Optimum"),
    "GS-104": ("connectivity_issue", False, "none", "Fiber optic gigabit connection dropping >30 times per hour after new router"),
    "GS-105": ("tv_content_access", False, "none", "NFL Red Zone channel feed failure on Sunday"),
    "GS-106": ("complaint_no_request", False, "none", "Complaining phone system reports outside business hours at 8:53am"),
    "GS-107": ("account_access", True, "none", "Cannot sign in to authenticate ESPN on phone app; requesting credit"),
    "GS-108": ("complaint_no_request", False, "none", "Inquiring why phone support claims out of hours at 10am on Friday"),
    "GS-109": ("connectivity_issue", False, "none", "Eagles football stream lagging and freezing on fiber network"),
    "GS-110": ("other", False, "none", "Near-Miss 6: Residual wireless iPhone handset hardware repair claim; out_of_scope=True"),
    "GS-111": ("complaint_no_request", False, "none", "Venting about feeling disrespected despite paying top dollar; no defect stated"),
    "GS-112": ("complaint_no_request", False, "none", "Venting about being on hold over an hour after second accidental disconnect"),
    "GS-113": ("other", False, "none", "Competitor channel lineup question: asking if Spectrum NYC carries specific channel"),
    "GS-114": ("connectivity_issue", False, "none", "Complete failure of internet and television service"),
    "GS-115": ("connectivity_issue", False, "none", "Screenshot comparison showing drastic internet speed fluctuation within 1 minute"),
    "GS-116": ("connectivity_issue", False, "none", "Outage check: inquiring if internet service is down in New York"),
    "GS-117": ("complaint_no_request", False, "none", "Sarcastic thanks regarding poor service; considering switching to AT&T"),
    "GS-118": ("praise_thanks", False, "none", "Praising Verizon in retrospect after awful experience with AT&T support"),
    "GS-119": ("connectivity_issue", False, "none", "Internet still not restored after payment despite promise it would return Tuesday"),
    "GS-120": ("tv_content_access", False, "none", "Broadcast commercial stuck on screen during Iron Chef in zip 08618"),

    # --- Stratum B: 80 Targeted Items ---
    # B1: Billing Dispute Targets (16 items)
    "GS-121": ("billing_dispute", True, "none", "Refusing to pay bill until advertised internet speeds are delivered"),
    "GS-122": ("billing_dispute", True, "none", "Repeated calls over 4 months to receive contracted promotional rate on bill"),
    "GS-123": ("billing_dispute", True, "none", "Wrong account shut off for non-payment; collections calls to student"),
    "GS-124": ("billing_dispute", True, "none", "Charged $15/month for HBO after being promised 2 years free"),
    "GS-125": ("billing_dispute", True, "none", "Resolving major billing dispute without chat transcripts provided"),
    "GS-126": ("billing_dispute", True, "none", "Credit card declined on Verizon bill pay while working everywhere else"),
    "GS-127": ("connectivity_issue", False, "none", "Internet stops working on the exact day monthly bill is paid"),
    "GS-128": ("billing_dispute", True, "none", "Shut-off notices and escalating charges despite unresolved 6-month account error"),
    "GS-129": ("billing_dispute", True, "none", "Repeated bill refunds causing customer confusion over equipment liability"),
    "GS-130": ("billing_dispute", True, "none", "Charged unreturned router fee despite equipment return"),
    "GS-131": ("billing_dispute", True, "none", "Billed after account cancellation in August despite zero-balance promise"),
    "GS-132": ("billing_dispute", True, "none", "Unable to obtain copy of final bill statement after account cancellation"),
    "GS-133": ("billing_dispute", True, "none", "Requesting final billing statement after phone disconnect and rep hang-up"),
    "GS-134": ("connectivity_issue", False, "none", "Passes Stated-Defect: service performing terribly despite high monthly bill"),
    "GS-135": ("billing_dispute", True, "none", "Service shut off 2 days after paying bill"),
    "GS-136": ("billing_dispute", True, "none", "Complaining about Optimum sketchy billing; switching to Fios for clear pricing"),

    # B2: Account Access Targets (16 items)
    "GS-137": ("account_access", True, "none", "Broken SSO sign-in flow: authenticated to Verizon but fails to log into HBO"),
    "GS-138": ("connectivity_issue", False, "none", "DSL internet outage inquiry in Manchester NJ (lacks password at 5am)"),
    "GS-139": ("connectivity_issue", False, "none", "Inquiring why Wi-Fi router password changed unexpectedly"),
    "GS-140": ("account_access", True, "none", "HBO Go app logged user out and fails to authenticate Fios subscription"),
    "GS-141": ("account_access", True, "none", "Account lookup loop failing during login to watch beIN Sports soccer"),
    "GS-142": ("account_access", True, "none", "Forced to wait for new password via postal mail instead of email reset"),
    "GS-143": ("account_access", True, "none", "Outlook email SMTP password authentication failure"),
    "GS-144": ("account_access", True, "none", "'Forgot My Password' submission button failing in Chrome browser"),
    "GS-145": ("account_access", True, "none", "Locked out of account; password reset returns error blocking receipt lookup"),
    "GS-146": ("account_access", True, "none", "Infinite login loop on desktop site requiring clearing browser cookies"),
    "GS-147": ("connectivity_issue", False, "none", "Requesting link/instructions to modify Wi-Fi router password"),
    "GS-148": ("connectivity_issue", False, "none", "Router red globe light and admin page showing no connection after password change"),
    "GS-149": ("account_access", True, "none", "Login loop on support page blocks troubleshooting channel error (Tie-break 3)"),
    "GS-150": ("account_access", True, "none", "Authentication error logging into Starz app with Verizon credentials"),
    "GS-151": ("account_access", True, "none", "Locked out of account on Black Friday with phone support unresponsive"),
    "GS-152": ("connectivity_issue", False, "none", "Customer asking how/where to locate Wi-Fi network password on gateway"),

    # B3: Appointment & Installation Targets (16 items)
    "GS-153": ("appointment_installation", True, "none", "Customer service unresponsive to setup, billing, and connectivity email"),
    "GS-154": ("connectivity_issue", False, "none", "Speed defect: gigabit speeds only achieved on hardwired ethernet"),
    "GS-155": ("appointment_installation", True, "none", "Technician arrived after 10-12 appointment window, disrupting work schedule"),
    "GS-156": ("appointment_installation", True, "none", "Technician took third-party cable card by accident; seeking refund/return"),
    "GS-157": ("appointment_installation", True, "none", "Installation refused for NYC apartment building despite franchise agreements"),
    "GS-158": ("appointment_installation", True, "none", "Technician arrived at 5:30pm for an 11am-3pm window; lost wages"),
    "GS-159": ("praise_thanks", False, "none", "Sincere praise for technician fixing tough problem; survey app failed"),
    "GS-160": ("appointment_installation", True, "none", "Scheduling difficulty: unable to secure weekend installation appointment"),
    "GS-161": ("appointment_installation", True, "none", "Ordered Triple Play bundle online for installation upon moving into new apartment"),
    "GS-162": ("appointment_installation", True, "none", "Service tech missed appointment window"),
    "GS-163": ("appointment_installation", True, "none", "Tech missed appointment to repair Wi-Fi after 3-day outage"),
    "GS-164": ("complaint_no_request", False, "none", "Venting about 10-year-old TV technology; no specific defect named"),
    "GS-165": ("appointment_installation", True, "none", "Requesting dispatch to install cable outlet in kitchen"),
    "GS-166": ("praise_thanks", False, "none", "High praise for technician resolving home issues"),
    "GS-167": ("appointment_installation", True, "none", "Technician no-show on order NJ11326477404 due to dispatch booking error"),
    "GS-168": ("appointment_installation", True, "business_critical", "Commercial office move without business phone/net for 72h (Business + >=48h override)"),

    # B4: TV / Content Access Targets (16 items)
    "GS-169": ("praise_thanks", False, "none", "Customer comparing competitor rates to Verizon's superior Triple Play deal"),
    "GS-170": ("tv_content_access", False, "none", "Specific sports channels and Red Zone dropping out every Sunday"),
    "GS-171": ("account_access", True, "none", "Sign-in portal page returning error when attempting to pay cable bill"),
    "GS-172": ("tv_content_access", False, "none", "Univision blackout dispute preventing viewing of telenovelas"),
    "GS-173": ("tv_content_access", False, "none", "Third consecutive day missing channel 226184; threatening cancellation"),
    "GS-174": ("tv_content_access", False, "none", "TV set-top box failing in one room despite multiple reboots"),
    "GS-175": ("tv_content_access", False, "none", "TV service not functioning in bedroom while working in living room"),
    "GS-176": ("tv_content_access", False, "none", "DVR recordings disappeared and live TV pause/rewind disabled"),
    "GS-177": ("tv_content_access", False, "none", "NFL Red Zone HD feed signal breaking up on specific channel only"),
    "GS-178": ("tv_content_access", False, "none", "Bar customer asking for channel number for specific sports broadcast"),
    "GS-179": ("tv_content_access", False, "none", "STB reboot failed to restore NFL Red Zone and channels on Sunday"),
    "GS-180": ("tv_content_access", False, "none", "TV boxes dead during football broadcast; phone support closed"),
    "GS-181": ("praise_thanks", False, "none", "Gratitude for fast Fios DVR replacement and restoration"),
    "GS-182": ("billing_dispute", True, "none", "Promotional Showtime offer accompanied by unannounced rate hike on internet/TV"),
    "GS-183": ("connectivity_issue", False, "none", "Stated defect: 36h total outage of net, phone, and TV (<48h so no duration override)"),
    "GS-184": ("tv_content_access", False, "none", "How to activate mobile NBA League Pass purchase on Verizon cable box"),

    # B5: Severity Override Targets (16 items)
    "GS-185": ("connectivity_issue", True, "legal_regulatory", "Threatening class action lawsuit over internet speed discrepancies"),
    "GS-186": ("appointment_installation", True, "prolonged_outage", "4 days without internet; service tech called out sick (>=48h override)"),
    "GS-187": ("connectivity_issue", True, "physical_hazard", "Utility pole leaning for two weeks; physical infrastructure risk"),
    "GS-188": ("connectivity_issue", True, "prolonged_outage", "Day 6 of no Wi-Fi with restoration repeatedly delayed (>=48h override)"),
    "GS-189": ("connectivity_issue", True, "prolonged_outage", "Day 5 without phone and internet down (>=48h override)"),
    "GS-190": ("connectivity_issue", True, "physical_hazard", "Utility wire down in front yard for 6 weeks; physical hazard"),
    "GS-191": ("appointment_installation", True, "none", "Scheduling utility line transfer from replaced PSEG pole to new pole"),
    "GS-192": ("connectivity_issue", True, "prolonged_outage", "Day 5 with no internet (>=48h override)"),
    "GS-193": ("other", False, "none", "Net Neutrality policy advocacy tweet; out of scope Twitter commentary"),
    "GS-194": ("appointment_installation", True, "none", "Scheduling technician truck to reconnect fiber drop from pole to basement ONT"),
    "GS-195": ("connectivity_issue", True, "medical", "Day 7 outage; elderly mom unable to access LifeAlert (Medical safety override)"),
    "GS-196": ("connectivity_issue", True, "physical_hazard", "Downed utility wire laying across neighbor's driveway; hazard override"),
    "GS-197": ("billing_dispute", True, "legal_regulatory", "Unfulfilled $250 promotional gift card; filing complaints with BBB and FTC"),
    "GS-198": ("connectivity_issue", True, "physical_hazard", "Rotted utility pole snapped after months of delay; physical hazard"),
    "GS-199": ("billing_dispute", True, "legal_regulatory", "Alleging contract fraud, recordings sent to regulatory officials"),
    "GS-200": ("billing_dispute", True, "legal_regulatory", "Threatening retention of attorney to blow whistle on account dispute"),
}

def main():
    print("[label_golden] Loading unlabeled golden set...")
    df = pd.read_csv(UNLABELED_PATH)
    assert len(df) == 200, f"Error: expected 200 rows, found {len(df)}"

    labeled_rows = []
    missing = []

    for _, row in df.iterrows():
        sid = row["sample_id"]
        if sid in ANNOTATIONS:
            intent, escalate, override, notes = ANNOTATIONS[sid]
            r = row.to_dict()
            r["intent"] = intent
            r["escalate"] = escalate
            r["severity_override"] = override
            r["notes"] = notes
            labeled_rows.append(r)
        else:
            missing.append(sid)

    if missing:
        raise ValueError(f"Missing annotations for sample IDs: {missing}")

    df_labeled = pd.DataFrame(labeled_rows)
    df_labeled.to_csv(LABELED_PATH, index=False, encoding="utf-8")
    print(f"[label_golden] Successfully saved 200 labeled items -> {LABELED_PATH}")

    # Summary Statistics
    print("\n--- GOLDEN SET SUMMARY STATISTICS ---")
    print("Class Distribution:")
    print(df_labeled["intent"].value_counts())
    print(f"\nEscalation Rate: {df_labeled['escalate'].mean()*100:.1f}% ({df_labeled['escalate'].sum()}/{len(df_labeled)})")
    print("\nSeverity Override Distribution:")
    print(df_labeled["severity_override"].value_counts())

if __name__ == "__main__":
    main()
