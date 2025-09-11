"""
kg_rag_service/main.py

FastAPI microservice for:
- Knowledge Graph (NetworkX)
- Semantic embeddings (sentence-transformers)
- FAISS retrieval
- CV / Job parsing
- Scoring (graph overlap + embedding sim)
- LLM wrapper (Ollama with LLaMA3.2)
"""

import os
import json
import time
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
import networkx as nx
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import re
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kg_rag_service")

# ----------------------------
# Config (tweak as needed)
# ----------------------------
KG_FILE = "careerhunt_kg.gpickle"
EMBEDDINGS_FILE = "embeddings.json"
FAISS_INDEX_FILE = "faiss.index"
NEW_NODES_FILE = "new_nodes_log.json"
DIM = 384  # embedding dimension for all-MiniLM-L6-v2
N_RETRIEVE_DEFAULT = 8

# LLM config (Ollama)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# ----------------------------
# Init / Load models & data
# ----------------------------
logger.info("Loading embedding model...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Load or initialize KG and embeddings
if os.path.exists(KG_FILE) and os.path.exists(EMBEDDINGS_FILE):
    try:
        G = nx.read_gpickle(KG_FILE)
        with open(EMBEDDINGS_FILE, "r") as f:
            embeddings = json.load(f)
        logger.info(f"Loaded existing KG: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    except Exception as e:
        logger.error(f"Failed to load KG/embeddings: {e}")
        G = nx.Graph()
        embeddings = {}
else:
    G = nx.Graph()
    embeddings = {}

# Ensure new nodes log exists
if not os.path.exists(NEW_NODES_FILE):
    with open(NEW_NODES_FILE, "w") as f:
        json.dump([], f)

# Build (or rebuild) FAISS index helper
def build_faiss_index(emb_dict: Dict[str, List[float]]):
    keys = list(emb_dict.keys())
    if len(keys) == 0:
        index = faiss.IndexFlatIP(DIM)
        return index, keys
    vecs = np.array([emb_dict[k] for k in keys]).astype('float32')
    # normalize for cosine using inner product
    faiss.normalize_L2(vecs)
    index = faiss.IndexFlatIP(DIM)
    index.add(vecs)
    return index, keys

faiss_index, faiss_keys = build_faiss_index(embeddings)
logger.info(f"FAISS index initialized with {len(faiss_keys)} vectors.")

# ----------------------------
# Utilities
# ----------------------------
def persist_state():
    try:
        nx.write_gpickle(G, KG_FILE)
        with open(EMBEDDINGS_FILE, "w") as f:
            json.dump(embeddings, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to persist state: {e}")

def log_new_node(node_name: str, node_type: str):
    try:
        with open(NEW_NODES_FILE, "r") as f:
            log = json.load(f)
    except:
        log = []
    log.append({"node": node_name, "type": node_type, "ts": time.time()})
    with open(NEW_NODES_FILE, "w") as f:
        json.dump(log, f, indent=2)

def compute_text_embedding(text: str) -> List[float]:
    vec = embedder.encode([text])[0].astype('float32')
    return vec.tolist()

def add_vector_to_faiss(node_name: str, vector: List[float]):
    global faiss_index, faiss_keys
    v = np.array([vector]).astype('float32')
    faiss.normalize_L2(v)
    if faiss_index is None:
        faiss_index, faiss_keys = build_faiss_index({node_name: vector})
    else:
        faiss_index.add(v)
        faiss_keys.append(node_name)

def faiss_search_by_vector(vec: List[float], topk: int = 5) -> List[Dict[str, Any]]:
    if faiss_index is None or faiss_index.ntotal == 0:
        return []
    v = np.array([vec]).astype('float32')
    faiss.normalize_L2(v)
    D, I = faiss_index.search(v, topk)
    results = []
    for score, idx in zip(D[0], I[0]):
        if idx < len(faiss_keys):
            results.append({"node": faiss_keys[idx], "score": float(score)})
    return results

def node_text_representation(node: str) -> str:
    meta = G.nodes.get(node, {})
    parts = [node]
    for k, v in meta.items():
        if isinstance(v, (str, int, float)):
            parts.append(str(v))
        elif isinstance(v, list):
            parts.append(" ".join([str(x) for x in v]))
    return " ".join(parts)

# ----------------------------
# Simple parsers
# ----------------------------
def parse_cv_text(cv_text: str) -> Dict[str, Any]:
    text = cv_text.replace("\r", "\n")
    skills = []
    experience = []
    skill_patterns = [r"skills[:\-]\s*(.+)", r"technical skills[:\-]\s*(.+)"]
    for pat in skill_patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            sline = m.group(1)
            for s in re.split(r"[,|\n;]+", sline):
                s = s.strip()
                if s:
                    skills.append(s)
            break
    if not skills:
        tokens = re.findall(r"\b[A-Za-z\+\#]{2,20}\b", text)
        freq = {}
        for t in tokens:
            freq[t.lower()] = freq.get(t.lower(), 0) + 1
        for w, c in sorted(freq.items(), key=lambda x: -x[1])[:40]:
            if c >= 2 and len(w) >= 2 and not w.isnumeric():
                skills.append(w)
    exp_lines = re.findall(r".{0,80}(?:at|@)\s+[A-Z][\w&\-\s]{2,80}", text)
    for line in exp_lines[:10]:
        experience.append(line.strip())
    return {"skills": list(dict.fromkeys([s.strip() for s in skills if s.strip()])), "experience": experience}

def parse_job_text(job_text: str) -> Dict[str, Any]:
    skills = []
    title = ""
    company = ""
    m = re.search(r"required skills[:\-]\s*(.+)", job_text, flags=re.IGNORECASE)
    if m:
        for s in re.split(r"[,|\n;]+", m.group(1)):
            s = s.strip()
            if s:
                skills.append(s)
    if not skills:
        m2 = re.search(r"(requirements|must have|you must have)[:\-]\s*(.+)", job_text, flags=re.IGNORECASE)
        if m2:
            for s in re.split(r"[,|\n;]+", m2.group(2)):
                s = s.strip()
                if s:
                    skills.append(s)
    mtitle = re.search(r"title[:\-]\s*(.+)", job_text, flags=re.IGNORECASE)
    if mtitle:
        title = mtitle.group(1).strip()
    mcomp = re.search(r"company[:\-]\s*(.+)", job_text, flags=re.IGNORECASE)
    if mcomp:
        company = mcomp.group(1).strip()
    return {"title": title, "company": company, "required_skills": [s for s in skills if s]}

# ----------------------------
# FastAPI app + models
# ----------------------------
app = FastAPI(title="KG-RAG Service")

class AddNodeRequest(BaseModel):
    node_name: str
    node_type: str
    neighbors: List[str] = []
    metadata: Optional[Dict[str, Any]] = None

class IngestCVRequest(BaseModel):
    application_id: str
    user_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    cv_text: str

class IngestJobRequest(BaseModel):
    job_id: str
    title: Optional[str] = None
    company: Optional[str] = None
    job_text: str

class EvalRequest(BaseModel):
    candidate_node: str
    job_node: str
    return_explanation: bool = True
    topk: int = 5

class RankRequest(BaseModel):
    job_node: str
    candidate_nodes: List[str]
    topn: int = 10
    return_explanation: bool = True

# ----------------------------
# Scoring & Evaluation Helpers
# ----------------------------
def graph_overlap_score(job_node: str, candidate_node: str) -> float:
    job_skills = [n.replace("skill_", "") for n in G.neighbors(job_node) if n.startswith("skill_")]
    cand_skills = [n.replace("skill_", "") for n in G.neighbors(candidate_node) if n.startswith("skill_")]
    if len(job_skills) == 0:
        return 0.0
    matched = len(set(job_skills).intersection(set(cand_skills)))
    return matched / len(job_skills)

def embedding_similarity(node_a: str, node_b: str) -> float:
    if node_a not in embeddings or node_b not in embeddings:
        return 0.0
    a = np.array(embeddings[node_a]).astype('float32')
    b = np.array(embeddings[node_b]).astype('float32')
    denom = (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
    return float(np.dot(a, b) / denom)

# ----------------------------
# LLM wrapper (Ollama)
# ----------------------------
def call_llm(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["ollama", "run", OLLAMA_MODEL],
            input=prompt.encode("utf-8"),
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            logger.error(f"Ollama error: {result.stderr}")
            return "LLM failed to generate response."
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"call_llm error: {e}")
        return "LLM service unavailable."

# ----------------------------
# Core Endpoints
# ----------------------------
@app.post("/add_node")
def add_node(req: AddNodeRequest):
    node = req.node_name
    if node in G:
        return {"status": "exists", "node": node}
    if req.node_type not in ["job", "skill", "company", "candidate"]:
        raise HTTPException(status_code=400, detail="Invalid node_type")
    G.add_node(node, type=req.node_type, **(req.metadata or {}))
    for n in req.neighbors:
        if n not in G:
            if n.startswith("job_"):
                G.add_node(n, type="job")
            elif n.startswith("skill_"):
                G.add_node(n, type="skill")
            elif n.startswith("company_"):
                G.add_node(n, type="company")
            else:
                G.add_node(n, type="skill")
        G.add_edge(node, n)
    node_text = node_text_representation(node)
    vec = compute_text_embedding(node_text)
    neighbor_vecs = [embeddings[n] for n in req.neighbors if n in embeddings]
    if neighbor_vecs:
        try:
            nv = np.mean(np.array(neighbor_vecs).astype('float32'), axis=0)
            vec = (0.6 * nv + 0.4 * np.array(vec)).astype('float32').tolist()
        except Exception:
            pass
    embeddings[node] = vec
    add_vector_to_faiss(node, vec)
    persist_state()
    log_new_node(node, req.node_type)
    return {"status": "ok", "node": node}

@app.post("/ingest_cv")
def ingest_cv(req: IngestCVRequest):
    parsed = parse_cv_text(req.cv_text)
    skills = parsed["skills"]
    candidate_node = f"candidate_{req.application_id}"
    neighbors = []
    for s in skills:
        sname = f"skill_{s}"
        neighbors.append(sname)
        if sname not in G:
            G.add_node(sname, type="skill", name=s)
            embeddings[sname] = compute_text_embedding(sname)
            add_vector_to_faiss(sname, embeddings[sname])
    add_node_req = AddNodeRequest(
        node_name=candidate_node,
        node_type="candidate",
        neighbors=neighbors,
        metadata={"name": req.name, "email": req.email, "user_id": req.user_id,
                  "application_id": req.application_id, "experience": parsed.get("experience", [])}
    )
    return add_node(add_node_req)

@app.post("/ingest_job")
def ingest_job(req: IngestJobRequest):
    parsed = parse_job_text(req.job_text)
    title = req.title or parsed.get("title") or ""
    company = req.company or parsed.get("company") or ""
    skills = parsed.get("required_skills", [])
    job_node = f"job_{req.job_id}"
    company_node = f"company_{company}" if company else None
    neighbors = []
    if company_node:
        neighbors.append(company_node)
        if company_node not in G:
            G.add_node(company_node, type="company", name=company)
            embeddings[company_node] = compute_text_embedding(company_node + " " + company)
            add_vector_to_faiss(company_node, embeddings[company_node])
    for s in skills:
        sname = f"skill_{s}"
        neighbors.append(sname)
        if sname not in G:
            G.add_node(sname, type="skill", name=s)
            embeddings[sname] = compute_text_embedding(sname)
            add_vector_to_faiss(sname, embeddings[sname])
    add_node_req = AddNodeRequest(node_name=job_node, node_type="job", neighbors=neighbors,
                                  metadata={"title": title, "company": company})
    return add_node(add_node_req)

@app.post("/evaluate_cv")
def evaluate_cv(req: EvalRequest):
    cand = req.candidate_node
    job = req.job_node
    if job not in G or cand not in G:
        raise HTTPException(status_code=404, detail="job or candidate node not found")
    graph_score = graph_overlap_score(job, cand)
    sim = embedding_similarity(job, cand)
    final_score = 0.5 * graph_score + 0.5 * sim
    job_skills = [n.replace("skill_", "") for n in G.neighbors(job) if n.startswith("skill_")]
    cand_skills = [n.replace("skill_", "") for n in G.neighbors(cand) if n.startswith("skill_")]
    missing = list(set(job_skills) - set(cand_skills))
    response = {
        "candidate_node": cand,
        "job_node": job,
        "graph_score": round(graph_score, 3),
        "embedding_similarity": round(sim, 3),
        "final_score": round(final_score, 3),
        "job_skills": job_skills,
        "candidate_skills": cand_skills,
        "missing_skills": missing
    }
    if req.return_explanation:
        prompt = (
            f"Job required skills: {', '.join(job_skills)}\n"
            f"Candidate skills: {', '.join(cand_skills)}\n"
            f"Scores -> graph:{graph_score:.3f}, sim:{sim:.3f}, final:{final_score:.3f}\n\n"
            "Write a short evaluation: (1) match summary (2) missing skills (3) recommended next steps."
        )
        response["explanation"] = call_llm(prompt)
    return response

@app.post("/rank_candidates")
def rank_candidates(req: RankRequest):
    job = req.job_node
    if job not in G:
        raise HTTPException(status_code=404, detail="job not found")
    scores = []
    for cand in req.candidate_nodes:
        if cand not in G:
            continue
        g = graph_overlap_score(job, cand)
        s = embedding_similarity(job, cand)
        final = 0.5 * g + 0.5 * s
        scores.append({"candidate": cand, "final_score": round(final, 3),
                       "graph_score": round(g, 3), "sim": round(s, 3)})
    scores = sorted(scores, key=lambda x: x["final_score"], reverse=True)
    out = {"job": job, "ranked": scores[:req.topn]}
    if req.return_explanation:
        prompt = f"Job required skills: {', '.join([n.replace('skill_','') for n in G.neighbors(job) if n.startswith('skill_')])}\n\n"
        prompt += "Candidates and skills:\n"
        for s in scores[:req.topn]:
            c = s["candidate"]
            prompt += f"- {c}: {', '.join([n.replace('skill_','') for n in G.neighbors(c) if n.startswith('skill_')])}\n"
        prompt += "\nExplain the ranking and suggest interview questions."
        out["explanation"] = call_llm(prompt)
    return out

@app.post("/search_nodes")
def search_nodes(query: str, topk: int = N_RETRIEVE_DEFAULT):
    qvec = compute_text_embedding(query)
    results = faiss_search_by_vector(qvec, topk)
    for r in results:
        r["type"] = G.nodes[r["node"]].get("type")
    return {"query": query, "results": results}

