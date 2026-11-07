"""ID-only deterministic StateGraph over the shared leased worker and DB markers.

Database state is the recovery checkpoint. Review publication is a separate,
authenticated revision-checked API transaction. No in-memory checkpointer is
advertised as durable; PostgreSQL checkpointer/interrupt integration is deferred.
"""
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from backend.models.models import StatementImport, WorkItem
from backend.services.statement_service import process_claimed


class MonthlyState(TypedDict, total=False):
    work_id: str
    fence: int
    import_id: str
    revision: int
    state: str
    error_code: str | None


def run_claimed(db, work_id, fence, *, scanner_available=True):
    def validate(state):
        work = db.get(WorkItem, state['work_id'])
        if not work or work.kind != 'statement':
            raise ValueError('Unsupported work')
        job = db.query(StatementImport).filter_by(user_id=work.user_id, work_id=work.id).one()
        return {'import_id': job.id}

    def extract_and_stage(state):
        process_claimed(db, state['work_id'], state['fence'], scanner_available=scanner_available)
        return {}

    def review_checkpoint(state):
        db.expire_all()
        job = db.get(StatementImport, state['import_id'])
        return {'revision': job.revision, 'state': job.state, 'error_code': job.error_code}

    graph = StateGraph(MonthlyState)
    graph.add_node('validate', validate)
    graph.add_node('extract_stage_reconcile', extract_and_stage)
    graph.add_node('review_checkpoint', review_checkpoint)
    graph.add_edge(START, 'validate')
    graph.add_edge('validate', 'extract_stage_reconcile')
    graph.add_edge('extract_stage_reconcile', 'review_checkpoint')
    graph.add_edge('review_checkpoint', END)
    return graph.compile().invoke({'work_id': work_id, 'fence': fence})
