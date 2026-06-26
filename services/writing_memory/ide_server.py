import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from datetime import datetime

app = FastAPI(title="Research OS IDE MVP")

# Ensure static directory exists
os.makedirs("services/writing_memory/static", exist_ok=True)

@app.get("/")
def read_root():
    return FileResponse("services/writing_memory/static/ide.html")

@app.get("/api/search/literature")
async def search_literature(q: str, limit: int = 10):
    """Search literature using the free OpenAlex API"""
    try:
        # OpenAlex uses search filter
        url = f"https://api.openalex.org/works?search={q}&per-page={limit}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            
            results = []
            for work in data.get("results", []):
                # OpenAlex returns abstracts as an inverted index, we skip full parsing for MVP
                authors = [a.get("author", {}).get("display_name", "") for a in work.get("authorships", [])[:3]]
                author_str = ", ".join(authors) + (" et al." if len(work.get("authorships", [])) > 3 else "")
                
                results.append({
                    "id": work.get("id"),
                    "title": work.get("title") or "Untitled",
                    "doi": work.get("doi") or "",
                    "year": work.get("publication_year") or "",
                    "authors": author_str,
                    "oa_url": work.get("open_access", {}).get("oa_url") or ""
                })
            return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/api/generate_digest")
async def generate_digest(topic: str = "HER2 ADC"):
    """Mock endpoint for weekly digest generation"""
    # In production, this would fetch the last 7 days of OpenAlex data and call DeepSeek/Claude
    today = datetime.now().strftime("%Y-%m-%d")
    markdown_report = f"""# Weekly Research Digest: {topic}
**Generated:** {today}

## 🚀 1. Novel Targets & Mechanisms
- **Discovery of a novel bispecific ADC targeting HER2 and TROP2** (Nature Cancer, 2026). This paper demonstrates a 30% increase in internalization rate compared to Enhertu.
- **Overcoming Trastuzumab Deruxtecan resistance** via lysosomal pathway modulation.

## 🧬 2. Patent & IP Updates
- **US20260012345A1**: Daiichi Sankyo filed a new patent covering a novel cleavable linker with a DAR of 8. *FTO Alert: High relevance to our internal linker design.*

## 💡 3. Actionable Insights for Our Lab
Based on the literature, we recommend adjusting our `Project_A` cell-killing assay protocol to include a 48-hour lysosomal inhibitor pre-treatment.
"""
    return {"ok": True, "report": markdown_report, "title": f"Weekly Digest: {topic}"}

if __name__ == "__main__":
    print("🚀 Starting Research OS IDE MVP on http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
