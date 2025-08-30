from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, List, Optional
from src.models.grading import grade_answer
from src.models.content import summarize as content_summarize, diagram_prompt, qa_over_content, adaptation_suggestions
from src.models.recommend import recommend_modules
from src.models.analytics import compute_analytics

app = FastAPI(title="CHW E-Learning AI API")

class GradingRequest(BaseModel):
    question: str
    reference_answer: str
    user_answer: str
    lang: str

@app.post("/grade")
def grade(req: GradingRequest) -> Any:
    try:
        return grade_answer(req.question, req.reference_answer, req.user_answer, req.lang)
    except Exception as e:
        return {"error": str(e)}

class ContentRequest(BaseModel):
    text: str
    lang: str

@app.post("/summarize")
def summarize(req: ContentRequest) -> Any:
    try:
        return content_summarize(req.text, req.lang)
    except Exception as e:
        return {"error": str(e)}

@app.post("/diagram_prompt")
def diagram_prompt_ep(req: ContentRequest) -> Any:
    try:
        return diagram_prompt(req.text, req.lang)
    except Exception as e:
        return {"error": str(e)}

class QARequest(BaseModel):
    question: str
    lang: str

@app.post("/qa_over_content")
def qa_over_content_ep(req: QARequest) -> Any:
    try:
        return qa_over_content(req.question, req.lang)
    except Exception as e:
        return {"error": str(e)}

@app.post("/adaptation_suggestions")
def adaptation_suggestions_ep(req: ContentRequest) -> Any:
    try:
        return adaptation_suggestions(req.text, req.lang)
    except Exception as e:
        return {"error": str(e)}

class RecommendRequest(BaseModel):
    region: str
    patient_tags: List[str]
    level: str

@app.post("/recommend")
def recommend(req: RecommendRequest) -> Any:
    try:
        return recommend_modules(req.region, req.patient_tags, req.level)
    except Exception as e:
        return {"error": str(e)}

@app.get("/analytics")
def analytics() -> Any:
    try:
        return compute_analytics()
    except Exception as e:
        return {"error": str(e)}
