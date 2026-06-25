#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Framework Selection Rationale Report Renderer

Renders the "Framework Selection Rationale" section for CRO reports (CN and EN).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.framework_selection.selector import select_frameworks


def render_framework_selection_section_cn(
    query_numbering: List[Dict[str, Any]],
    selection_result: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Render Framework Selection Rationale section (Chinese).
    
    Args:
        query_numbering: ANARCII numbering output
        selection_result: Optional pre-computed selection result (if None, will compute)
    
    Returns:
        HTML string for the section
    """
    if selection_result is None:
        selection_result = select_frameworks(query_numbering)
    
    top3_vh = selection_result.get("top3_vh", [])
    top3_vl = selection_result.get("top3_vl", [])
    final_choice = selection_result.get("final_choice", {})
    triggered_rules = selection_result.get("triggered_rules", [])
    
    html = """
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                
                <div class="strategy-box" style="margin-bottom: 30px;">
                    <p style="margin: 0; color: #7f8c8d; font-size: 0.95em;">
                        <strong>：</strong> = FR1–FR3 only（FR4 ）。
                        FR4/J ，。
                    </p>
                </div>
    """
    
    # Top3 VH candidates table
    if top3_vh:
        html += """
                <h3 style="margin-top: 20px; color: #34495e;">VH （Top 3）</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th></th>
                            <th>Framework ID</th>
                            <th>FR Identity</th>
                            <th>Canonical Match</th>
                            <th>Tags</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        for i, cand in enumerate(top3_vh[:3], 1):
            fw_id = cand.get("framework_id", "N/A")
            fr_seq = cand.get("fr_sequence_fr1_fr3", "TODO")
            canonical = cand.get("canonical", {})
            tags = ", ".join(cand.get("tags", [])) or "—"
            
            # Get FR identity from score details
            score_details = cand.get("_score_details", {})
            fr_identity_val = score_details.get("fr_identity", None)
            fr_identity = f"{fr_identity_val:.3f}" if fr_identity_val is not None else "N/A"
            
            cdr1_class = canonical.get("cdr1", {}).get("class", "TODO")
            cdr2_class = canonical.get("cdr2", {}).get("class", "TODO")
            canonical_match = f"{cdr1_class}/{cdr2_class}" if cdr1_class != "TODO" and cdr2_class != "TODO" else "TODO"
            
            # Build reason string with all score components
            reason_parts = []
            if fr_identity != "N/A":
                reason_parts.append(f"FR identity: {fr_identity}")
            canonical_status = score_details.get("canonical_status", "")
            if canonical_status and "Match" in canonical_status:
                reason_parts.append("Canonical match")
            cdr3_penalty = score_details.get("cdr3_penalty", 0)
            if cdr3_penalty > 0:
                reason_parts.append(f"CDR3: -{cdr3_penalty:.3f}")
            reason = "; ".join(reason_parts) if reason_parts else "FR1-FR3"
            
            html += f"""
                        <tr>
                            <td><strong>{i}</strong></td>
                            <td><code>{fw_id}</code></td>
                            <td>{fr_identity}</td>
                            <td>{canonical_match}</td>
                            <td>{tags}</td>
                            <td>{reason}</td>
                        </tr>"""
        
        html += """
                    </tbody>
                </table>"""
    
    # Top3 VL candidates table
    if top3_vl:
        html += """
                <h3 style="margin-top: 30px; color: #34495e;">VL （Top 3）</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th></th>
                            <th>Framework ID</th>
                            <th>FR Identity</th>
                            <th>Canonical Match</th>
                            <th>Tags</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        for i, cand in enumerate(top3_vl[:3], 1):
            fw_id = cand.get("framework_id", "N/A")
            fr_seq = cand.get("fr_sequence_fr1_fr3", "TODO")
            canonical = cand.get("canonical", {})
            tags = ", ".join(cand.get("tags", [])) or "—"
            
            score_details = cand.get("_score_details", {})
            fr_identity_val = score_details.get("fr_identity", None)
            fr_identity = f"{fr_identity_val:.3f}" if fr_identity_val is not None else "N/A"
            cdr1_class = canonical.get("cdr1", {}).get("class", "TODO")
            cdr2_class = canonical.get("cdr2", {}).get("class", "TODO")
            canonical_match = f"{cdr1_class}/{cdr2_class}" if cdr1_class != "TODO" and cdr2_class != "TODO" else "TODO"
            canonical_status = score_details.get("canonical_status", "")
            reason = f"FR identity: {fr_identity}" if fr_identity != "N/A" else "FR1-FR3"
            
            html += f"""
                        <tr>
                            <td><strong>{i}</strong></td>
                            <td><code>{fw_id}</code></td>
                            <td>{fr_identity}</td>
                            <td>{canonical_match}</td>
                            <td>{tags}</td>
                            <td>{reason}</td>
                        </tr>"""
        
        html += """
                    </tbody>
                </table>"""
    
    # Final selection
    html += """
                <h3 style="margin-top: 30px; color: #34495e;"></h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th></th>
                            <th></th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>"""
    
    final_vh = final_choice.get("VH", "N/A")
    final_vl = final_choice.get("VL", "N/A")
    fr4_vh = final_choice.get("FR4_VH", "hJH4")
    fr4_vl = final_choice.get("FR4_VL", "hJK1")
    
    html += f"""
                        <tr>
                            <td><strong>VH </strong></td>
                            <td><code>{final_vh}</code></td>
                            <td>FR1-FR3 identitycanonical envelope</td>
                        </tr>
                        <tr>
                            <td><strong>VL </strong></td>
                            <td><code>{final_vl}</code></td>
                            <td>FR1-FR3 identitycanonical envelope</td>
                        </tr>
                        <tr>
                            <td><strong>FR4/J (VH)</strong></td>
                            <td><code>{fr4_vh}</code></td>
                            <td>，（）</td>
                        </tr>
                        <tr>
                            <td><strong>FR4/J (VL)</strong></td>
                            <td><code>{fr4_vl}</code></td>
                            <td>，（）</td>
                        </tr>"""
    
    html += """
                    </tbody>
                </table>"""
    
    # Triggered rules
    if triggered_rules:
        html += """
                <h3 style="margin-top: 30px; color: #34495e;"></h3>
                <ul style="line-height: 2;">"""
        
        for rule in triggered_rules:
            rule_id = rule.get("id", "unknown")
            reason = rule.get("reason", "Rule triggered")
            html += f"""
                    <li><strong>{rule_id}:</strong> {reason}</li>"""
        
        html += """
                </ul>"""
    
    html += """
            </div>"""
    
    return html


def render_framework_selection_section_en(
    query_numbering: List[Dict[str, Any]],
    selection_result: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Render Framework Selection Rationale section (English).
    
    Args:
        query_numbering: ANARCII numbering output
        selection_result: Optional pre-computed selection result (if None, will compute)
    
    Returns:
        HTML string for the section
    """
    if selection_result is None:
        selection_result = select_frameworks(query_numbering)
    
    top3_vh = selection_result.get("top3_vh", [])
    top3_vl = selection_result.get("top3_vl", [])
    final_choice = selection_result.get("final_choice", {})
    triggered_rules = selection_result.get("triggered_rules", [])
    
    html = """
            <!-- Framework Selection Rationale -->
            <div class="section">
                <h2 class="section-title">Framework Selection Rationale</h2>
                
                <div class="strategy-box" style="margin-bottom: 30px;">
                    <p style="margin: 0; color: #7f8c8d; font-size: 0.95em;">
                        <strong>Important:</strong> Framework definition = FR1–FR3 only (FR4 is NOT part of framework definition).
                        FR4/J segments are selected separately as compatibility components based on selection rules.
                    </p>
                </div>
    """
    
    # Top3 VH candidates table
    if top3_vh:
        html += """
                <h3 style="margin-top: 20px; color: #34495e;">VH Framework Candidates (Top 3)</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Framework ID</th>
                            <th>FR Identity</th>
                            <th>Canonical Match</th>
                            <th>Tags</th>
                            <th>Reason</th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        for i, cand in enumerate(top3_vh[:3], 1):
            fw_id = cand.get("framework_id", "N/A")
            canonical = cand.get("canonical", {})
            tags = ", ".join(cand.get("tags", [])) or "—"
            
            score_details = cand.get("_score_details", {})
            fr_identity_val = score_details.get("fr_identity", None)
            fr_identity = f"{fr_identity_val:.3f}" if fr_identity_val is not None else "N/A"
            cdr1_class = canonical.get("cdr1", {}).get("class", "TODO")
            cdr2_class = canonical.get("cdr2", {}).get("class", "TODO")
            canonical_match = f"{cdr1_class}/{cdr2_class}" if cdr1_class != "TODO" and cdr2_class != "TODO" else "TODO"
            
            # Build reason string with all score components
            reason_parts = []
            if fr_identity != "N/A":
                reason_parts.append(f"FR identity: {fr_identity}")
            canonical_status = score_details.get("canonical_status", "")
            if canonical_status and "Match" in canonical_status:
                reason_parts.append("Canonical match")
            cdr3_penalty = score_details.get("cdr3_penalty", 0)
            if cdr3_penalty > 0:
                reason_parts.append(f"CDR3 risk penalty: -{cdr3_penalty:.3f}")
            reason = "; ".join(reason_parts) if reason_parts else "Based on FR1-FR3 match"
            
            html += f"""
                        <tr>
                            <td><strong>{i}</strong></td>
                            <td><code>{fw_id}</code></td>
                            <td>{fr_identity}</td>
                            <td>{canonical_match}</td>
                            <td>{tags}</td>
                            <td>{reason}</td>
                        </tr>"""
        
        html += """
                    </tbody>
                </table>"""
    
    # Top3 VL candidates table
    if top3_vl:
        html += """
                <h3 style="margin-top: 30px; color: #34495e;">VL Framework Candidates (Top 3)</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Framework ID</th>
                            <th>FR Identity</th>
                            <th>Canonical Match</th>
                            <th>Tags</th>
                            <th>Reason</th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        for i, cand in enumerate(top3_vl[:3], 1):
            fw_id = cand.get("framework_id", "N/A")
            canonical = cand.get("canonical", {})
            tags = ", ".join(cand.get("tags", [])) or "—"
            
            score_details = cand.get("_score_details", {})
            fr_identity_val = score_details.get("fr_identity", None)
            fr_identity = f"{fr_identity_val:.3f}" if fr_identity_val is not None else "N/A"
            cdr1_class = canonical.get("cdr1", {}).get("class", "TODO")
            cdr2_class = canonical.get("cdr2", {}).get("class", "TODO")
            canonical_match = f"{cdr1_class}/{cdr2_class}" if cdr1_class != "TODO" and cdr2_class != "TODO" else "TODO"
            
            # Build reason string with all score components
            reason_parts = []
            if fr_identity != "N/A":
                reason_parts.append(f"FR identity: {fr_identity}")
            canonical_status = score_details.get("canonical_status", "")
            if canonical_status and "Match" in canonical_status:
                reason_parts.append("Canonical match")
            cdr3_penalty = score_details.get("cdr3_penalty", 0)
            if cdr3_penalty > 0:
                reason_parts.append(f"CDR3 risk penalty: -{cdr3_penalty:.3f}")
            reason = "; ".join(reason_parts) if reason_parts else "Based on FR1-FR3 match"
            
            html += f"""
                        <tr>
                            <td><strong>{i}</strong></td>
                            <td><code>{fw_id}</code></td>
                            <td>{fr_identity}</td>
                            <td>{canonical_match}</td>
                            <td>{tags}</td>
                            <td>{reason}</td>
                        </tr>"""
        
        html += """
                    </tbody>
                </table>"""
    
    # Final selection
    html += """
                <h3 style="margin-top: 30px; color: #34495e;">Final Selection</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Component</th>
                            <th>Selection</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>"""
    
    final_vh = final_choice.get("VH", "N/A")
    final_vl = final_choice.get("VL", "N/A")
    fr4_vh = final_choice.get("FR4_VH", "hJH4")
    fr4_vl = final_choice.get("FR4_VL", "hJK1")
    
    html += f"""
                        <tr>
                            <td><strong>VH Framework</strong></td>
                            <td><code>{final_vh}</code></td>
                            <td>Based on FR1-FR3 identity and canonical envelope match</td>
                        </tr>
                        <tr>
                            <td><strong>VL Framework</strong></td>
                            <td><code>{final_vl}</code></td>
                            <td>Based on FR1-FR3 identity and canonical envelope match</td>
                        </tr>
                        <tr>
                            <td><strong>FR4/J (VH)</strong></td>
                            <td><code>{fr4_vh}</code></td>
                            <td>Compatibility component selected by rules (NOT part of framework definition)</td>
                        </tr>
                        <tr>
                            <td><strong>FR4/J (VL)</strong></td>
                            <td><code>{fr4_vl}</code></td>
                            <td>Compatibility component selected by rules (NOT part of framework definition)</td>
                        </tr>"""
    
    html += """
                    </tbody>
                </table>"""
    
    # Triggered rules
    if triggered_rules:
        html += """
                <h3 style="margin-top: 30px; color: #34495e;">Triggered Selection Rules</h3>
                <ul style="line-height: 2;">"""
        
        for rule in triggered_rules:
            rule_id = rule.get("id", "unknown")
            reason = rule.get("reason", "Rule triggered")
            html += f"""
                    <li><strong>{rule_id}:</strong> {reason}</li>"""
        
        html += """
                </ul>"""
    
    html += """
            </div>"""
    
    return html
