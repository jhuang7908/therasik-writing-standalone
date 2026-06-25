"""
api/main.py  —  InSynBio AbEngineCore Demo API
Run: conda run -n anarcii uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.toolchain_env import ensure_toolchain_path, probe_toolchain

ensure_toolchain_path()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from api.routers import humanization, cmc, annotate, auth, structure, vh_to_vhh, petization, recheck, offline, cart_design, assistant, downstream
try:
    from api.routers import payments
    HAS_PAYMENTS = True
    PAYMENTS_ERROR = None
except Exception as e:
    import traceback
    HAS_PAYMENTS = False
    PAYMENTS_ERROR = traceback.format_exc()
from api.routers.petization import internal_pet_console_enabled
from api import auth_db
from api.job_store import jobs, STORAGE_ROOT, request_job_cancel, ensure_job_in_memory
from api.public_locale import public_site_name, public_locale

auth_db.init_db()
auth_db.bootstrap_from_env()


def _localize_therasik_html(text: str) -> str:
    if not text:
        return text
    # Order matters: longest / most-specific phrases first so they win before
    # shorter, more ambiguous tokens get rewritten.
    replacements = [
        # ── Brand / title bar ────────────────────────────────────────────
        ("InSynBio AbEngineCore", "Therasik AbEngineCore"),
        ("InSynBio Console", "Therasik Console"),
        ('<html lang="en">', '<html lang="zh-CN">'),
        ("Client Copy", "客户版"),

        # ── Report titles ────────────────────────────────────────────────
        ("VH/VL Antibody Humanization Report", "VH/VL 抗体人源化报告"),
        ("VH/VL Humanization Report", "VH/VL 人源化报告"),
        ("VHH Humanization Report", "VHH 人源化报告"),

        # ── Section headers (§...) ───────────────────────────────────────
        ("§1.1 — Conformation Profile Analysis", "§1.1 — 构象特征分析"),
        ("§2 — CDR Identification (IMGT)", "§2 — CDR 鉴定（IMGT）"),
        ("§3 — Germline Framework Selection", "§3 — 胚系框架选择"),
        ("§4b — Delivery Package", "§4b — 交付包"),
        ("§4 — Structure", "§4 — 结构"),
        ("§5c — Mutations Requiring Customer Review", "§5c — 需客户复核的突变"),
        ("§5d — J-segment (FR4) Retemplating", "§5d — J 段（FR4）模板重构"),
        ("§5 — Framework Mutation Decisions", "§5 — 框架区突变决策"),
        ("§6 — CDR Structural Conservation (Cα RMSD: mouse vs. humanized)",
            "§6 — CDR 结构保守性（Cα RMSD：鼠源 vs 人源化）"),
        ("§6 — CDR Structural Conservation", "§6 — CDR 结构保守性"),
        ("§7 — Immunogenicity / Humanness Assessment", "§7 — 免疫原性 / 人源化程度评估"),
        ("§8 — Basic Developability Screen (Donor vs Humanized)",
            "§8 — 基础可开发性筛查（供体 vs 人源化）"),
        ("§10 — Donor vs Humanized — FR/CDR Segmentation",
            "§10 — 供体 vs 人源化 — FR/CDR 分段"),
        ("§11 — CMC Developability Advisory (V5.5.1)", "§11 — CMC 可开发性建议（V5.5.1）"),
        ("§11 — CMC Developability Advisory", "§11 — CMC 可开发性建议"),
        ("§12 — Delivery checklist summary", "§12 — 交付清单概要"),

        # ── Run / reference provenance metadata ──────────────────────────
        ("Run metadata", "运行元信息"),
        ("Report format (suite)", "报告格式（套件）"),
        ("Report format (protocol)", "报告格式（协议）"),
        ("Report Format Version", "报告格式版本"),
        ("Service report (content)", "服务报告（内容）"),
        ("Service report", "服务报告"),
        ("Analysis / engine", "分析引擎"),
        ("Reference panel", "参考面板"),
        ("Sequence / project ID", "序列 / 项目 ID"),
        ("Job ID", "任务 ID"),
        ("Generated (browser)", "生成时间（浏览器）"),
        ("Input sequences (VH / VL)", "输入序列（VH / VL）"),
        ("Fv structure modeling", "Fv 结构建模"),
        ("Reference Benchmark", "参考基准"),
        ("Physicochemical Profile", "理化特征概览"),
        ("CDR Fingerprint", "CDR 指纹特征"),
        ("Engineering Actions", "工程优化建议"),
        ("Clinical ADA Context", "临床 ADA 背景信息"),
        ("Humanness Indicators (HPR + p-AbNatiV2)", "人源化指标（HPR + p-AbNatiV2）"),
        ("Method & Version", "方法与版本"),
        ("Analysis Version", "分析版本"),
        ("Underlying Standard", "底层标准"),
        ("Report Version", "报告版本"),

        # ── Reference cohort provenance block ────────────────────────────
        ("Reference cohort provenance", "参考队列来源"),
        ("Natural VH/VL benchmark panel", "天然 VH/VL 基准面板"),
        ("Engineered VH/VL benchmark panel", "工程化 VH/VL 基准面板"),
        ("Human IgG natural-baseline VH/VL CMC distribution",
            "人源 IgG 天然基线 VH/VL CMC 分布"),
        ("Engineered/clinical VH/VL reference", "工程化 / 临床 VH/VL 参考"),
        ("Reference range derived from internal source-matched benchmark panel",
            "参考范围来自内部来源匹配基准面板"),
        ("Detailed cohort composition is confidential",
            "队列详细组成不对外公开"),
        ("frozen release", "冻结版本"),
        ("Panel type", "面板类型"),
        ("Release ID", "版本编号"),
        ("Purpose in this report", "本报告中的用途"),

        # ── Strong / bold inline labels in the run header line ───────────
        ("<strong>Service</strong>", "<strong>服务</strong>"),
        ("<strong>Content variant</strong>", "<strong>内容版本</strong>"),
        ("<strong>Protocol</strong>", "<strong>协议</strong>"),
        ("<strong>Analysis</strong>", "<strong>分析</strong>"),
        ("<strong>Build</strong>", "<strong>构建</strong>"),
        ("<strong>Environment</strong>", "<strong>环境</strong>"),
        ("UI Build:", "UI 构建:"),
        ("API Version:", "API 版本:"),
        ("Run Mode:", "运行模式:"),
        ("(FastAPI)", "（FastAPI）"),

        # ── §0 overview table label cells ────────────────────────────────
        ("<td class='lbl'>Project</td>", "<td class='lbl'>项目</td>"),
        ("<td class='lbl'>Generated</td>", "<td class='lbl'>生成时间</td>"),
        ("<td class='lbl'>Pipeline</td>", "<td class='lbl'>流水线</td>"),
        ("<td class='lbl'>Report Format Version</td>", "<td class='lbl'>报告格式版本</td>"),
        ("<td class='lbl'>Run Mode</td>", "<td class='lbl'>运行模式</td>"),
        ("<td class='lbl'>Engineering Mode</td>", "<td class='lbl'>工程模式</td>"),
        ("<td class='lbl'>Optimization Strategy</td>", "<td class='lbl'>优化策略</td>"),
        ("<td class='lbl'>Execution Priority</td>", "<td class='lbl'>执行优先级</td>"),
        ("<td class='lbl'>Engine Rescue Path</td>", "<td class='lbl'>引擎补救路径</td>"),
        ("<td class='lbl'>Surface Fallback</td>", "<td class='lbl'>表面回退</td>"),
        ("<td class='lbl'>Final Route</td>", "<td class='lbl'>最终路径</td>"),
        ("<td class='lbl'>VH Route</td>", "<td class='lbl'>VH 路径</td>"),
        ("<td class='lbl'>VL Route</td>", "<td class='lbl'>VL 路径</td>"),

        # ── §0 overview cell values ──────────────────────────────────────
        ("VH/VL humanization — report protocol V5.5.1",
            "VH/VL 人源化 — 报告协议 V5.5.1"),
        ("standard graft → engine rescue → post-engine surface fallback",
            "标准移植 → 引擎补救 → 引擎后表面回退"),
        ("<b>Standard pipeline</b>", "<b>标准流水线</b>"),
        ("<b>Standard humanization</b>", "<b>标准人源化</b>"),
        ("<b>standard germline graft</b>", "<b>标准胚系移植</b>"),
        ("<b>Human germline CDR grafting</b>", "<b>人源胚系 CDR 移植</b>"),
        ("<b>not requested</b>", "<b>未请求</b>"),
        ("<b>not triggered</b>", "<b>未触发</b>"),
        ("(post-engine gate)", "（引擎后闸门）"),
        ("SMOKE validation", "SMOKE 校验"),

        # ── Section §3 / §5 / §6 / §7 / §8 table headers ─────────────────
        ("ADA literature (split: selected VH template vs VL template)",
            "ADA 文献（按所选 VH 模板与 VL 模板分组）"),
        ("Clinical antibodies using the selected VH framework (allele or family)",
            "使用所选 VH 框架（等位基因或家族）的临床抗体"),
        ("Clinical antibodies using the selected VL framework (allele or family)",
            "使用所选 VL 框架（等位基因或家族）的临床抗体"),
        ("Per-chain clinical / reference context", "按链临床 / 参考背景"),
        ("Coordinate-system note", "坐标系说明"),
        ("Pipeline QA audit", "流水线 QA 审计"),
        ("Show qa_audit (JSON)", "查看 qa_audit (JSON)"),
        ("Items requiring attention", "需关注项"),
        ("Top Germline Framework Candidates", "候选胚系框架"),
        ("Germline Framework Selection", "胚系框架选择"),
        ("Selected VH germline", "已选 VH 胚系"),
        ("Selected VL germline", "已选 VL 胚系"),
        ("Recommended back-mutations", "推荐回突变位点"),
        ("Humanized sequences", "人源化序列"),
        ("Sequence Comparison", "序列对比"),
        ("Donor species", "供体物种"),

        # ── Multi-word donor/humanized labels (long → short) ─────────────
        ("Donor Ab", "供体抗体"),
        ("Donor VH", "供体 VH"),
        ("Donor VL", "供体 VL"),
        ("Donor (input)", "供体（输入）"),
        ("Humanized Ab", "人源化抗体"),
        ("Humanized VH", "人源化 VH"),
        ("Humanized VL", "人源化 VL"),
        ("Gate (humanized)", "闸门（人源化）"),
        ("Human germline", "人源胚系"),
        ("VH FR ID%", "VH FR 同一性 %"),
        ("VL FR ID%", "VL FR 同一性 %"),
        ("Avg FR ID%", "平均 FR 同一性 %"),
        ("VH Germline", "VH 胚系"),
        ("VL Germline", "VL 胚系"),
        ("CDR Loop", "CDR 环"),
        ("QC Result", "QC 结果"),
        ("Disease / Indication", "疾病 / 适应症"),

        # ── Table headers (medium) wrapped in <th> ───────────────────────
        ("<th>Position</th>", "<th>位置</th>"),
        ("<th>Status</th>", "<th>状态</th>"),
        ("<th>Severity</th>", "<th>严重程度</th>"),
        ("<th>Threshold</th>", "<th>阈值</th>"),
        ("<th>Metric</th>", "<th>指标</th>"),
        ("<th>Parameter</th>", "<th>参数</th>"),
        ("<th>Phase</th>", "<th>阶段</th>"),
        ("<th>Item</th>", "<th>项目</th>"),
        ("<th>Detail</th>", "<th>详情</th>"),
        ("<th>Description</th>", "<th>描述</th>"),
        ("<th>Note</th>", "<th>备注</th>"),
        ("<th>Category</th>", "<th>类别</th>"),
        ("<th>Check</th>", "<th>检查</th>"),
        ("<th>Match</th>", "<th>匹配</th>"),
        ("<th>Bundle</th>", "<th>套件</th>"),
        ("<th>Chain</th>", "<th>链</th>"),
        ("<th>Length</th>", "<th>长度</th>"),
        ("<th>Sequence</th>", "<th>序列</th>"),
        ("<th>Interpretation</th>", "<th>解读</th>"),
        ("<th>Target</th>", "<th>目标</th>"),
        ("<th>Drug</th>", "<th>药物</th>"),
        ("<th>Pos</th>", "<th>位置</th>"),
        ("<th>Donor</th>", "<th>供体</th>"),
        ("<th>Humanized</th>", "<th>人源化</th>"),
        ("<th>QC</th>", "<th>QC</th>"),

        # ── TOC bar anchors (mixed CN/EN today → unified CN) ─────────────
        ("<a href='#s1_1'>Conformation</a>", "<a href='#s1_1'>构象</a>"),
        ("<a href='#s2'>CDR ID</a>", "<a href='#s2'>CDR 鉴定</a>"),
        ("<a href='#s3'>Germline</a>", "<a href='#s3'>胚系</a>"),
        ("<a href='#s5'>Back-Mut</a>", "<a href='#s5'>回突变</a>"),
        ("<a href='#s6'>CDR RMSD</a>", "<a href='#s6'>CDR RMSD</a>"),
        ("<a href='#s7'>Humanness</a>", "<a href='#s7'>人源化</a>"),
        ("<a href='#s8'>mini-CMC</a>", "<a href='#s8'>mini-CMC</a>"),
        ("<a href='#s10'>Sequences</a>", "<a href='#s10'>序列</a>"),
        ("<a href='#s11'>Advisory</a>", "<a href='#s11'>建议</a>"),
        ("<a href='#s12'>Checklist</a>", "<a href='#s12'>清单</a>"),
        ("<a href='#s12qa'>QA audit</a>", "<a href='#s12qa'>QA 审计</a>"),
        ("<b>Contents</b>", "<b>目录</b>"),

        # ── Common section names (legacy / shared) ───────────────────────
        ("Method & Version", "方法与版本"),
        ("Service", "服务"),
        ("Overview", "总览"),
        ("Structure", "结构"),
        ("Downloads", "下载"),

        # ── Paragraph-level advisory / disclaimer / empty-state text ─────
        ("All generated files are bundled in the delivery ZIP provided alongside this report.",
            "全部生成文件均已打包在本报告附带的交付 ZIP 中。"),
        ("At these framework positions the engineering trade-off cannot be resolved without project context. Please pick one option per row before lead selection.",
            "下述框架位点的工程权衡需结合项目上下文方可判定，请在 lead 候选锁定前为每一行选择一个方案。"),
        ("CDR Preservation (Donor vs Final)", "CDR 保留（供体 vs 最终）"),
        ("Conformation-based framework matching", "基于构象的框架匹配"),
        ("Conservative CDR shape; FR humanness decreases by 1 residue.",
            "保守的 CDR 形状；FR 人源化程度下降 1 个残基。"),
        ("Epitope screening status: skipped; HTTP: N/A",
            "表位筛查状态：跳过；HTTP：N/A"),
        ("FR4 corresponds to the immunoglobulin",
            "FR4 对应免疫球蛋白"),
        ("Hard gate: every protected engineering-CDR position matches the donor sequence.",
            "硬闸门：所有受保护的工程 CDR 位点均与供体序列一致。"),
        ("Higher FR humanness; possible mild CDR-shape drift if interface depends on this residue.",
            "更高的 FR 人源化程度；若界面依赖该残基，可能产生轻微 CDR 形状偏移。"),
        ("Internal quality review completed. Please combine with experimental confirmation for downstream decisions.",
            "内部质量审查已完成；请结合实验确认用于下游决策。"),
        ("Metrics are reported for comparability between predicted donor and humanized models; confirm critical conclusions experimentally.",
            "指标用于在预测的供体与人源化模型之间作可比性参考；关键结论请通过实验确认。"),
        ("Murine: human VH/VL frameworks are restricted to the clinical-frequency anchor pool (no full Kabat-cache expansion).",
            "鼠源：人源 VH/VL 框架仅限于临床频次锚定池（不进行完整 Kabat 缓存扩展）。"),
        ("No literature-linked ADA entries were found for either selected template.",
            "未在文献中找到与所选模板相关的 ADA 条目。"),
        ("None flagged in this run (empty does not imply liability-free in vitro).",
            "本次运行未标记任何风险位点（为空并不代表体外无风险）。"),
        ("Overall status (checklist summary):", "总体状态（清单概要）："),
        ("Primary sequence naturalness context for VH/VL jobs (repertoire 9-mer compatibility). AbLang2 and T20 are not run in this workflow.",
            "VH/VL 任务的一级序列天然度参考（基于组库 9-mer 相容性）；AbLang2 与 T20 在该工作流中不运行。"),
        ("Sequence-level developability advisories are present in this run.",
            "本次运行包含序列层面的可开发性提示。"),
        ("Structural profiling of CDR loops to ensure framework-conformation compatibility.",
            "对 CDR 环进行结构层面的特征分析，以确保框架—构象兼容性。"),
        ("The humanization of the donor antibody is assessed as ",
            "对供体抗体人源化的评估结果为 "),
        ("The humanized candidate has been audited for essential physicochemical liabilities. The overall profile reflects a stable sequence suitable for downstream process development. Prioritization is given to physical stability and expression yield, ensuring a favorable profile for clinical translation.",
            "人源化候选抗体已完成关键理化风险审计。整体特征显示该序列稳定，适合用于下游工艺开发；优先确保物理稳定性与表达产量，以获得有利于临床转化的特征。"),
        ("These two tables list clinical antibodies that use the ",
            "下方两张表列出了使用 "),

        # ── §0 evaluation sentence (continuation after WARN/PASS badge) ──
        ("The selected <strong>Standard humanization</strong> strategy balances framework humanness with paratope preservation. The resulting sequence aligns with clinical developability benchmarks, with specific attention paid to the structural integrity of the CDR loops.",
            "所选的 <strong>标准人源化</strong> 策略在 FR 人源化程度与互补位保留之间取得平衡；所得序列与临床可开发性基准一致，并特别关注 CDR 环的结构完整性。"),
        # Also support <b> variant of Standard humanization (different report builds)
        ("<strong>Standard humanization</strong>", "<strong>标准人源化</strong>"),
        ("<strong>Standard pipeline</strong>", "<strong>标准流水线</strong>"),

        # ── §1.1 CDR profiling table cells ───────────────────────────────
        ("✓ Profiled", "✓ 已分析"),
        ("Structural envelope validation", "结构包络验证"),

        # ── §2 IMGT footnotes ────────────────────────────────────────────
        ("CDR segments below use <b>IMGT V-domain boundaries</b> for clear database alignment.",
            "下方 CDR 段使用 <b>IMGT V 结构域边界</b> 以便清晰对齐数据库。"),
        ("Framework identity % and related fields elsewhere refer to the <b>selected human templates</b> in this report — not recalculated from this table alone.",
            "本报告中其它位置出现的框架同一性百分比及相关字段均参考 <b>所选人源模板</b>，并非仅基于本表重新计算。"),
        ("3. FR% vs CDR display", "3. FR% 与 CDR 显示"),
        (" Percent identities elsewhere in this report compare to the <strong>selected human germlines</strong>; §2 lists CDR segments with IMGT boundaries for cross-database alignment — <b>do not mix coordinate systems</b> when comparing numbers.",
            "：本报告其它位置的同一性百分比与 <strong>所选人源胚系</strong> 比对得到；§2 列出 CDR 段的 IMGT 边界以便跨数据库对齐 —— 比较数值时 <b>切勿混用坐标系</b>。"),

        # ── §3 clinical drug table footnotes (VH / VL variants) ──────────
        ("Listed drugs share the <strong>VH germline annotation</strong> in §3 with your selected template (exact allele or same IMGT gene family). VL annotations vary and are shown for context.",
            "下列药物在 §3 中所标注的 <strong>VH 胚系</strong> 与所选模板一致（相同等位基因或同一 IMGT 基因家族）。VL 标注存在差异，仅作背景参考。"),
        ("Listed drugs share the <strong>VL germline annotation</strong> in §3 with your selected template (exact allele or same IMGT gene family). VH annotations vary and are shown for context.",
            "下列药物在 §3 中所标注的 <strong>VL 胚系</strong> 与所选模板一致（相同等位基因或同一 IMGT 基因家族）。VH 标注存在差异，仅作背景参考。"),

        # ── Discussion subsection headers ────────────────────────────────
        ("Structural Discussion", "结构性讨论"),
        ("Developability Discussion", "可开发性讨论"),
        ("Sequence Discussion", "序列讨论"),
        ("Humanness Discussion", "人源化讨论"),

        # ── §11 / advisory card components ───────────────────────────────
        ("CMC LIABILITY REVIEW", "CMC 风险审查"),
        ("Findings:", "发现："),
        ("Recommendation:", "建议："),
        ("Liabilities: none listed", "风险位点：未列出"),
        ("Liabilities: ", "风险位点："),
        ("QA warnings: ", "QA 警告："),
        (" above recommended ", " 高于推荐值 "),
        ("Treat this as an advisory outcome and review §8 and §12 before lead nomination.",
            "请将此视为咨询性结论，在 lead 候选锁定前复核 §8 与 §12。"),
        ("🟡 MED", "🟡 中风险"),
        ("🔴 HIGH", "🔴 高风险"),
        ("🟢 LOW", "🟢 低风险"),
        ("🟢 OK", "🟢 通过"),

        # ── Humanization report — p-AbNatiV2 bracket note ─────────────────
        ("Computed when Run Mode includes structure evaluation (Standard / Enhanced). Quick Preview omits this gate.",
            "在运行模式包含结构评估（标准 / 增强）时计算；快速预览模式不运行此闸门。"),

        # ── CMC report — reference cohort provenance ──────────────────────
        ("Engineered/clinical IgG VH/VL CMC reference", "工程化 / 临床 IgG VH/VL CMC 参考"),
        ("Human IgG natural-baseline distribution", "人源 IgG 天然基线分布"),

        # ── CMC report — §0 summary table labels ─────────────────────────
        ("Developability index / 100", "可开发性指数 / 100"),
        ("Developability Index / 100", "可开发性指数 / 100"),
        ("Reference standard", "参考标准"),
        ("Engineered clinical VH/VL reference", "工程化临床 VH/VL 参考"),
        ("p-AbNatiV2 Likelihood", "p-AbNatiV2 似然值"),
        ("(VH/VL pairing likelihood proxy)", "（VH/VL 配对似然代理指标）"),

        # ── CMC report — §1 sequence submission note ──────────────────────
        ("1-letter amino acids as submitted for this run.",
            "单字母氨基酸序列，已按本次运行提交。"),
        ("Regions from ANARCII IMGT numbering + pipeline FR/CDR boundaries (same path as humanization/VHH tooling).",
            "来自 ANARCII IMGT 编号 + 流水线 FR/CDR 边界（与人源化 / VHH 工具链相同路径）。"),

        # ── CMC report — §1b segmentation table headers ───────────────────
        ("<th>Region</th>", "<th>区段</th>"),
        ("<th>Len</th>", "<th>长度</th>"),

        # ── CMC report — §2 structure note ───────────────────────────────
        ("In-silico Fv model for visualization and manual review of FR candidate sites; not a crystal structure.",
            "计算预测的 Fv 模型，用于可视化和手动复核 FR 候选位点；非晶体结构。"),
        ("Download Fv model (PDB)", "下载 Fv 模型（PDB）"),

        # ── CMC report — §3 score card labels ────────────────────────────
        ("<div class=\"score-lbl\">Developability Index / 100</div>",
            "<div class=\"score-lbl\">可开发性指数 / 100</div>"),
        ("Developability Index / 100", "可开发性指数 / 100"),
        ("Percentile rank vs selected reference panel",
            "与所选参考面板的百分位排名"),
        ("Gate (intersection):", "闸门（交叉）:"),
        ("Reference band:", "参考区间:"),
        ("Within the broader clinical reference space but should be monitored.",
            "在更广泛的临床参考范围内，但应持续监控。"),
        ("Within the preferred regular-antibody reference region.",
            "在常规抗体首选参考范围内。"),
        ("Within normal clinical range.", "在正常临床范围内。"),
        ("Optimal for antibody stability and expression.", "处于抗体稳定性与表达的最佳范围。"),
        ("Above the core reference range; review VH/VL interface packing.", "超出核心参考范围；建议复核 VH/VL 界面堆积。"),
        ("Below the core reference range.", "低于核心参考范围。"),

        # ── CMC report — §4 liability table rows ─────────────────────────
        ("Deamidation sites (NG / NS / NN motifs)", "脱酰胺位点（NG / NS / NN 基序）"),
        ("Oxidation sites (Met, Trp)", "氧化位点（Met, Trp）"),
        ("Glycosylation sites (N-X-S/T)", "糖基化位点（N-X-S/T）"),
        ("0 preferred in CDR; FR ≤ 2 acceptable", "CDR 中优选 0；FR 中 ≤ 2 可接受"),
        ("0 in V-domain; Fc N297 retained", "V 结构域中为 0；Fc N297 保留"),

        # ── CMC report — §5 reference panel interpretation ────────────────
        ("All reported values are interpreted only against reference distributions generated with the same internal calculation protocol. Cross-method thresholds are not mixed.",
            "所有报告值均仅与使用相同内部计算协议生成的参考分布进行解读；不混用跨方法阈值。"),
        ("Gene-engineered humanized antibodies use the engineered clinical VH/VL reference primary gate (approved-style mAb drug space), distinct from the fully-human natural cohort.",
            "基因工程化人源抗体使用工程化临床 VH/VL 参考作为主要闸门（已批准风格 mAb 药物空间），有别于全人源天然队列。"),
        ("Fully human regular antibodies are reviewed for naturalness and clinical drug-space compatibility.",
            "全人源常规抗体针对天然度和临床药物空间相容性进行审查。"),

        # ── CMC report — FR-only liability row ───────────────────────────
        ("FR-only", "仅框架区"),
        ("Framework observations (no auto site list)", "框架区观察（无自动位点列表）"),
        ("No numeric current/target pair was emitted for this row — often a qualitative liability flag without an automated FR substitution shortlist. Cross-check 高风险 / 中等风险 rows in the developability tile panel (§5) above and any CDR advisories below.",
            "本行未生成数字化当前/目标对 — 通常是无自动 FR 替代候选列表的定性风险标记。请交叉核查上方可开发性面板（§5）中的高风险 / 中等风险行及下方 CDR 建议。"),
        ("The liability scan recorded framework-region notes, but no 高风险-gated metric row produced an FR substitution shortlist for this response (or all candidate positions were filtered). Review the liability findings in context; this line alone is not a substitute for the 25-parameter gate outcome.",
            "风险扫描记录了框架区说明，但本次响应中没有高风险闸门指标行生成 FR 替代候选列表（或所有候选位点已被过滤）。请结合背景审查风险结果；本行单独不能替代 25 参数闸门结论。"),

        # ── CMC report — CDR advisory block ──────────────────────────────
        ("<strong>CDR Advisory Warnings (do not modify without structural validation)</strong>",
            "<strong>CDR 建议警告（未经结构验证，切勿修改）</strong>"),

        # ── CMC report — mutation rules bullet list ───────────────────────
        ("Position Selection: Target non-critical, surface-exposed framework (FR) positions. Strictly avoid CDRs, Vernier zone residues, and positions within 5 Å of the CDR loops or VH/VL interface.",
            "位点选择：针对非关键、表面暴露的框架区（FR）位点；严格避开 CDR、Vernier 区残基以及距 CDR 环或 VH/VL 界面 5 Å 以内的位点。"),
        ("Mutation Rules: Apply distinct strategies based on surface properties. Use conservative substitutions at exposed hydrophobic patches to reduce aggregation risk, and utilize polar/charged surfaces for pI and net-charge tuning.",
            "突变规则：根据表面性质采用差异化策略；在暴露的疏水斑块处应用保守替换以降低聚集风险，利用极性 / 带电表面调节 pI 和净电荷。"),
        ("CDR Advisories: Treat all CDR liabilities as strictly advisory. Many highly successful clinical antibodies contain sequence liabilities within CDRs that are essential for antigen binding; modifications require explicit structural and functional validation.",
            "CDR 建议：将所有 CDR 风险位点视为严格的咨询性提示。许多成功的临床抗体在 CDR 中含有对抗原结合至关重要的序列风险位点；修改须经过明确的结构和功能验证。"),
        ("Action sequencing is FR-first and evidence-driven; maintain uniform report format across runs.",
            "操作顺序为 FR 优先且以证据为驱动；跨运行保持统一的报告格式。"),

        # ── CMC report — §1b section name ────────────────────────────────
        ("§1b — IMGT segmentation (FR / CDR)", "§1b — IMGT 分区（FR / CDR）"),
        ("§1 — Submitted VH / VL sequences", "§1 — 提交的 VH / VL 序列"),
        ("§2 — In-silico Fv Structure Model", "§2 — 计算预测 Fv 结构模型"),
        ("§3 — Developability Score", "§3 — 可开发性评分"),
        ("§4 — Developability Liability Screen", "§4 — 可开发性风险筛查"),
        ("§5 — Physicochemical Parameter Profile", "§5 — 理化参数特征"),
        ("§6 — CMC Mutation Advisory", "§6 — CMC 突变建议"),
        ("Click to expand sequence", "点击展开序列"),
        ("(empty)", "（空）"),
        ("Not applicable", "不适用"),
        ("N/A", "N/A"),

        # ── Status / severity tokens (use sparingly; uppercase only) ─────
        ("HIGH", "高风险"),
        ("LOW", "低风险"),
        ("MODERATE", "中等风险"),
        ("PASS", "通过"),
        ("WARN", "警告"),
        ("DONE", "完成"),
        ("Choose one", "请选择"),
    ]
    out = text
    for a, b in replacements:
        out = out.replace(a, b)

    # ── Final regex pass: rewrite the inner text of <th ...>X</th> and
    # ── <td class='lbl' ...>X</td> tags so inline styles, single/double
    # ── quoting, and extra attributes cannot make a phrase escape
    # ── localization. Technical abbreviations (CDR, QC, Cα RMSD, VH GL,
    # ── VL GL, Δ, #, ...) are intentionally NOT in the map → preserved.
    cell_text_map: Dict[str, str] = {
        # — short table headers —
        "Analysis": "分析",
        "Humanized": "人源化",
        "Donor": "供体",
        "Parameter": "参数",
        "Position": "位置",
        "Pos": "位置",
        "Status": "状态",
        "Severity": "严重程度",
        "Threshold": "阈值",
        "Metric": "指标",
        "Phase": "阶段",
        "Item": "项目",
        "Detail": "详情",
        "Description": "描述",
        "Note": "备注",
        "Category": "类别",
        "Check": "检查",
        "Match": "匹配",
        "Bundle": "套件",
        "Chain": "链",
        "Length": "长度",
        "Sequence": "序列",
        "Interpretation": "解读",
        "Target": "目标",
        "Drug": "药物",
        "Choose one": "请选择",
        "Avg FR ID%": "平均 FR 同一性 %",
        "Donor Ab": "供体抗体",
        "Donor VH": "供体 VH",
        "Donor VL": "供体 VL",
        "Donor (input)": "供体（输入）",
        "Humanized Ab": "人源化抗体",
        "Humanized VH": "人源化 VH",
        "Humanized VL": "人源化 VL",
        "Gate (humanized)": "闸门（人源化）",
        "Human germline": "人源胚系",
        "VH Germline": "VH 胚系",
        "VL Germline": "VL 胚系",
        "VH FR ID%": "VH FR 同一性 %",
        "VL FR ID%": "VL FR 同一性 %",
        "CDR Loop": "CDR 环",
        "QC Result": "QC 结果",
        "Disease / Indication": "疾病 / 适应症",

        # — §0 overview & metadata row labels (also appear as td class=lbl) —
        "Project": "项目",
        "Generated": "生成时间",
        "Pipeline": "流水线",
        "Run Mode": "运行模式",
        "Engineering Mode": "工程模式",
        "Optimization Strategy": "优化策略",
        "Execution Priority": "执行优先级",
        "Engine Rescue Path": "引擎补救路径",
        "Surface Fallback": "表面回退",
        "Final Route": "最终路径",
        "VH Route": "VH 路径",
        "VL Route": "VL 路径",
        "Report Format Version": "报告格式版本",
        "Overall Status": "总体状态",
        "Phases Passed": "已通过的阶段",
        "Checklist Phases Passed": "已通过的清单阶段",
        "Selection Policy": "选择策略",
        "Quality Control Note": "质量控制说明",

        # — Selected V{H,L} germline (cover both capital and lowercase g) —
        "Selected VH germline": "已选 VH 胚系",
        "Selected VL germline": "已选 VL 胚系",
        "Selected VH Germline": "已选 VH 胚系",
        "Selected VL Germline": "已选 VL 胚系",
        # Post-string-replace residue: earlier `VH Germline → VH 胚系`
        # already ran on the inner text, so the regex pass sees the partly
        # translated form. Catch those too.
        "Selected VH 胚系": "已选 VH 胚系",
        "Selected VL 胚系": "已选 VL 胚系",
        "Recommended back-mutations applied (§5a)": "已应用的推荐回突变位点（§5a）",
        "推荐回突变位点 applied (§5a)": "已应用的推荐回突变位点（§5a）",

        # — Mini-CMC / developability label cells —
        "Theoretical pI": "理论 pI",
        "Fab pI (mini-CMC)": "Fab pI（mini-CMC）",
        "Instability Index": "不稳定性指数",
        "GRAVY (Hydrophobicity)": "GRAVY（疏水性）",
        "Net charge proxy": "净电荷代理指标",
        "Mini-CMC Liabilities": "Mini-CMC 风险位点",
        "Sequence liability motifs": "序列风险基序",
        "CDR sequence liabilities": "CDR 序列风险位点",
        "CDR-support framework positions": "CDR 支撑框架位点",
        "T-cell epitope module": "T 细胞抗原表位模块",

        # — Humanness / naturalness / model confidence —
        "HPR Index": "HPR 指数",
        "HPR Index (humanized Fv, combined)": "HPR 指数（人源化 Fv，综合）",
        "Paired Fv naturalness (p-AbNatiV, full evaluation)":
            "Fv 配对天然度（p-AbNatiV，完整评估）",
        "Paired Fv naturalness (p-AbNatiV; Standard / Enhanced)":
            "Fv 配对天然度（p-AbNatiV；标准 / 增强）",
        "Predicted model confidence (pLDDT-eq)": "预测模型置信度（pLDDT-eq）",

        # — Structure / framework difference cells —
        "FR differences total (germline vs donor)": "FR 差异总数（胚系 vs 供体）",
        "Framework back-mutation candidates (engine list)":
            "框架回突变候选（引擎列表）",
        "Mean CDR Cα RMSD (mouse→humanized)":
            "CDR Cα RMSD 平均值（鼠源→人源化）",
        "VH/VL Packing Angle (principal axis)": "VH/VL 堆叠角（主轴）",
        "VH FR identity (FR1–FR3, framework-only)":
            "VH FR 同一性（FR1–FR3，仅框架）",
        "VL FR identity (FR1–FR3, framework-only)":
            "VL FR 同一性（FR1–FR3，仅框架）",
        "Germline-linked ADA literature": "与胚系相关的 ADA 文献",
    }
    def _cell_replace(m: "re.Match[str]") -> str:
        inner = m.group(2)
        key = inner.strip()
        return f"{m.group(1)}{cell_text_map.get(key, inner)}{m.group(3)}"

    out = re.sub(r"(<th\b[^>]*>)([^<]+)(</th>)", _cell_replace, out)
    # Match <td class='lbl'>X</td> or <td class="lbl">X</td> with any extra attrs / order.
    out = re.sub(r"(<td\b[^>]*\blbl\b[^>]*>)([^<]+)(</td>)", _cell_replace, out)

    # ── Variable-residue mutation choice phrases (§5c rows) ──────────────
    # The residue letter changes per row, so we use re.sub with a backreference.
    out = re.sub(
        r"Keep germline residue ([A-Z]) \(maximize humanness\)",
        r"保留胚系残基 \1（最大化人源化程度）",
        out,
    )
    out = re.sub(
        r"Revert to donor residue ([A-Z]) \(preserve CDR/interface support\)",
        r"回突变至供体残基 \1（保留 CDR/界面支撑）",
        out,
    )
    # Variable "applied (§5a/§5b)" forms for back-mutation counters
    out = re.sub(
        r"back-mutations applied \(§5([a-z])\)",
        r"已应用回突变（§5\1）",
        out,
    )

    # Framework-decision integrity summary (counts vary per project).
    # Example source:
    #   "Framework-decision integrity: <b>44</b> framework difference(s) reviewed;
    #    <b>2</b> back-mutation(s) applied (§5a);
    #    <b>2</b> position(s) escalated for customer review (§5c)."
    out = re.sub(
        r"Framework-decision integrity:\s*<b>(\d+)</b>\s*framework difference\(s\) reviewed;\s*"
        r"<b>(\d+)</b>\s*back-mutation\(s\) applied \(§5([a-z])\);\s*"
        r"<b>(\d+)</b>\s*position\(s\) escalated for customer review \(§5([a-z])\)\.",
        r"框架决策完整性：复核了 <b>\1</b> 个框架差异；已应用 <b>\2</b> 个回突变（§5\3）；"
        r"上送 <b>\4</b> 个位点供客户复核（§5\5）。",
        out,
    )
    return out

# ── App (triggered reload v4) ────────────────────────────────────────────────

app = FastAPI(
    title="InSynBio AbEngineCore",
    description="Computational antibody engineering platform.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Sub-App (all endpoints under /api) ───────────────────────────────────

api_app = FastAPI(title="AbEngineCore API")

api_app.include_router(humanization.router)
api_app.include_router(cmc.router)
api_app.include_router(annotate.router)
api_app.include_router(auth.router)
api_app.include_router(structure.router)
api_app.include_router(vh_to_vhh.router)
api_app.include_router(petization.router)
api_app.include_router(recheck.router)
api_app.include_router(offline.router)
api_app.include_router(cart_design.router)
api_app.include_router(assistant.router)
api_app.include_router(downstream.router)
if HAS_PAYMENTS:
    api_app.include_router(payments.router)

@api_app.middleware("http")
async def insynbio_release_headers(request: Request, call_next):
    response = await call_next(request)
    try:
        v = get_version_info()
        response.headers["X-AbEngineCore-Build"] = str(v.get("build_id") or "?")
        response.headers["X-AbEngineCore-Env"] = str(v.get("environment") or "?")
    except Exception:
        pass
    return response

def _pricing_catalog_payload() -> Dict[str, Any]:
    from api.pricing_constants import pricing_catalog

    return pricing_catalog()


@api_app.get("/pricing/catalog")
def pricing_catalog_api() -> Dict[str, Any]:
    return _pricing_catalog_payload()


@api_app.get("/health")
def health() -> Dict[str, Any]:
    return _health_payload()

@api_app.get("/jobs/{job_id}")
def get_job(job_id: str):
    if not ensure_job_in_memory(job_id):
        raise HTTPException(404, "Job not found")
    return jobs[job_id]

@api_app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    out = request_job_cancel(job_id)
    if out is None:
        raise HTTPException(404, "Job not found")
    return out

def _serve_file_impl(job_id: str, file_path: str, request: Request, *, force_therasik: bool = False):
    if ".." in file_path or file_path.startswith(("/", "\\")):
        raise HTTPException(400, "Invalid path")
    base = STORAGE_ROOT / job_id
    path = (base / file_path).resolve()
    try:
        path.relative_to(base.resolve())
    except ValueError:
        raise HTTPException(400, "Invalid path")
    if not path.is_file():
        raise HTTPException(404, f"File not found: {file_path}")
    
    filename = path.name
    media = None
    if filename.lower().endswith(".zip"):
        media = "application/zip"
        return FileResponse(str(path), filename=filename, media_type=media)
    elif filename.lower().endswith((".html", ".htm")):
        host = (request.headers.get("host", "") or "").lower()
        xfh = (request.headers.get("x-forwarded-host", "") or "").lower()
        req_host = ((request.url.hostname or "") if request.url else "").lower()
        referer = (request.headers.get("referer", "") or "").lower()
        origin = (request.headers.get("origin", "") or "").lower()
        site_q = (request.query_params.get("site", "") or "").strip().lower()
        probe = " ".join([host, xfh, req_host, referer, origin, site_q])
        if force_therasik or ("therasik" in probe):
            text = path.read_text(encoding="utf-8", errors="ignore")
            text = _localize_therasik_html(text)
            return HTMLResponse(
                text,
                media_type="text/html; charset=utf-8",
                headers={
                    "Cache-Control": "no-store, max-age=0, must-revalidate",
                    "Pragma": "no-cache",
                    "Content-Disposition": "inline",
                },
            )
        # Serve HTML inline so browsers render it in a new tab (no attachment header).
        return FileResponse(
            str(path),
            media_type="text/html; charset=utf-8",
            headers={
                "Cache-Control": "no-store, max-age=0, must-revalidate",
                "Pragma": "no-cache",
                "Content-Disposition": "inline",
            },
        )
    return FileResponse(str(path), filename=filename, media_type=media)


@api_app.get("/files/{job_id}/{file_path:path}")
def serve_file(job_id: str, file_path: str, request: Request):
    return _serve_file_impl(job_id, file_path, request, force_therasik=False)


@api_app.get("/tfiles/{job_id}/{file_path:path}")
def serve_file_therasik(job_id: str, file_path: str, request: Request):
    # Therasik dedicated report/file route: always apply therasik-side localization
    # for HTML artifacts while keeping binary downloads unchanged.
    return _serve_file_impl(job_id, file_path, request, force_therasik=True)

# Session tracking (moved to /api/sessions/*)
import time as _time
_online_sessions: dict = {}
_ONLINE_TTL = 90

@api_app.post("/sessions/ping")
async def session_ping(request: Request):
    try: body = await request.json()
    except: body = {}
    user = str(body.get("user", "unknown"))[:32]
    role = str(body.get("role", "user"))[:16]
    ip = request.client.host if request.client else "unknown"
    _online_sessions[user] = {"last_seen": _time.time(), "role": role, "ip": ip}
    return {"ok": True}

@api_app.get("/sessions/online")
def sessions_online(user: str = "", role: str = ""):
    if role != "admin": return {"authorized": False}
    now = _time.time()
    active = []
    for u, info in list(_online_sessions.items()):
        if now - info["last_seen"] < _ONLINE_TTL:
            active.append({"user": u, "role": info["role"], "last_seen_s": int(now - info["last_seen"])})
    active.sort(key=lambda x: x["last_seen_s"])
    return {"authorized": True, "count": len(active), "users": active}

app.mount("/api", api_app)

# Static assets (CSS / JS / images extracted out of console HTML for browser caching).
# Files under api/static/assets/ are immutable per release; bump the filename on change.
_ASSETS_DIR = ROOT / "api" / "static" / "assets"
if _ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_ASSETS_DIR), html=False),
        name="assets",
    )

# ── Root / Frontend ──────────────────────────────────────────────────────────

def get_version_info():
    vpath = ROOT / "config" / "version_control.json"
    if vpath.exists():
        try: return json.loads(vpath.read_text(encoding="utf-8"))
        except: pass
    return {"protocol_version": "4.8.0", "analysis_version": "4.9.1", "report_format_version": "4.1.0", "build_id": "unknown", "environment": "UNKNOWN"}

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    host = (request.headers.get("host", "") or "").lower()
    forwarded_host = (request.headers.get("x-forwarded-host", "") or "").lower()
    req_host = ((request.url.hostname or "") if request.url else "").lower()
    host_probe = " ".join([host, forwarded_host, req_host])
    if "therasik" in host_probe:
        login_html = ROOT / "api" / "static" / "therasik_login.html"
    else:
        login_html = ROOT / "api" / "static" / "login.html"
        
    if login_html.exists():
        return HTMLResponse(login_html.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})
    return HTMLResponse("<h1>Login</h1>")

def _detect_therasik_tenant(request: Request) -> bool:
    """Detect therasik tenant from Host header, X-Forwarded-Host, Referer, or ?site=therasik query."""
    host = request.headers.get("host", "")
    forwarded_host = request.headers.get("x-forwarded-host", "")
    req_host = request.url.hostname or ""
    referer = request.headers.get("referer", "")
    site_q = (request.query_params.get("site", "") or "").strip().lower()
    probe = " ".join([host, forwarded_host, req_host, referer, site_q]).lower()
    return "therasik" in probe

@app.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    is_therasik = _detect_therasik_tenant(request)
    fname = "therasik_terms.html" if is_therasik else "terms.html"
    html_path = ROOT / "api" / "static" / fname
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})
    return HTMLResponse("<h1>Terms of Service</h1>")

@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    is_therasik = _detect_therasik_tenant(request)
    fname = "therasik_privacy.html" if is_therasik else "privacy.html"
    html_path = ROOT / "api" / "static" / fname
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})
    return HTMLResponse("<h1>Privacy Policy</h1>")

@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    is_therasik = _detect_therasik_tenant(request)
    fname = "therasik_pricing.html" if is_therasik else "pricing.html"
    html_path = ROOT / "api" / "static" / fname
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})
    return HTMLResponse("<h1>Pricing</h1>")


@app.get("/pricing/catalog")
def pricing_catalog_page_api() -> Dict[str, Any]:
    """Public pricing SSOT (also available at /api/pricing/catalog)."""
    return _pricing_catalog_payload()


@app.get("/internal/pet-console", response_class=HTMLResponse)
def internal_pet_console_page():
    if not internal_pet_console_enabled(): raise HTTPException(404, "Not found")
    html_path = ROOT / "api" / "static" / "pet_console.html"
    if not html_path.exists(): raise HTTPException(404, "Not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store, no-cache, must-revalidate"})

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    host = (request.headers.get("host", "") or "").lower()
    forwarded_host = (request.headers.get("x-forwarded-host", "") or "").lower()
    req_host = ((request.url.hostname or "") if request.url else "").lower()
    site_q = (request.query_params.get("site", "") or "").strip().lower()
    host_probe = " ".join([host, forwarded_host, req_host, site_q])
    is_therasik = "therasik" in host_probe
    if is_therasik:
        html = ROOT / "api" / "static" / "therasik_console.html"
    else:
        html = ROOT / "api" / "static" / "console.html"
        
    if not html.exists(): html = ROOT / "api" / "static" / "demo.html"
    if html.exists():
        text = html.read_text(encoding="utf-8")
        vinfo = get_version_info()
        is_dev = (request.url.port == 8000)
        env_label = "DEV" if is_dev else "LIVE"
        env_color = "#f85149" if is_dev else "#21c7d9"
        hide_btns_css = "#auth-open-btn, #auth-logout-btn { display: none !important; }" if not is_dev else ""
        
        v_shim = f"""
<style>
  :root {{ --env-color: {env_color}; }}
  .topbar {{ border-bottom: 2px solid var(--env-color) !important; }}
  .brand-text::after {{
    content: "{env_label} · build {vinfo['build_id']}";
    display: block !important;
    font-size: 9px !important;
    font-weight: 700 !important;
    color: var(--env-color) !important;
    margin-top: 2px !important;
  }}
  {hide_btns_css}
</style>
"""
        text = text.replace("</head>", v_shim + "</head>", 1)
        
        head_meta_fix = """
<script>
(function(){
  try {
    var m = document.querySelector('meta[name="insynbio-api-base"]');
    var saved = "";
    try { saved = (localStorage.getItem("insynbio_api_endpoint") || "").trim().replace(/\\/$/, ""); } catch(e) {}
    var base = saved || window.location.origin;
    if (m) m.setAttribute('content', base);
    window.__INSYNBIO_API_BASE__ = base;
  } catch(e) {}
})();
</script>
"""
        text = text.replace("</head>", head_meta_fix + "</head>", 1)
        if is_therasik:
            site_name = "therasik"
            locale_name = "zh"
        else:
            site_name = public_site_name()
            locale_name = public_locale()
        text = text.replace("__INSYNBIO_PUBLIC_SITE__", site_name)
        text = text.replace("__INSYNBIO_PUBLIC_LOCALE__", locale_name)
        # Force meta overrides even if historical html has hardcoded values.
        text = re.sub(
            r'(<meta name="insynbio-public-site" content=")[^"]*(">)',
            rf'\1{site_name}\2',
            text,
            count=1,
        )
        text = re.sub(
            r'(<meta name="insynbio-public-locale" content=")[^"]*(">)',
            rf'\1{locale_name}\2',
            text,
            count=1,
        )
        import hashlib
        _stamp = hashlib.md5(text.encode()).hexdigest()[:8]
        text = text.replace("</head>", f'<meta name="x-console-stamp" content="{_stamp}"></head>', 1)
        return HTMLResponse(text, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})
    return HTMLResponse("<h1>InSynBio AbEngineCore</h1>")

# ── Health check payload ─────────────────────────────────────────────────────

def _git_short_sha(cwd: Path) -> Optional[str]:
    env_sha = os.environ.get("ABENGINECORE_GIT_SHA", "").strip()
    if env_sha: return env_sha[:40]
    for base in (cwd, cwd.parent):
        try:
            r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(base), capture_output=True, text=True, timeout=2.0)
            if r.returncode == 0 and r.stdout.strip(): return r.stdout.strip()
        except: continue
    return None

def _health_payload() -> Dict[str, Any]:
    git_sha = _git_short_sha(ROOT)
    try: vinfo = get_version_info()
    except: vinfo = {"protocol_version": "unavailable", "analysis_version": "unavailable", "report_format_version": "unavailable", "build_id": "unavailable", "environment": "ERROR"}
    analysis_ver = str(vinfo.get("analysis_version") or "4.9.1")
    try:
        from api.report_versioning import export_service_report_versions
        service_report_versions = export_service_report_versions()
    except: service_report_versions = {}
    toolchain = probe_toolchain()
    overall = "ok" if toolchain.get("toolchain_ok") else "degraded"
    try:
        from api.pricing_constants import PRICING_VERSION

        pricing_version = PRICING_VERSION
    except Exception:
        pricing_version = None
    stripe_configured = bool(os.environ.get("STRIPE_SECRET_KEY"))
    deepseek_configured = bool(os.environ.get("DEEPSEEK_API_KEY"))
    try:
        from api import auth_db as _auth_db

        insynbio_smtp_configured = _auth_db.smtp_configured("insynbio")
        therasik_smtp_configured = _auth_db.smtp_configured("therasik")
    except Exception:
        insynbio_smtp_configured = bool(
            os.environ.get("INSYNBIO_SMTP_HOST")
            and os.environ.get("INSYNBIO_SMTP_USER")
            and os.environ.get("INSYNBIO_SMTP_PASS")
        )
        therasik_smtp_configured = bool(
            os.environ.get("THERASIK_SMTP_HOST")
            and os.environ.get("THERASIK_SMTP_USER")
            and os.environ.get("THERASIK_SMTP_PASS")
        )
    return {
        "status": overall,
        "version": os.environ.get("ABENGINECORE_VERSION") or analysis_ver,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "git_sha": git_sha,
        "build_id": vinfo.get("build_id"),
        "environment": vinfo.get("environment"),
        "protocol_version": vinfo.get("protocol_version"),
        "analysis_version": vinfo.get("analysis_version"),
        "report_format_version": vinfo.get("report_format_version"),
        "pricing_version": pricing_version,
        "stripe_configured": stripe_configured,
        "deepseek_configured": deepseek_configured,
        "deepseek_model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "insynbio_smtp_configured": insynbio_smtp_configured,
        "therasik_smtp_configured": therasik_smtp_configured,
        "service_report_versions": service_report_versions,
        "toolchain": toolchain,
        "payments_error": PAYMENTS_ERROR,
    }

@app.get("/health")
def health_root(): return _health_payload()
