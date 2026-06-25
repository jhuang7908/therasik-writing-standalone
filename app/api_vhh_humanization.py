"""
VHH Humanization HTTP API

RESTful API，humanize_vhh
FastAPIFlask
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional

# 
PROJECT_ROOT = Path(__file__).resolve.parents[1]
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization import humanize_vhh
from core.reporting import generate_markdown_report, generate_html_report, save_report
from core.config import get_config


# FastAPI，Flask
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    try:
        from flask import Flask, request, jsonify
        from flask_cors import CORS
        HAS_FLASK = True
    except ImportError:
        HAS_FLASK = False


# ==================== Pydantic Models (FastAPI) ====================

if HAS_FASTAPI:
    class HumanizeRequest(BaseModel):
        """"""
        seq: str = Field(..., description="VHH")
        panel: str = Field(default="A", description="：A/B/C/all")
        top_k: int = Field(default=3, ge=1, le=20, description="k")
        source: Optional[str] = Field(default=None, description="VHH")
    
    class HumanizeResponse(BaseModel):
        """"""
        success: bool
        result: Optional[Dict[str, Any]] = None
        error: Optional[str] = None


# ==================== FastAPI Implementation ====================

if HAS_FASTAPI:
    app = FastAPI(
        title="VHH Humanization API",
        description="VHHAPI",
        version="1.0.0"
    )
    
    # CORS
    cfg = get_config
    if cfg.api.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    @app.get("/")
    async def root:
        """API"""
        return {
            "service": "VHH Humanization API",
            "version": "1.0.0",
            "endpoints": {
                "/humanize": "POST - VHH",
                "/health": "GET - ",
                "/docs": "GET - API（Swagger）"
            }
        }
    
    @app.get("/health")
    async def health:
        """"""
        return {"status": "healthy"}
    
    @app.post("/humanize", response_model=HumanizeResponse)
    async def humanize_vhh_api(req: HumanizeRequest):
        """
        VHH
        
        Args:
            req: ，VHH
        
        Returns:
            
        """
        try:
            result = humanize_vhh(
                req.seq,
                panel=req.panel,
                top_k=req.top_k,
                source=req.source
            )
            
            if result.get("success"):
                return HumanizeResponse(success=True, result=result)
            else:
                return HumanizeResponse(
                    success=False,
                    error=result.get("error", "Unknown error")
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/humanize/report")
    async def humanize_vhh_report(
        req: HumanizeRequest,
        format: str = "markdown"
    ):
        """
        VHH
        
        Args:
            req: 
            format: （markdown/html）
        
        Returns:
            
        """
        try:
            result = humanize_vhh(
                req.seq,
                panel=req.panel,
                top_k=req.top_k,
                source=req.source
            )
            
            if not result.get("success"):
                raise HTTPException(
                    status_code=400,
                    detail=result.get("error", "Humanization failed")
                )
            
            if format == "html":
                content = generate_html_report(result)
                return HTMLResponse(content=content)
            else:
                content = generate_markdown_report(result)
                return PlainTextResponse(content=content)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# ==================== Flask Implementation ====================

elif HAS_FLASK:
    app = Flask(__name__)
    
    # CORS
    cfg = get_config
    if cfg.api.cors_enabled:
        CORS(app)
    
    @app.route("/", methods=["GET"])
    def root:
        """API"""
        return jsonify({
            "service": "VHH Humanization API",
            "version": "1.0.0",
            "endpoints": {
                "/humanize": "POST - VHH",
                "/health": "GET - "
            }
        })
    
    @app.route("/health", methods=["GET"])
    def health:
        """"""
        return jsonify({"status": "healthy"})
    
    @app.route("/humanize", methods=["POST"])
    def humanize_vhh_api:
        """
        VHH
        
        Request Body (JSON):
        {
            "seq": "QVQLVESGGG...",
            "panel": "A",
            "top_k": 3,
            "source": "llama"
        }
        
        Returns:
            JSON
        """
        try:
            data = request.get_json
            if not data:
                return jsonify({"success": False, "error": "Missing request body"}), 400
            
            seq = data.get("seq")
            if not seq:
                return jsonify({"success": False, "error": "Missing 'seq' field"}), 400
            
            panel = data.get("panel", "A")
            top_k = data.get("top_k", 3)
            source = data.get("source")
            
            result = humanize_vhh(seq, panel=panel, top_k=top_k, source=source)
            
            if result.get("success"):
                return jsonify({"success": True, "result": result})
            else:
                return jsonify({
                    "success": False,
                    "error": result.get("error", "Unknown error")
                }), 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route("/humanize/report", methods=["POST"])
    def humanize_vhh_report:
        """
        VHH
        
        Query Parameters:
            format: markdown (default) or html
        
        Request Body:  /humanize
        """
        try:
            data = request.get_json
            if not data:
                return jsonify({"success": False, "error": "Missing request body"}), 400
            
            seq = data.get("seq")
            if not seq:
                return jsonify({"success": False, "error": "Missing 'seq' field"}), 400
            
            panel = data.get("panel", "A")
            top_k = data.get("top_k", 3)
            source = data.get("source")
            format_type = request.args.get("format", "markdown")
            
            result = humanize_vhh(seq, panel=panel, top_k=top_k, source=source)
            
            if not result.get("success"):
                return jsonify({
                    "success": False,
                    "error": result.get("error", "Humanization failed")
                }), 400
            
            if format_type == "html":
                content = generate_html_report(result)
                return content, 200, {"Content-Type": "text/html"}
            else:
                content = generate_markdown_report(result)
                return content, 200, {"Content-Type": "text/plain"}


# ====================  ====================

def run_api(host: Optional[str] = None, port: Optional[int] = None, debug: Optional[bool] = None):
    """
    API
    
    Args:
        host: （config）
        port: （config）
        debug: （config）
    """
    cfg = get_config
    
    host = host or cfg.api.host
    port = port or cfg.api.port
    debug = debug if debug is not None else cfg.api.debug
    
    if HAS_FASTAPI:
        import uvicorn
        print(f"[INFO] FastAPI: http://{host}:{port}")
        print(f"[INFO] API: http://{host}:{port}/docs")
        uvicorn.run(app, host=host, port=port, log_level="info" if not debug else "debug")
    elif HAS_FLASK:
        print(f"[INFO] Flask: http://{host}:{port}")
        app.run(host=host, port=port, debug=debug)
    else:
        raise RuntimeError(
            "FastAPIFlask。"
            "FastAPI: pip install fastapi uvicorn"
            "Flask: pip install flask flask-cors"
        )


if __name__ == "__main__":
    run_api


















