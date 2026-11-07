"""Curated education only; retrieved text is never interpreted as instructions."""
from datetime import date
from backend.knowledge.registry import Registry

GLOSSARY = {
    "emi": "An EMI is a scheduled loan payment. It can contain principal and interest; a bank debit alone does not prove the split.",
    "budget": "A budget compares planned income and commitments. Historical surplus alone does not establish investable cash.",
    "risk": "Investment values can fall. Essential near-term goals need liquidity and capacity assessment.",
    "tax_documents": "Tax documents provide evidence for a supported period; they do not by themselves establish a final tax liability.",
}


def educate(topic: str, registry: Registry, *, owner_id: int, as_of: date):
    evidence = registry.retrieve(topic, owner_id=owner_id, as_of=as_of)
    if topic not in GLOSSARY or not evidence:
        return {"status": "unavailable", "reason": "No current reviewed education evidence"}
    return {"status": "complete", "kind": "generic_education", "text": GLOSSARY[topic],
            "citations": [{"source_id": v.source_id, "version": v.version,
                           "hash": v.content_hash, "url": str(v.url)} for v in evidence]}
