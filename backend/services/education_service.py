"""Read-only public sample answers. Never reads a DB, private corpus or model.

Only exact reviewed glossary evidence supports the corresponding curated claim.
Arbitrary retrieved text, URLs, numerical claims and tool instructions are never
rendered as answers. This narrow grounding rule is deliberately conservative.
"""
from datetime import date
from urllib.parse import quote

from backend.core.telemetry import traceable
from backend.knowledge.education import GLOSSARY
from backend.knowledge.registry import Registry, SourceVersion
from backend.schemas.knowledge import Citation, EducationAnswer


def freshness(source: SourceVersion, as_of: date):
    if as_of < max(source.effective, source.published, source.fetched):
        return 'not_yet_current'
    return 'expired' if as_of >= source.expires else 'current'


def citation(source: SourceVersion, as_of: date) -> Citation:
    return Citation(**{key: getattr(source, key) for key in (
        'source_id', 'version', 'title', 'content_hash', 'published', 'fetched', 'effective', 'expires', 'licence', 'jurisdiction')},
        url=str(source.url), staleness=freshness(source, as_of),
        resolve_path='/education/sources/' + quote(source.source_id, safe='') + '/versions/' + str(source.version))


@traceable(name='education.answer')
def answer(topic: str, registry: Registry, *, as_of: date) -> EducationAnswer:
    evidence = registry.public_catalog(topic)
    sources = [citation(v, as_of) for v in evidence]
    current = [v for v in evidence if freshness(v, as_of) == 'current']
    result = dict(topic=topic, status='unavailable', text='Current reviewed evidence is unavailable for this topic.',
                  reason='no_current_public_evidence', as_of=as_of, staleness='unavailable', sources=sources)
    if sources and not current:
        result['staleness'] = 'expired' if all(v.staleness == 'expired' for v in sources) else 'not_yet_current'
    if current and topic in GLOSSARY:
        # A topic tag alone does not establish entailment. Conflicting or injected
        # documents fail closed, even alongside an otherwise valid citation.
        if any(v.text != GLOSSARY[topic] for v in current):
            result.update(reason='evidence_conflict_or_unsupported_claim', staleness='conflicting')
        else:
            result.update(status='complete', text=GLOSSARY[topic], reason=None, staleness='current',
                          sources=[citation(v, as_of) for v in current])
    return EducationAnswer(**result)


def resolve(source_id: str, version: int, registry: Registry, *, as_of: date):
    # Only fixed glossary topics are in this public application corpus. No caller
    # controls an owner, index name, filesystem path or ingestion URL.
    for topic in GLOSSARY:
        for source in registry.public_catalog(topic):
            if (source.source_id, source.version) == (source_id, version):
                label = freshness(source, as_of)
                return {'source': citation(source, as_of), 'as_of': as_of,
                        'excerpt': source.text if label == 'current' and source.text == GLOSSARY[topic] else None,
                        'corpus': 'public_sample_only'}
    return None
