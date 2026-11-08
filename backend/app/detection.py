"""Explainable, rule-based fraud indicator engine (standard library only).

A rule fires on one utterance only when every pattern group matches.
Scores are a screening aid. They never prove that a call is fraudulent.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

MEDIUM_SCORE = 2
HIGH_SCORE = 6
DISCLAIMER = ("Rule-based screening only. A flag is a reason to pause and verify, "
              "not proof that a call is fraudulent.")
SAFETY_TIPS = ("Never share an OTP, UPI PIN, password or card details on a call. "
               "Hang up and call the official number on your card or the bank's website. "
               "Cybercrime helpline in India: 1930, or cybercrime.gov.in.")
CATEGORY_LABELS = {
    "DIGITAL_ARREST": "Digital arrest / fake authority",
    "FAKE_KYC_BANK": "Fake KYC / bank impersonation",
    "UPI_PAYMENT": "UPI / payment fraud",
    "SOCIAL_ENGINEERING": "Social engineering",
}

_NUKTA = {"\u0958": "\u0915", "\u0959": "\u0916", "\u095a": "\u0917",
          "\u095b": "\u091c", "\u095e": "\u092b", "\u095f": "\u092f"}
_ASCII_PUNCT = re.compile(r"[!\"#$%&()*+,\-./:;<=>?@\[\\\]^_`{|}~\u0964\u0965]")


def normalize(text: str) -> str:
    """Lowercase, unify Devanagari spellings, drop zero-width characters and punctuation."""
    text = unicodedata.normalize("NFC", text)
    text = "".join(_NUKTA.get(ch, ch) for ch in text)
    text = text.replace("\u093c", "").replace("\u0901", "\u0902")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    text = _ASCII_PUNCT.sub(" ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


# Patterns are matched against normalize()d text, so they are written lowercase.
OTP = r"\botp\b|one time password|verification code|ओ ?टी ?पी|वन ?टाइम ?पासवर्ड"
SHARE = (r"\b(share|send|tell|read|give|batao|bataiye|bataye|bolo|bhejo|dijiye|dedo)\b"
         r"|बताइए|बताइये|बताएं|बताओ|भेजें|भेजो|दीजिए|बोलिए")
AUTH = (r"\b(police|cbi|enforcement directorate|cyber cell|crime branch|customs|narcotics|ncb|trai|court"
        r"|sarkari adhikari)\b|पुलिस|सीबीआई|ईडी|साइबर सेल|क्राइम ब्रांच|अदालत|कोर्ट|सरकारी अधिकारी")
ARREST = r"\barrest|\bwarrant\b|\bjail\b|custody|गिरफ्तार|वारंट|जेल"
INVEST = r"under (investigation|surveillance)|digital arrest|money laundering|mule account|आपके खिलाफ|आप पर (केस|मामला)|मनी लॉन्ड्रिंग"
SECRECY = (r"don'?t tell (anyone|anybody)|do not tell (anyone|anybody)|keep (this|it) secret"
           r"|kisi ko (mat|na) (batana|bataiye|bataye)|किसी को (मत|न) बताएं|फोन (मत|न) काटें|कॉल (मत|न) काटें"
           r"|phone mat (kaat|kat)|call mat (kaat|kat)")
PAY = (r"pay (a |the )?(fine|penalty|bail|security|amount)|send (the )?money|transfer (the )?money"
       r"|paise bhejo|paisa bhejo|paise (jama|dijiye|bhejiye)|जुर्माना|जमानत की राशि|पैसे (भेजें|भेजो|जमा)")
BANK = (r"bank (representative|officer|manager|executive|employee)"
        r"|(sbi|hdfc|icici|axis|pnb|kotak) (se|ka|ke) (bol|baat|karmchari|officer|executive)"
        r"|बैंक (से|का|के|की) (अधिकारी|कर्मचारी|प्रतिनिधि)")
KYC = r"\bkyc\b|के ?वाई ?सी|केवाईसी"
KYC_URG = r"urgent|immediately|today|expir|suspend|block|\b(turant|jald|jaldi|aaj|abhi)\b|तुरंत|जल्द|अभी|आज"
ACCOUNT_THREAT = r"(account|khata|खाता|अकाउंट).{0,30}(block|suspend|freez|deactivat|band|बंद|ब्लॉक|सस्पेंड)"
CRED = r"password|passcode|mpin|atm pin|cvv|card number|account number|पासवर्ड|सीवीवी|कार्ड नंबर|अकाउंट नंबर"
UPI_PIN = r"upi ?pin|यूपीआई ?(का )?पिन"
PIN_ACTION = r"\b(enter|daal|dalo|dalen|dalein|share|tell|batao|bataiye)\b|डालें|डालिए|डालो|दर्ज|बताइए|बताएं"
COLLECT = r"collect|payment request|money request|पेमेंट रिक्वेस्ट|रिक्वेस्ट"
APPROVE = r"\bapprove\b|\baccept\b|\ballow\b|अप्रूव|स्वीकार|मंजूर"
REFUND = r"refund|reversal|cashback|रिफंड|रीफंड|पैसे वापस|पैसा वापस"
SUPPORT = r"customer (care|support|service) (executive|agent|officer|representative)|helpline|कस्टमर केयर"
ID_TERM = r"aadhaar|aadhar|pan card|pan number|date of birth|आधार|पैन"
URGENCY = (r"urgent|immediately|right now|last chance|hurry|\b(turant|jaldi|jald|abhi)\b"
           r"|\b\d+ (minutes?|mins?|hours?)\b|तुरंत|जल्दी|जल्द|अभी")
THREAT = r"legal action|severe action|strict action|will be punished|dhamki|धमकी|सख्त कार्रवाई|कानूनी कार्रवाई"
REMOTE = r"anydesk|teamviewer|quicksupport|quick support|screen ?share|remote access|एनीडेस्क"

# Benign warning phrasing. Suppresses only rules marked suppressible.
_BENIGN = [re.compile(p) for p in (
    r"\b(never|not) (ever )?(ask|asks|request|requests)\b",
    r"\bnever (enter|share|disclose|give)\b|\bdo not (share|disclose)\b|\bdon'?t share\b",
    r"\b(never|do not|don'?t) tell (anyone|anybody) your\b",
    r"कभी (भी )?(नहीं|न)|नहीं (मांगते|पूछते)|शेयर न करें|साझा न करें",
)]


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    weight: int
    groups: tuple
    explanation: str
    action: str
    critical: bool = False
    suppressible: bool = False


def _rule(*args, **kwargs) -> Rule:
    return Rule(*args, **kwargs)


RULES = [
    _rule("DA_AUTHORITY", "DIGITAL_ARREST", 2, (AUTH,),
          "Claims to speak for police, a central agency or a court. Real officials do not run arrests or fines over a phone call.",
          "Do not act on it. Hang up and verify through an official number."),
    _rule("DA_ARREST", "DIGITAL_ARREST", 3, (ARREST,),
          "Threatens arrest, a warrant or jail to create fear.",
          "Do not comply. Report to 1930 or cybercrime.gov.in."),
    _rule("DA_INVESTIGATION", "DIGITAL_ARREST", 3, (INVEST,),
          "Says the person is under investigation or linked to a crime such as money laundering.",
          "Do not share any details. Report the call to 1930."),
    _rule("DA_SECRECY", "DIGITAL_ARREST", 2, (SECRECY,),
          "Asks the person to keep the call secret or stay connected. Isolation stops the victim from checking.",
          "Hang up. Talk to a trusted family member before any payment.", suppressible=True),
    _rule("DA_PAYMENT_DEMAND", "DIGITAL_ARREST", 3, (PAY,),
          "Demands money for a fine, bail or deposit to avoid arrest.",
          "Never transfer money on a call. Report to 1930.", suppressible=True),
    _rule("BANK_CLAIM", "FAKE_KYC_BANK", 1, (BANK,),
          "Claims to be a bank employee. Banks do call customers, so this alone is weak evidence.",
          "Hang up and call the number printed on your card or on the bank's official website."),
    _rule("OTP_REQUEST", "FAKE_KYC_BANK", 5, (OTP, SHARE),
          "Asks the person to share or read out an OTP. OTPs authorise transactions and account changes.",
          "Do not share the OTP with anyone. Hang up now.", critical=True, suppressible=True),
    _rule("CREDENTIAL_REQUEST", "FAKE_KYC_BANK", 5, (CRED, SHARE),
          "Asks for a password, CVV, card number or account number.",
          "Never share credentials on a call. If you already shared one, change it in the official app.",
          critical=True, suppressible=True),
    _rule("KYC_URGENCY", "FAKE_KYC_BANK", 2, (KYC, KYC_URG),
          "Pairs a KYC update with urgency or a deadline, a common fake-KYC pattern.",
          "Update KYC only through the official bank app or branch."),
    _rule("ACCOUNT_THREAT", "FAKE_KYC_BANK", 2, (ACCOUNT_THREAT,),
          "Threatens to block or suspend the account to force a quick response.",
          "Check the account status in the official app, not through the caller."),
    _rule("UPI_PIN_REQUEST", "UPI_PAYMENT", 5, (UPI_PIN, PIN_ACTION),
          "Asks the person to enter a UPI PIN. Entering a PIN sends money. Receiving money never needs a PIN.",
          "Never enter a UPI PIN to receive money. Close the app and report to 1930.",
          critical=True, suppressible=True),
    _rule("COLLECT_APPROVAL", "UPI_PAYMENT", 5, (COLLECT, APPROVE),
          "Asks the person to approve a collect or payment request. Approving one sends money to the caller.",
          "Decline the collect request in your UPI app. Do not approve requests from callers.",
          critical=True, suppressible=True),
    _rule("FAKE_REFUND", "UPI_PAYMENT", 1, (REFUND,),
          "Mentions a refund. Refund talk is common in scams and in real support calls.",
          "Check the refund status in your bank or UPI app, not through the caller."),
    _rule("SUPPORT_CLAIM", "UPI_PAYMENT", 1, (SUPPORT,),
          "Claims to be customer support. Weak evidence alone; verify the number independently.",
          "Use the helpline listed on the official website."),
    _rule("SENSITIVE_ID_REQUEST", "SOCIAL_ENGINEERING", 3, (ID_TERM, SHARE),
          "Asks for identity numbers such as Aadhaar, PAN or date of birth.",
          "Do not share identity numbers on an unsolicited call.", suppressible=True),
    _rule("URGENCY", "SOCIAL_ENGINEERING", 1, (URGENCY,),
          "Creates time pressure. Urgency alone is common and is not treated as a scam.",
          "Take a moment and verify before acting."),
    _rule("THREAT_LANGUAGE", "SOCIAL_ENGINEERING", 2, (THREAT,),
          "Uses threats or intimidation to force a quick decision.",
          "Do not respond to threats. End the call."),
    _rule("REMOTE_ACCESS", "SOCIAL_ENGINEERING", 5, (REMOTE,),
          "Asks the person to install a screen-sharing or remote-control app, which gives the caller control of the phone.",
          "Do not install apps on request. Uninstall any you installed and report to 1930.", critical=True),
]
_COMPILED = [(rule, [re.compile(g) for g in rule.groups]) for rule in RULES]


def analyze(transcript: str) -> dict:
    """Score a transcript line by line and return the evidence behind every alert."""
    utterances = [(n, line.strip()) for n, line in enumerate(transcript.splitlines(), 1) if line.strip()]
    fired: dict[str, list[dict]] = {}
    for line_no, raw in utterances:
        norm = normalize(raw)
        benign = any(p.search(norm) for p in _BENIGN)
        for rule, pats in _COMPILED:
            if rule.suppressible and benign:
                continue
            if all(p.search(norm) for p in pats):
                fired.setdefault(rule.id, []).append({"line": line_no, "text": raw})

    hits = [r for r in RULES if r.id in fired]
    score = sum(r.weight for r in hits)
    critical = any(r.critical for r in hits)
    if critical or score >= HIGH_SCORE:
        risk = "HIGH"
    elif score >= MEDIUM_SCORE:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    weight_by_category: dict[str, int] = {}
    for r in hits:
        weight_by_category[r.category] = weight_by_category.get(r.category, 0) + r.weight
    category = None
    if weight_by_category and risk != "LOW":
        category = max(weight_by_category, key=weight_by_category.get)
    top = max(hits, key=lambda r: (r.critical, r.weight), default=None)
    action = top.action if top else ("No significant indicators found. Still never share OTPs, "
                                     "UPI PINs or passwords on a call.")
    return {
        "risk_level": risk,
        "score": score,
        "critical_indicator": critical,
        "category": category,
        "category_label": CATEGORY_LABELS.get(category),
        "recommended_action": action,
        "utterance_count": len(utterances),
        "indicators": [{"rule_id": r.id, "category": r.category, "weight": r.weight,
                        "critical": r.critical, "explanation": r.explanation,
                        "evidence": fired[r.id]} for r in hits],
        "thresholds": {"medium_at": MEDIUM_SCORE, "high_at": HIGH_SCORE,
                       "critical_indicator_forces_high": True},
        "safety_tips": SAFETY_TIPS,
        "disclaimer": DISCLAIMER,
    }
