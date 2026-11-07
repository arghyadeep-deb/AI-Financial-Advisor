"""Authenticated, provider-free public sample education; no personalized research."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Response

from backend.core.dependencies import get_current_user
from backend.knowledge.education import GLOSSARY
from backend.knowledge.sample_catalog import sample_registry
from backend.models.models import User
from backend.schemas.knowledge import EducationRequest, EducationAnswer
from backend.services import education_service as service

router = APIRouter(prefix='/education', tags=['Public sample education'])


def today():
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


@router.get('/topics')
def topics(response: Response, user: User = Depends(get_current_user)):
    response.headers['Cache-Control'] = 'no-store'
    as_of, registry = today(), sample_registry()
    return {'corpus': 'public_sample_only', 'as_of': as_of, 'personalized_advice_enabled': False,
            'topics': [{'topic': topic, 'status': result.status, 'staleness': result.staleness}
                       for topic in sorted(GLOSSARY) for result in [service.answer(topic, registry, as_of=as_of)]]}


@router.post('/answers', response_model=EducationAnswer)
def answer(payload: EducationRequest, response: Response, user: User = Depends(get_current_user)):
    response.headers['Cache-Control'] = 'no-store'
    return service.answer(payload.topic, sample_registry(), as_of=today())


@router.get('/sources/{source_id}/versions/{version}')
def source(source_id: str, response: Response, version: int = Path(ge=1), user: User = Depends(get_current_user)):
    response.headers['Cache-Control'] = 'no-store'
    result = service.resolve(source_id, version, sample_registry(), as_of=today())
    if result is None:
        raise HTTPException(404, 'Resource not found.')
    return result
