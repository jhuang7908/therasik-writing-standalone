"""

"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from core.audit import AuditLogger, AuditLogEntry, get_audit_logger


class TestAuditLogger:
    """"""
    
    def test_audit_logger_initialization(self):
        """"""
        with tempfile.TemporaryDirectory as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            assert logger.log_dir.exists
    
    def test_log_humanization(self):
        """"""
        with tempfile.TemporaryDirectory as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            result = {
                'success': True,
                'best_match': {
                    'template': {'template_id': 'TEST_001'},
                    'scoring': {'combined_score': 0.85}
                }
            }
            output_id = logger.log_humanization(
                sequence="QVQLVESGGG...",
                result=result,
                panel="A",
                top_k=3
            )
            assert output_id is not None
            assert len(output_id) > 0
    
    def test_log_fallback(self):
        """fallback"""
        with tempfile.TemporaryDirectory as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            logger.log_fallback(
                sequence="QVQLVESGGG...",
                fallback_type="numbering",
                fallback_reason="ANARCII failed"
            )
            # 
            log_file = logger._get_log_file
            assert log_file.exists
    
    def test_log_error(self):
        """"""
        with tempfile.TemporaryDirectory as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            logger.log_error(
                sequence="QVQLVESGGG...",
                error_message="Test error",
                error_code="TEST_ERROR"
            )
            log_file = logger._get_log_file
            assert log_file.exists
    
    def test_sequence_hashing(self):
        """"""
        with tempfile.TemporaryDirectory as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            seq1 = "QVQLVESGGG..."
            seq2 = "QVQLVESGGG..."
            hash1 = logger._hash_sequence(seq1)
            hash2 = logger._hash_sequence(seq2)
            assert hash1 == hash2  # 
    
    def test_query_logs(self):
        """"""
        with tempfile.TemporaryDirectory as tmpdir:
            logger = AuditLogger(log_dir=Path(tmpdir))
            # 
            logger.log_humanization(
                sequence="TEST_SEQ_1",
                result={'success': True, 'best_match': {}},
                project_name="test_project"
            )
            logger.log_humanization(
                sequence="TEST_SEQ_2",
                result={'success': True, 'best_match': {}},
                project_name="other_project"
            )
            # 
            logs = logger.query_logs(project_name="test_project")
            assert len(logs) >= 1
            assert all(log['project_name'] == 'test_project' for log in logs)
    
    def test_get_audit_logger_singleton(self):
        """"""
        logger1 = get_audit_logger
        logger2 = get_audit_logger
        assert logger1 is logger2  # 


















