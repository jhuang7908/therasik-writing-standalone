"""
pubmed_fetch.py — AI-native weekly article selection (full-text required).

Flow:
  PubMed (free full text / PMC OA) → fetch PMC full text → AI score Top-N
  → auto-pick one story → attach 2–3 PubMed neighbor references.
"""

import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
for _env in (ROOT / "content_generation_tools" / ".env", ROOT / ".env"):
    if _env.exists():
        for _line in _env.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                k, v = _line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
        break

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "pipeline@nextvivo.com")
NCBI_APIKEY = os.getenv("NCBI_API_KEY", "")

TOP_CANDIDATES = int(os.getenv("WEEKLY_ARTICLE_TOP_N", "20"))
MIN_FULLTEXT_CHARS = int(os.getenv("WEEKLY_MIN_FULLTEXT_CHARS", "5000"))
RELATED_REF_COUNT = int(os.getenv("WEEKLY_RELATED_REFS", "3"))

SEARCH_QUERY = (
    "(humanized mice[Title/Abstract] OR humanized mouse model[Title/Abstract])"
    " AND (immunotherapy[Title/Abstract] OR checkpoint[Title/Abstract]"
    "      OR CAR-T[Title/Abstract] OR bispecific[Title/Abstract]"
    "      OR tumor[Title/Abstract] OR cancer[Title/Abstract])"
    " AND (NSG[Title/Abstract] OR NCG[Title/Abstract] OR NOG[Title/Abstract]"
    "      OR PBMC[Title/Abstract] OR CD34[Title/Abstract])"
)

FULLTEXT_FILTER = "(free full text[filter] OR pmc open access[filter])"

SCORER_SYSTEM = """你是生物医药文献筛选器。任务：从【已有 PMC 全文】的候选中，选出最适合作为「本周唯一主线故事」的一篇。

主题：人源化小鼠模型 + 免疫类药物在人源化模型中的临床前评估。

## 硬性规则
1. 只能依据提供的 title / abstract / full_text_excerpt / journal 打分，禁止编造。
2. 必须能讲清「一个完整故事」：模型是什么、药物/疗法是什么、主要结果是什么。
3. 摘要空或过短、全文摘录无法支撑故事线 → total_score < 40。
4. 必须对每位候选都打分；selected_pmid 必须是列表中的 PMID。
5. 只输出 JSON，无 markdown。

## 评分（各 0–25，total 0–100）
- topic_fit：人源化小鼠模型开发/表征
- eval_fit：免疫药物疗效/毒性/PK 评估
- evidence_strength：全文是否含可引用的定量结果与实验设计
- audience_value：是否适合每周科普简报（一个清晰故事）

## 输出
{
  "rankings": [{"pmid":"...","total_score":80,"topic_fit":20,"eval_fit":20,
                "evidence_strength":20,"audience_value":20,"one_line_reason":"..."}],
  "selected_pmid": "...",
  "selection_rationale": "为何这篇适合作为本周唯一主线（2-3句）",
  "story_hook": "一句话故事钩子（中文）"
}"""


def _ncbi_params(extra: dict | None = None) -> dict:
    p = {"email": NCBI_EMAIL}
    if NCBI_APIKEY:
        p["api_key"] = NCBI_APIKEY
    if extra:
        p.update(extra)
    return p


def _http_get(url: str, params: dict, timeout: int = 90, retries: int = 4) -> requests.Response:
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=_ncbi_params(params), timeout=timeout)
            r.raise_for_status()
            return r
        except (requests.RequestException, ValueError) as e:
            last_err = e
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"NCBI request failed after {retries} tries: {last_err}")


def _get_json(url: str, params: dict) -> dict:
    """Read NCBI JSON defensively.

    NCBI occasionally returns JSON text containing raw control characters,
    which `requests.Response.json()` rejects. Clean those characters once
    before failing the pipeline.
    """
    r = _http_get(url, params)
    try:
        return r.json()
    except ValueError as first_err:
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", r.text)
        try:
            return json.loads(cleaned)
        except ValueError:
            preview = r.text[:200].replace("\n", "\\n")
            raise RuntimeError(f"NCBI JSON parse failed: {first_err}; preview={preview!r}") from first_err


def search_recent(days: int = 30, max_results: int = TOP_CANDIDATES) -> list[str]:
    min_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    query = (
        f"({SEARCH_QUERY}) AND (review[pt] OR clinical trial[pt] OR journal article[pt])"
        f" AND {FULLTEXT_FILTER}"
    )
    data = _get_json(f"{NCBI_BASE}/esearch.fcgi", {
        "db": "pubmed",
        "term": query,
        "mindate": min_date,
        "datetype": "pdat",
        "retmax": max_results,
        "sort": "relevance",
        "retmode": "json",
    })
    pmids = data.get("esearchresult", {}).get("idlist", [])
    print(f"  PubMed+fulltext search ({days}d, top {max_results}): {len(pmids)} hits")
    return pmids


def _parse_article_node(art: ET.Element) -> dict:
    def _txt(node, tag, default=""):
        el = node.find(f".//{tag}") if node is not None else None
        return (el.text or "").strip() if el is not None else default

    pmid_el = art.find(".//PMID")
    pmid = (pmid_el.text or "").strip() if pmid_el is not None else ""

    abstract_parts = []
    for ab in art.findall(".//AbstractText"):
        label = ab.get("Label", "")
        text = (ab.text or "").strip()
        if label:
            abstract_parts.append(f"{label}: {text}")
        elif text:
            abstract_parts.append(text)
    abstract = " ".join(abstract_parts)

    authors = []
    for auth in art.findall(".//Author")[:3]:
        ln = _txt(auth, "LastName")
        fn = _txt(auth, "ForeName")
        if ln:
            authors.append(f"{ln} {fn}".strip())
    author_str = ", ".join(authors) + (" et al." if len(authors) >= 3 else "")

    doi = ""
    pmcid = ""
    for aid in art.findall(".//ArticleId"):
        id_type = aid.get("IdType", "")
        val = (aid.text or "").strip()
        if id_type == "doi":
            doi = val
        elif id_type == "pmc":
            pmcid = val

    return {
        "pmid": pmid,
        "title": _txt(art, "ArticleTitle"),
        "abstract": abstract,
        "authors": author_str,
        "journal": _txt(art, "Title"),
        "year": _txt(art, "Year") or _txt(art, "MedlineDate")[:4],
        "doi": doi,
        "pmcid": pmcid,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "full_text": "",
        "full_text_chars": 0,
        "full_text_source": "",
    }


def fetch_articles(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    time.sleep(0.4)
    xml_text = _http_get(f"{NCBI_BASE}/efetch.fcgi", {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
    }).text
    root = ET.fromstring(xml_text)
    by_pmid = {}
    for art in root.findall(".//PubmedArticle"):
        rec = _parse_article_node(art)
        if rec["pmid"]:
            by_pmid[rec["pmid"]] = rec
    return [by_pmid[p] for p in pmids if p in by_pmid]


def fetch_article(pmid: str) -> dict:
    articles = fetch_articles([pmid])
    if not articles:
        raise RuntimeError(f"PMID {pmid} not found on PubMed")
    return articles[0]


def resolve_pmc_ids(pmids: list[str]) -> dict[str, str]:
    """Map PMID → PMC numeric id (no PMC prefix)."""
    if not pmids:
        return {}
    mapping: dict[str, str] = {}
    chunk = 10
    for i in range(0, len(pmids), chunk):
        batch = pmids[i : i + chunk]
        time.sleep(0.35)
        try:
            data = _get_json(f"{NCBI_BASE}/elink.fcgi", {
                "dbfrom": "pubmed",
                "db": "pmc",
                "id": ",".join(batch),
                "retmode": "json",
            })
        except RuntimeError as exc:
            print(f"  [WARN] NCBI elink failed for PMID batch {batch[0]}..{batch[-1]}: {exc}")
            continue
        for linkset in data.get("linksets", []):
            src = str(linkset.get("ids", [""])[0])
            for ldb in linkset.get("linksetdbs", []):
                if ldb.get("linkname") == "pubmed_pmc":
                    ids = ldb.get("links", [])
                    if ids:
                        mapping[src] = str(ids[0])
    return mapping


def _jats_to_text(xml_text: str) -> str:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ""
    chunks: list[str] = []
    for path in (".//article-title", ".//abstract//p", ".//sec-title", ".//body//p"):
        for el in root.findall(path):
            t = " ".join("".join(el.itertext()).split())
            if len(t) > 20:
                chunks.append(t)
    if not chunks:
        chunks = [" ".join("".join(root.itertext()).split())]
    text = "\n\n".join(chunks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_pmc_fulltext(pmc_id: str) -> str:
    time.sleep(0.4)
    xml_text = _http_get(f"{NCBI_BASE}/efetch.fcgi", {
        "db": "pmc",
        "id": pmc_id,
        "retmode": "xml",
    }, timeout=120).text
    return _jats_to_text(xml_text)


def attach_full_texts(articles: list[dict]) -> list[dict]:
    pmids = [a["pmid"] for a in articles]
    pmc_map = resolve_pmc_ids(pmids)
    enriched = []
    for art in articles:
        rec = dict(art)
        pmc_id = pmc_map.get(rec["pmid"]) or (rec.get("pmcid") or "").replace("PMC", "")
        if not pmc_id:
            enriched.append(rec)
            continue
        try:
            full = fetch_pmc_fulltext(pmc_id)
            rec["pmcid"] = f"PMC{pmc_id}"
            rec["full_text"] = full
            rec["full_text_chars"] = len(full)
            rec["full_text_source"] = "pmc"
        except Exception as e:
            print(f"  [WARN] PMC fetch failed for PMID {rec['pmid']}: {e}")
        enriched.append(rec)
    return enriched


def filter_fulltext_candidates(articles: list[dict]) -> list[dict]:
    ok = [a for a in articles if a.get("full_text_chars", 0) >= MIN_FULLTEXT_CHARS]
    print(f"  Full-text eligible (≥{MIN_FULLTEXT_CHARS} chars): {len(ok)}/{len(articles)}")
    return ok


def find_related_references(
    main_pmid: str,
    count: int = RELATED_REF_COUNT,
    fallback_pool: list[dict] | None = None,
) -> list[dict]:
    """PubMed neighbor similarity → related reading list; pool fallback if empty."""
    neighbor_pmids: list[str] = []
    try:
        time.sleep(0.35)
        data = _get_json(f"{NCBI_BASE}/elink.fcgi", {
            "dbfrom": "pubmed",
            "db": "pubmed",
            "id": main_pmid,
            "linkname": "pubmed_pubmed",
            "cmd": "neighbor_score",
            "retmode": "json",
        })
        for linkset in data.get("linksets", []):
            for ldb in linkset.get("linksetdbs", []):
                if ldb.get("linkname") == "pubmed_pubmed":
                    for lid in ldb.get("links", []):
                        s = str(lid)
                        if s != main_pmid and s not in neighbor_pmids:
                            neighbor_pmids.append(s)
    except Exception as e:
        print(f"  [WARN] PubMed neighbor lookup failed: {e}")

    refs: list[dict] = []
    if neighbor_pmids:
        refs = fetch_articles(neighbor_pmids[: count * 2])[:count]

    if len(refs) < count and fallback_pool:
        for c in fallback_pool:
            if c["pmid"] == main_pmid:
                continue
            if any(r["pmid"] == c["pmid"] for r in refs):
                continue
            refs.append({
                "pmid": c["pmid"],
                "title": c["title"],
                "authors": c["authors"],
                "journal": c["journal"],
                "year": c["year"],
                "doi": c.get("doi", ""),
                "url": c["url"],
                "relation": "same_search_pool",
            })
            if len(refs) >= count:
                break

    return [
        {
            "pmid": r["pmid"],
            "title": r["title"],
            "authors": r["authors"],
            "journal": r["journal"],
            "year": r["year"],
            "doi": r.get("doi", ""),
            "url": r["url"],
            "relation": r.get("relation", "pubmed_similarity"),
        }
        for r in refs[:count]
    ]


def _strip_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        if "```" in raw:
            raw = raw[: raw.rfind("```")]
    return raw.strip()


def _call_scorer(prompt: str) -> str:
    from openai import OpenAI

    providers = [
        ("deepseek", "deepseek-chat", os.getenv("DEEPSEEK_API_KEY", ""), "https://api.deepseek.com"),
        ("kimi", "moonshot-v1-32k", os.getenv("KIMI_API_KEY", ""), "https://api.moonshot.cn/v1"),
        ("gemini", "gemini-2.5-flash", os.getenv("GEMINI_API_KEY", ""),
         os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")),
    ]
    last_err = None
    for name, model, key, base in providers:
        if not key:
            continue
        try:
            client = OpenAI(api_key=key, base_url=base)
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SCORER_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=3500,
                temperature=0,
            )
            print(f"  Article scorer: {name}")
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [WARN] {name} scorer failed: {e}")
            last_err = e
    raise RuntimeError(f"All scorers failed: {last_err}")


def _build_scorer_prompt(candidates: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(candidates, 1):
        excerpt = (c.get("full_text") or c.get("abstract") or "")[:3500]
        blocks.append(
            f"### 候选 {i}\n"
            f"PMID: {c['pmid']}\n"
            f"PMCID: {c.get('pmcid', 'n/a')}\n"
            f"Title: {c['title']}\n"
            f"Journal: {c['journal']} ({c['year']})\n"
            f"Full-text chars: {c.get('full_text_chars', 0)}\n"
            f"Abstract: {(c.get('abstract') or '')[:1200]}\n"
            f"Full-text excerpt:\n{excerpt}\n"
        )
    return (
        "本周只讲一个故事。请从下列【有全文】候选中选出最佳主线文献。\n\n"
        + "\n".join(blocks)
    )


def score_candidates(candidates: list[dict]) -> dict:
    raw = _call_scorer(_build_scorer_prompt(candidates))
    try:
        return json.loads(_strip_json(raw))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Scorer invalid JSON: {e}\n{raw[:500]}")


def _pick_from_ai_score(
    score_result: dict,
    candidates: list[dict],
    used_pmids: set[str],
) -> tuple[str, dict]:
    valid_pmids = {c["pmid"] for c in candidates}
    ranked = sorted(
        [r for r in score_result.get("rankings", []) if str(r.get("pmid", "")) in valid_pmids],
        key=lambda r: float(r.get("total_score", 0)),
        reverse=True,
    )
    selected = str(score_result.get("selected_pmid", ""))
    if selected in valid_pmids and selected not in used_pmids:
        return selected, score_result
    for row in ranked:
        pmid = str(row["pmid"])
        if pmid not in used_pmids:
            score_result["selected_pmid"] = pmid
            return pmid, score_result
    if ranked:
        pmid = str(ranked[0]["pmid"])
        score_result["selected_pmid"] = pmid
        score_result["selection_rationale"] = "Reusing highest-ranked full-text article."
        return pmid, score_result
    raise RuntimeError("No valid AI ranking among full-text candidates")


def _search_with_fulltext(days_list: list[int]) -> tuple[list[str], list[dict]]:
    for days in days_list:
        pmids = search_recent(days=days)
        if not pmids:
            continue
        articles = attach_full_texts(fetch_articles(pmids))
        eligible = filter_fulltext_candidates(articles)
        if eligible:
            return pmids, eligible
    return [], []


def get_weekly_article(cache_path: str | None = None) -> dict:
    """
    AI-native weekly pick with mandatory PMC full text.
    Returns one main story + related_references for slide 6 / social footer.
    """
    cache_file = Path(cache_path) if cache_path else None
    used_pmids: set[str] = set()
    cache: dict = {"used_pmids": [], "selection_history": []}

    if cache_file and cache_file.exists():
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
        used_pmids = set(cache.get("used_pmids", []))

    _, candidates = _search_with_fulltext([30, 90, 180, 365])
    if not candidates:
        raise RuntimeError(
            "No PMC full-text candidates found. "
            "Try widening search or check NCBI connectivity."
        )

    # Prefer unused PMIDs for scoring pool
    pool = [c for c in candidates if c["pmid"] not in used_pmids] or candidates

    score_result = None
    chosen_pmid = None
    selection_mode = "ai_native_fulltext"

    try:
        score_result = score_candidates(pool)
        chosen_pmid, score_result = _pick_from_ai_score(score_result, pool, used_pmids)
        print(f"  AI selected PMID {chosen_pmid} (full-text story)")
        if score_result.get("story_hook"):
            print(f"  Story hook: {score_result['story_hook']}")
    except Exception as e:
        print(f"  [WARN] AI scorer failed ({e}); fallback to first unused full-text")
        selection_mode = "fulltext_relevance_fallback"
        for c in pool:
            if c["pmid"] not in used_pmids:
                chosen_pmid = c["pmid"]
                break
        if not chosen_pmid:
            chosen_pmid = pool[0]["pmid"]

    article = next((c for c in pool if c["pmid"] == chosen_pmid), None)
    if article is None:
        article = attach_full_texts([fetch_article(chosen_pmid)])[0]

    if article.get("full_text_chars", 0) < MIN_FULLTEXT_CHARS:
        raise RuntimeError(
            f"Selected PMID {chosen_pmid} lacks sufficient full text "
            f"({article.get('full_text_chars', 0)} chars)"
        )

    related = find_related_references(chosen_pmid, RELATED_REF_COUNT, fallback_pool=pool)
    article["related_references"] = related
    article["narrative_policy"] = {
        "mode": "single_story",
        "main_pmid": chosen_pmid,
        "related_count": len(related),
    }
    article["selection"] = {
        "mode": selection_mode,
        "selected_pmid": chosen_pmid,
        "rationale": (score_result or {}).get("selection_rationale", ""),
        "story_hook": (score_result or {}).get("story_hook", ""),
        "rankings": (score_result or {}).get("rankings", []),
        "full_text_chars": article.get("full_text_chars", 0),
        "pmcid": article.get("pmcid", ""),
        "selected_at": datetime.now().isoformat(timespec="seconds"),
    }

    if cache_file:
        used_pmids.add(chosen_pmid)
        history = cache.get("selection_history", [])
        history.append({
            "pmid": chosen_pmid,
            "title": article["title"],
            "pmcid": article.get("pmcid", ""),
            "full_text_chars": article.get("full_text_chars", 0),
            "story_hook": article["selection"].get("story_hook", ""),
            "related_pmids": [r["pmid"] for r in related],
            "mode": selection_mode,
            "at": article["selection"]["selected_at"],
        })
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps({
                "used_pmids": sorted(used_pmids),
                "selection_history": history[-52:],
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return article


if __name__ == "__main__":
    cache = sys.argv[1] if len(sys.argv) > 1 else "outputs/weekly_cache.json"
    picked = get_weekly_article(cache_path=cache)
    # Don't dump full_text to stdout (too large)
    preview = {k: v for k, v in picked.items() if k != "full_text"}
    preview["full_text_chars"] = picked.get("full_text_chars", 0)
    print(json.dumps(preview, ensure_ascii=False, indent=2))
