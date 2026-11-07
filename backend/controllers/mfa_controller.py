from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.dependencies import AuthContext, get_auth_context
from backend.schemas.mfa import MfaCode, MfaVerify, MfaSetupResponse
from backend.schemas.schemas import AuthResponse
from backend.schemas.platform import Reauthentication
from backend.services import mfa_service as mfa

router = APIRouter(prefix='/auth/mfa', tags=['MFA'])


def private(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'


@router.get('/status')
def status(response: Response, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    private(response)
    return mfa.status(db, ctx.user.id)


@router.post('/enroll/start', response_model=MfaSetupResponse)
def start(payload: Reauthentication, response: Response, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    private(response)
    return mfa.start(db, ctx.user, payload.password.get_secret_value())


@router.post('/enroll/confirm')
def confirm(payload: MfaCode, response: Response, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    private(response)
    return mfa.confirm(db, ctx.user, payload.code.get_secret_value())


@router.post('/verify', response_model=AuthResponse)
def verify(payload: MfaVerify, response: Response, db: Session = Depends(get_db)):
    private(response)
    return mfa.verify(db, payload.challenge.get_secret_value(), payload.code.get_secret_value())


@router.post('/disable')
def disable(payload: Reauthentication, response: Response, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    private(response)
    return mfa.manage(db, ctx.user, payload.password.get_secret_value(), disable=True)


@router.post('/recovery-codes/regenerate')
def regenerate(payload: Reauthentication, response: Response, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    private(response)
    return mfa.manage(db, ctx.user, payload.password.get_secret_value())
