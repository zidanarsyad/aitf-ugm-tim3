from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import List, Optional, Any
import time
import json

app = FastAPI(
    title="Team 3 API - Communication Strategy",
    version="1.0.0",
    description="API Contract untuk integrasi dengan layanan AI dari Tim 3 yang mendukung CPT dan SFT untuk korpus legal pemerintah."
)

security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Middleware untuk memverifikasi API_KEY.
    Gunakan Authorization: Bearer <API_KEY>
    """
    api_key = credentials.credentials
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Missing API Key",
                    "type": "authentication_error",
                    "param": None,
                    "code": "missing_api_key"
                }
            }
        )
    return api_key

# --- Pydantic Models ---

# 1. Models
class ModelData(BaseModel):
    id: str
    object: str
    created: int
    owned_by: str
    description: str

class ListModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelData]

# 2. Chat Completions
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.3
    max_tokens: Optional[int] = 1500
    stream: Optional[bool] = False

class ChatCompletionResponseMessage(BaseModel):
    role: str
    content: str

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatCompletionResponseMessage
    finish_reason: str

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class CitationRegulation(BaseModel):
    type: str
    title: str
    value: str

class Citations(BaseModel):
    regulations: Optional[List[CitationRegulation]] = []
    press_statements: Optional[List[Any]] = []

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage
    citations: Optional[Citations] = None

# 3. Crawler Status
class CrawlerData(BaseModel):
    id: str
    type: str
    status: str
    last_successful_run: int
    documents_fetched_last_run: int
    error_code: Optional[Any] = None

class CrawlerStatusResponse(BaseModel):
    object: str = "system_status"
    overall_status: str
    data: List[CrawlerData]


# --- API Endpoints ---

@app.get("/v1/models", response_model=ListModelsResponse, dependencies=[Depends(verify_api_key)])
async def list_models():
    """Mengambil daftar model retrieval/refinement yang tersedia."""
    return {
        "object": "list",
        "data": [
            {
                "id": "team3-comm-strategy-sft-v1",
                "object": "model",
                "created": 1709425000,
                "owned_by": "team-3",
                "description": "Model SFT untuk penyusunan strategi komunikasi dan revisi draf dengan bahasa birokrasi formal."
            }
        ]
    }

@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: ChatCompletionRequest):
    """Endpoint utama untuk Penyusunan Draf Strategi Komunikasi dan Revisi Draf."""
    if request.model != "team3-comm-strategy-sft-v1":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "message": f"Model '{request.model}' not found",
                    "type": "invalid_request_error",
                    "param": "model",
                    "code": "model_not_found"
                }
            }
        )

    if request.stream:
        async def event_stream():
            chunk1 = {
                "id": "chatcmpl-t3-001",
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": "### Strategi "}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(chunk1)}\n\n"
            
            # Simulate processing delay
            # await asyncio.sleep(0.5) 
            
            chunk2 = {
                "id": "chatcmpl-t3-001",
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "citations": {
                    "regulations": [{"type": "perpres", "title": "Perpres No. 117 Tahun 2021", "value": "Pasal 2"}]
                }
            }
            yield f"data: {json.dumps(chunk2)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return {
        "id": "chatcmpl-t3-001",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "### Strategi Komunikasi\nKomunikasi proaktif dengan empati, menekankan pada bantalan sosial.\n\n### Key Messages\n- Pemerintah memahami beban masyarakat dan telah menyiapkan BLT.\n- Kenaikan BBM dialokasikan untuk infrastruktur.\n\n### Channel\nPress conference, infografis Instagram."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 350,
            "total_tokens": 500
        },
        "citations": {
            "regulations": [
                {
                    "type": "perpres",
                    "title": "Perpres No. 117 Tahun 2021",
                    "value": "Terkait penyediaan dan pendistribusian BBM."
                }
            ]
        }
    }

@app.get("/v1/crawlers/status", response_model=CrawlerStatusResponse, dependencies=[Depends(verify_api_key)])
async def crawler_status():
    """Memantau status digitalisasi dokumen (scraping UU, Perpres, siaran pers)."""
    return {
        "object": "system_status",
        "overall_status": "healthy",
        "data": [
            {
                "id": "crawler-legal-corpus",
                "type": "regulations",
                "status": "running",
                "last_successful_run": 1709420000,
                "documents_fetched_last_run": 30,
                "error_code": None
            }
        ]
    }

# --- Exception Handlers for Standard Error Format ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Validation Error",
                "type": "invalid_request_error",
                "param": exc.errors()[0]["loc"][-1] if exc.errors() else None,
                "code": "validation_error"
            }
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": str(detail),
                "type": "api_error",
                "param": None,
                "code": "error"
            }
        }
    )
