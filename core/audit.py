"""


，GMP/GLP
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from core.utils.config_loader import get_config_lazy


@dataclass
class AuditLogEntry:
    """"""
    event_type: str  # "humanization", "fallback", "error"
    timestamp: str
    sequence_hash: str  # SHA256
    sequence_length: int
    template_library_version: str
    config_version: str
    project_name: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # 
    panel: Optional[str] = None
    top_k: Optional[int] = None
    best_template_id: Optional[str] = None
    combined_score: Optional[float] = None
    
    # Fallback
    fallback_type: Optional[str] = None
    fallback_reason: Optional[str] = None
    
    # 
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # ID（）
    output_id: Optional[str] = None
    
    # 
    metadata: Optional[Dict[str, Any]] = None


class AuditLogger:
    """"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        
        
        Args:
            log_dir: （None，）
        """
        if log_dir is None:
            cfg = get_config_lazy()
            # 
            if hasattr(cfg, 'project') and hasattr(cfg.project, 'audit_log_dir'):
                log_dir = Path(cfg.project.audit_log_dir)
            else:
                log_dir = Path("audit_logs")
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_log_file(self, date: Optional[str] = None) -> Path:
        """（）"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"audit_{date}.jsonl"
    
    def _hash_sequence(self, sequence: str) -> str:
        """SHA256"""
        return hashlib.sha256(sequence.encode('utf-8')).hexdigest()[:16]
    
    def log_humanization(
        self,
        sequence: str,
        result: Dict[str, Any],
        panel: str = "A",
        top_k: int = 3,
        project_name: str = "default",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        
        
        Args:
            sequence: VHH
            result: humanize_vhh()
            panel: 
            top_k: k
            project_name: 
            user_id: ID（）
            session_id: ID（）
            metadata: 
        
        Returns:
            ID（）
        """
        seq_hash = self._hash_sequence(sequence)
        timestamp = datetime.now().isoformat()
        
        # ID
        output_id = f"{seq_hash}_{int(datetime.now().timestamp())}"
        
        # 
        template_version = self._get_template_library_version()
        config_version = self._get_config_version()
        
        # 
        best_match = result.get("best_match", {})
        template = best_match.get("template", {})
        scoring = best_match.get("scoring", {})
        
        entry = AuditLogEntry(
            event_type="humanization",
            timestamp=timestamp,
            sequence_hash=seq_hash,
            sequence_length=len(sequence),
            template_library_version=template_version,
            config_version=config_version,
            project_name=project_name,
            user_id=user_id,
            session_id=session_id,
            panel=panel,
            top_k=top_k,
            best_template_id=template.get("template_id"),
            combined_score=scoring.get("combined_score"),
            output_id=output_id,
            metadata=metadata
        )
        
        # fallback
        if result.get("quality_flags", {}).get("cdr_compatibility_fallback"):
            self.log_fallback(
                sequence=sequence,
                fallback_type="cdr_compatibility",
                fallback_reason="CDR compatibility score below threshold",
                project_name=project_name,
                user_id=user_id,
                session_id=session_id
            )
        
        self._write_entry(entry)
        return output_id
    
    def log_fallback(
        self,
        sequence: str,
        fallback_type: str,
        fallback_reason: str,
        project_name: str = "default",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """fallback"""
        seq_hash = self._hash_sequence(sequence)
        timestamp = datetime.now().isoformat()
        
        entry = AuditLogEntry(
            event_type="fallback",
            timestamp=timestamp,
            sequence_hash=seq_hash,
            sequence_length=len(sequence),
            template_library_version=self._get_template_library_version(),
            config_version=self._get_config_version(),
            project_name=project_name,
            user_id=user_id,
            session_id=session_id,
            fallback_type=fallback_type,
            fallback_reason=fallback_reason,
            metadata=metadata
        )
        
        self._write_entry(entry)
    
    def log_error(
        self,
        sequence: str,
        error_message: str,
        error_code: str,
        project_name: str = "default",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """"""
        seq_hash = self._hash_sequence(sequence)
        timestamp = datetime.now().isoformat()
        
        entry = AuditLogEntry(
            event_type="error",
            timestamp=timestamp,
            sequence_hash=seq_hash,
            sequence_length=len(sequence),
            template_library_version=self._get_template_library_version(),
            config_version=self._get_config_version(),
            project_name=project_name,
            user_id=user_id,
            session_id=session_id,
            error_message=error_message,
            error_code=error_code,
            metadata=metadata
        )
        
        self._write_entry(entry)
    
    def _write_entry(self, entry: AuditLogEntry):
        """（JSONL）"""
        log_file = self._get_log_file()
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    
    def _get_template_library_version(self) -> str:
        """"""
        try:
            cfg = get_config_lazy()
            # 
            template_path = cfg.paths.human_templates
            if template_path.exists():
                with open(template_path, encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        # 
                        if '_library_version' in data[0]:
                            return data[0]['_library_version']
                        # 
                        mtime = template_path.stat().st_mtime
                        return f"mtime_{int(mtime)}"
        except Exception:
            pass
        return "unknown"
    
    def _get_config_version(self) -> str:
        """"""
        try:
            cfg = get_config_lazy()
            config_path = Path("config.yaml")
            if config_path.exists():
                mtime = config_path.stat().st_mtime
                return f"mtime_{int(mtime)}"
        except Exception:
            pass
        return "unknown"
    
    def query_logs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        project_name: Optional[str] = None,
        event_type: Optional[str] = None,
        sequence_hash: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        
        
        Args:
            start_date: （YYYY-MM-DD）
            end_date: （YYYY-MM-DD）
            project_name: 
            event_type: 
            sequence_hash: 
        
        Returns:
            
        """
        results = []
        
        # 
        if start_date and end_date:
            from datetime import datetime as dt
            start = dt.strptime(start_date, "%Y-%m-%d")
            end = dt.strptime(end_date, "%Y-%m-%d")
            dates = [
                (start + timedelta(days=x)).strftime("%Y-%m-%d")
                for x in range((end - start).days + 1)
            ]
        else:
            dates = [datetime.now().strftime("%Y-%m-%d")]
        
        for date in dates:
            log_file = self._get_log_file(date)
            if not log_file.exists():
                continue
            
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line.strip())
                    
                    # 
                    if project_name and entry.get("project_name") != project_name:
                        continue
                    if event_type and entry.get("event_type") != event_type:
                        continue
                    if sequence_hash and entry.get("sequence_hash") != sequence_hash:
                        continue
                    
                    results.append(entry)
        
        return results


# 
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """（）"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger

