import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.dependencies import get_current_user, profile_to_dict
from backend.schemas.schemas import ChatRequest, ChatResponse
from backend.services.chat_service import ChatService
from backend.services.profile_service import ProfileService
from backend.models.models import User

router = APIRouter(prefix="/chat", tags=["Chat"])


# ─── Standard Chat ────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
def chat(
    payload:      ChatRequest,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """
    Standard chat endpoint — returns full reply at once.

    Use this as fallback if streaming is not supported
    by the client environment.

    The AI knows:
    - Complete financial profile
    - Health score and grade
    - Full investment plan and SIPs
    - Stock recommendations
    - Credit card recommendations
    - Full conversation history
    - Knowledge base context for the query

    Example questions:
    - Why did you recommend HDFC Millennia?
    - How do I start a SIP?
    - What is ELSS?
    - Explain my health score
    - How much will I have in 10 years?
    """

    service  = ChatService(db)
    profile  = ProfileService(db).get(current_user.id)
    profile_dict = profile_to_dict(profile) if profile else {}

    # Get or create thread — saves user name and email to DB
    thread_id = service.get_or_create_thread(
        user_id    = current_user.id,
        thread_id  = payload.thread_id,
        message    = payload.message,
        user_name  = current_user.full_name,
        user_email = current_user.email
    )

    # Get reply
    result = service.chat(
        user_id   = current_user.id,
        user_name = current_user.full_name,
        message   = payload.message,
        thread_id = thread_id,
        profile   = profile_dict
    )

    return ChatResponse(
        reply     = result["reply"],
        thread_id = result["thread_id"]
    )


# ─── Streaming Chat ───────────────────────────────────────────────────────────

@router.post("/stream")
def chat_stream(
    payload:      ChatRequest,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """
    Streaming chat endpoint — returns tokens as Server Sent Events.

    Frontend receives and renders each token as it arrives —
    user sees the reply being typed in real time like ChatGPT.

    SSE Format:
        data: {"chunk": "Hello", "thread_id": 1}
        data: {"chunk": " there", "thread_id": 1}
        data: {"done": true, "thread_id": 1, "full_reply": "Hello there"}

    On error:
        data: {"error": "error message"}
    """

    service  = ChatService(db)
    profile  = ProfileService(db).get(current_user.id)
    profile_dict = profile_to_dict(profile) if profile else {}

    # Get or create thread — saves user name and email to DB
    thread_id = service.get_or_create_thread(
        user_id    = current_user.id,
        thread_id  = payload.thread_id,
        message    = payload.message,
        user_name  = current_user.full_name,
        user_email = current_user.email
    )

    # ── Generator function ────────────────────────────────────────────────
    def generate():
        full_reply = ""
        try:
            for chunk in service.chat_stream(
                user_id   = current_user.id,
                user_name = current_user.full_name,
                message   = payload.message,
                thread_id = thread_id,
                profile   = profile_dict
            ):
                if chunk:
                    full_reply += chunk
                    # Send chunk as SSE event
                    yield f"data: {json.dumps({'chunk': chunk, 'thread_id': thread_id})}\n\n"

            # Send done signal with full reply
            yield f"data: {json.dumps({'done': True, 'thread_id': thread_id, 'full_reply': full_reply})}\n\n"

        except Exception as e:
            print(f"[ChatStream] Error: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type = "text/event-stream",
        headers    = {
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Connection":                  "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )


# ─── Chat History ─────────────────────────────────────────────────────────────

@router.get("/history/{thread_id}")
def get_chat_history(
    thread_id:    int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """
    Get full chat history for a thread.
    Shows who sent each message — user name or AI Advisor.
    """

    from backend.models.models import Thread, Message

    # Verify thread belongs to user
    thread = db.query(Thread).filter(Thread.id == thread_id).first()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found.")

    if thread.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Get messages
    messages = (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at)
        .all()
    )

    return {
        "thread_id":  thread_id,
        "title":      thread.title,
        "user_name":  thread.user_name,
        "user_email": thread.user_email,
        "created_at": thread.created_at,
        "messages": [
            {
                "id":         m.id,
                "role":       m.role,
                "user_name":  m.user_name or (current_user.full_name if m.role == "user" else "AI Advisor"),
                "content":    m.content,
                "created_at": m.created_at
            }
            for m in messages
        ]
    }