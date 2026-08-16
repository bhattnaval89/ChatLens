from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.services.parser import parse_whatsapp_chat

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="ChatLens")

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.post("/analyze", response_class=HTMLResponse)
async def analyze_chat(
    request: Request,
    chat_file: UploadFile = File(...),
):
    if not chat_file.filename or not chat_file.filename.lower().endswith(".txt"):
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"error": "Please upload a WhatsApp .txt export file."},
            status_code=400,
        )

    file_bytes = await chat_file.read()

    try:
        chat_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        chat_text = file_bytes.decode("utf-8-sig")

    messages_df = parse_whatsapp_chat(chat_text)

    if messages_df.empty:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "error": (
                    "No messages could be parsed. "
                    "Your WhatsApp export may use a different format."
                )
            },
            status_code=400,
        )

    preview_df = messages_df.head(10).copy()
    preview_df["timestamp"] = preview_df["timestamp"].dt.strftime("%d %b %Y, %I:%M %p")
    preview_rows = preview_df.fillna("").to_dict(orient="records")

    summary = {
        "total_rows": len(messages_df),
        "messages": int((~messages_df["is_system"]).sum()),
        "system_messages": int(messages_df["is_system"].sum()),
        "participants": int(messages_df["sender"].dropna().nunique()),
    }

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "summary": summary,
            "preview_rows": preview_rows,
        },
    )