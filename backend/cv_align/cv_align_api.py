from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI()

# Request models
class CVRankRequest(BaseModel):
    job_description: str
    cvs: List[str]  # List of CV texts or file paths

class CVAnalyseRequest(BaseModel):
    job_description: str
    cv: str  # CV text or file path

# Dummy logic for demonstration (replace with actual CV_align logic)
def rank_cvs(job_description: str, cvs: List[str]) -> List[Dict[str, Any]]:
    # Replace with actual ranking logic
    return [
        {"cv": cv, "score": len(cv) % 100} for cv in sorted(cvs, key=lambda x: len(x), reverse=True)
    ]

def analyse_cv(job_description: str, cv: str) -> Dict[str, Any]:
    # Replace with actual analysis logic
    return {
        "cv": cv,
        "job_description": job_description,
        "match_score": len(cv) % 100,
        "analysis": "This is a dummy analysis. Replace with real output."
    }

@app.post("/rank-cvs")
def rank_cvs_endpoint(request: CVRankRequest):
    result = rank_cvs(request.job_description, request.cvs)
    return {"ranked_cvs": result}

@app.post("/analyse-cv")
def analyse_cv_endpoint(request: CVAnalyseRequest):
    result = analyse_cv(request.job_description, request.cv)
    return result

# To run: uvicorn cv_align_api:app --reload --port 8000
