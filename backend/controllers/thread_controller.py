from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.schemas.schemas import (
    ThreadCreate,
    ThreadResponse,
    HistoryResponse,
    MessageResponse
)
from backend.models.models import User, Thread, Message

router = APIRouter(prefix="/threads", tags=["Threads"])


# ─── Create Thread ────────────────────────────────────────────────────────────

@router.post("", response_model=ThreadResponse)
def create_thread(
    payload:      ThreadCreate,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """
    Create a new conversation thread.
    Saves user name and email so every thread in DB
    is traceable to a real person by name.
    """
    thread = Thread(
        user_id     = current_user.id,
        user_name   = current_user.full_name,
        user_email  = current_user.email,
        title       = payload.title[:200],
        thread_type = payload.thread_type
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


# ─── List Threads ─────────────────────────────────────────────────────────────

@router.get("")
def list_threads(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """
    List all conversation threads for the current user.
    Ordered by newest first.
    """
    threads = (
        db.query(Thread)
        .filter(Thread.user_id == current_user.id)
        .order_by(Thread.created_at.desc())
        .all()
    )

    return [
        {
            "id":          t.id,
            "title":       t.title,
            "thread_type": t.thread_type,
            "user_name":   t.user_name  or current_user.full_name,
            "user_email":  t.user_email or current_user.email,
            "created_at":  t.created_at
        }
        for t in threads
    ]


# ─── Get Thread History ───────────────────────────────────────────────────────

@router.get("/{thread_id}/history", response_model=HistoryResponse)
def get_history(
    thread_id:    int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """
    Get all messages in a specific thread.
    Each message shows who sent it — user name or AI Advisor.
    """

    # Verify thread exists
    thread = db.query(Thread).filter(Thread.id == thread_id).first()

    if not thread:
        raise HTTPException(
            status_code = 404,
            detail      = "Thread not found."
        )

    # Verify thread belongs to this user
    if thread.user_id != current_user.id:
        raise HTTPException(
            status_code = 403,
            detail      = "You do not have access to this thread."
        )

    # Get all messages ordered by time
    messages = (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at)
        .all()
    )

    return HistoryResponse(
        thread_id = thread_id,
        messages  = [
            MessageResponse(
                id         = m.id,
                role       = m.role,
                content    = m.content,
                created_at = m.created_at
            )
            for m in messages
        ]
    )


# ─── Get Full Thread Detail ───────────────────────────────────────────────────

@router.get("/{thread_id}")
def get_thread_detail(
    thread_id:    int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """
    Get full thread details including all messages with sender names.
    Useful for building a detailed chat history view.
    """

    thread = db.query(Thread).filter(Thread.id == thread_id).first()

    if not thread:
        raise HTTPException(
            status_code = 404,
            detail      = "Thread not found."
        )

    if thread.user_id != current_user.id:
        raise HTTPException(
            status_code = 403,
            detail      = "You do not have access to this thread."
        )

    messages = (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at)
        .all()
    )

    return {
        "thread_id":  thread.id,
        "title":      thread.title,
        "thread_type":thread.thread_type,
        "user_name":  thread.user_name  or current_user.full_name,
        "user_email": thread.user_email or current_user.email,
        "created_at": thread.created_at,
        "message_count": len(messages),
        "messages": [
            {
                "id":         m.id,
                "role":       m.role,
                "user_name":  (
                    m.user_name
                    if m.user_name
                    else (
                        current_user.full_name
                        if m.role == "user"
                        else "AI Advisor"
                    )
                ),
                "content":    m.content,
                "created_at": m.created_at
            }
            for m in messages
        ]
    }


# ─── Delete Thread ────────────────────────────────────────────────────────────

@router.delete("/{thread_id}")
def delete_thread(
    thread_id:    int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """Delete a thread and all its messages."""

    thread = db.query(Thread).filter(Thread.id == thread_id).first()

    if not thread:
        raise HTTPException(
            status_code = 404,
            detail      = "Thread not found."
        )

    if thread.user_id != current_user.id:
        raise HTTPException(
            status_code = 403,
            detail      = "You do not have access to this thread."
        )

    # Delete messages first
    db.query(Message).filter(
        Message.thread_id == thread_id
    ).delete()

    # Delete thread
    db.delete(thread)
    db.commit()

    return {
        "success":   True,
        "message":   f"Thread {thread_id} deleted successfully."
    }