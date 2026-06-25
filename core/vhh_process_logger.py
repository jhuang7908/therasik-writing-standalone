"""
VHH Pipeline （）

：
-  pipeline 
-  replay log（）
- 
-  JSON 

：
- 
- 
- Pipeline 
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ProcessStep:
    """"""
    step_id: str
    title: str
    detail: str
    timestamp: str
    extra: Optional[Dict[str, Any]] = None


class VHHProcessLogger:
    """VHH Pipeline （）"""
    
    def __init__(self):
        """"""
        self._steps: List[ProcessStep] = []
    
    def log(
        self,
        step_id: str,
        title: str,
        detail: str,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        
        
        Args:
            step_id: （ "step1_imgt"）
            title: （ "IMGT segmentation"）
            detail: 
            extra: （）
        """
        ts = datetime.now().isoformat(timespec="seconds")
        self._steps.append(
            ProcessStep(
                step_id=step_id,
                title=title,
                detail=detail,
                timestamp=ts,
                extra=extra or {},
            )
        )
    
    def to_list(self) -> List[Dict[str, Any]]:
        """"""
        return [asdict(s) for s in self._steps]
    
    def to_dict(self) -> Dict[str, Any]:
        """（）"""
        return {
            "steps": self.to_list(),
            "total_steps": len(self._steps),
            "generated_at": datetime.now().isoformat(),
        }
    
    def save(self, output_path):
        """"""
        import json
        from pathlib import Path
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        log_data = self.to_dict()
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Process log saved: {output_path}")
    
    def load(self, input_path) -> bool:
        """"""
        import json
        from pathlib import Path
        
        input_path = Path(input_path)
        if not input_path.exists():
            return False
        
        with open(input_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)
        
        steps_data = log_data.get("steps", [])
        self._steps = [
            ProcessStep(
                step_id=s.get("step_id", ""),
                title=s.get("title", ""),
                detail=s.get("detail", ""),
                timestamp=s.get("timestamp", ""),
                extra=s.get("extra", {}),
            )
            for s in steps_data
        ]
        
        return True
    
    def replay(self, callback: Optional[callable] = None):
        """
        
        
        Args:
            callback: ， (step_id, title, detail, timestamp, extra) 
        """
        for step in self._steps:
            if callback:
                callback(
                    step.step_id,
                    step.title,
                    step.detail,
                    step.timestamp,
                    step.extra,
                )
            else:
                # 
                print(f"[{step.timestamp}] ({step.step_id}) {step.title}")
                if step.detail:
                    print(f"    {step.detail}")
                if step.extra:
                    print(f"    Extra: {step.extra}")


def format_process_log_block(steps: List[Dict[str, Any]]) -> str:
    """
     process_log 。
    
    Args:
        steps: （）
    
    Returns:
        Markdown 
    """
    if not steps:
        return "。"
    
    lines = []
    for s in steps:
        ts = s.get("timestamp", "")
        step_id = s.get("step_id", "")
        title = s.get("title", "")
        detail = s.get("detail", "")
        
        lines.append(f"- **[{ts}]** ({step_id}) {title}")
        if detail:
            lines.append(f"  {detail}")
        
        extra = s.get("extra", {})
        if extra:
            for key, value in extra.items():
                lines.append(f"  - {key}: {value}")
    
    return "\n".join(lines)


def create_process_logger() -> VHHProcessLogger:
    """（）"""
    return VHHProcessLogger()


# 
if __name__ == "__main__":
    # 
    logger = VHHProcessLogger()
    
    # 
    logger.log(
        "step1_imgt",
        "IMGT segmentation",
        " ANARCI/IMGT  VHH 。",
    )
    
    logger.log(
        "step2_germline",
        "Germline library scan",
        f" 150  VH3 germline ， FR identity。",
        extra={"germline_count": 150},
    )
    
    logger.log(
        "step3_humanization",
        "Humanization strategy",
        "（Conservative/Balanced/Aggressive）。",
        extra={"strategies": ["conservative", "balanced", "aggressive"]},
    )
    
    logger.log(
        "step4_qa",
        "QA validation",
        " QA v3.5 ，。",
        extra={"qa_version": "v3.5", "status": "passed"},
    )
    
    # 
    steps_list = logger.to_list()
    print("\n" + "="*60)
    print("Process Log (as list):")
    print("="*60)
    import json
    print(json.dumps(steps_list, indent=2, ensure_ascii=False))
    
    # 
    print("\n" + "="*60)
    print("Process Log (formatted for report):")
    print("="*60)
    formatted = format_process_log_block(steps_list)
    print(formatted)
    
    # 
    print("\n" + "="*60)
    print("Replaying logs:")
    print("="*60)
    logger.replay()
