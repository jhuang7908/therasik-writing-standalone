from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path("therasik-web-source/images/wechat")
WIDE = (1200, 675)
CARD = (1200, 420)
CONTACT = (1200, 520)

BG = "#f4fffc"
TEAL = "#0d9488"
TEAL_DARK = "#0f766e"
TEAL_LIGHT = "#d8f7ef"
TEXT = "#111827"
MUTED = "#4b5563"
BORDER = "#9be7d8"
AMBER = "#f59e0b"
PURPLE = "#7c3aed"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf" if bold else "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_center(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt: ImageFont.ImageFont, fill: str) -> None:
    w, h = text_size(draw, text, fnt)
    draw.text((xy[0] - w / 2, xy[1] - h / 2), text, font=fnt, fill=fill)


def draw_multiline_center(draw: ImageDraw.ImageDraw, xy: tuple[int, int], lines: Sequence[str], fnt: ImageFont.ImageFont, fill: str, gap: int = 6) -> None:
    heights = [text_size(draw, line, fnt)[1] for line in lines]
    total_h = sum(heights) + gap * (len(lines) - 1)
    y = xy[1] - total_h / 2
    for line, h in zip(lines, heights):
        w = text_size(draw, line, fnt)[0]
        draw.text((xy[0] - w / 2, y), line, font=fnt, fill=fill)
        y += h + gap


def round_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str | None = None, width: int = 2, radius: int = 28) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    cur = ""
    for ch in text:
        test = cur + ch
        if text_size(draw, test, fnt)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(draw: ImageDraw.ImageDraw, pos: tuple[int, int], text: str, fnt: ImageFont.ImageFont, fill: str, max_width: int, line_gap: int = 10) -> int:
    x, y = pos
    for line in wrap_text(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += text_size(draw, line, fnt)[1] + line_gap
    return y


def base(size: tuple[int, int] = WIDE) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", size, BG)
    draw = ImageDraw.Draw(img)
    w, h = size
    draw.ellipse((-140, -180, 360, 320), fill="#dffff7")
    draw.ellipse((w - 300, h - 260, w + 160, h + 180), fill="#e6f7ff")
    draw.line((70, h - 80, w - 70, h - 80), fill="#cdeee7", width=2)
    return img, draw


def save(img: Image.Image, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(OUT_DIR / name, "PNG", optimize=True)


def cover() -> None:
    img, d = base(WIDE)
    w, h = WIDE
    d.text((70, 58), "Thera", font=font(40, True), fill=TEXT)
    d.text((188, 58), "sik", font=font(40, True), fill=TEAL)
    d.text((70, 120), "药物 AI 设计平台", font=font(72, True), fill=TEXT)
    d.text((70, 208), "AI 设计不是替代实验", font=font(42, True), fill=TEAL_DARK)
    d.text((70, 265), "而是减少实验盲目性", font=font(42, True), fill=TEAL_DARK)
    d.text((70, 338), "抗体工程 · CMC 可开发性 · 多特异抗体 · Smart CAR-T / CAR-M", font=font(26), fill=MUTED)
    for i, label in enumerate(["线上自助", "线下精修", "AI Agent"]):
        x = 72 + i * 180
        round_rect(d, (x, 398, x + 150, 454), fill="#ffffff", outline=BORDER, radius=18)
        draw_center(d, (x + 75, 426), label, font(24, True), TEAL_DARK)
    cx, cy = 920, 320
    d.ellipse((cx - 120, cy - 120, cx + 120, cy + 120), outline=TEAL, width=8)
    d.arc((cx - 170, cy - 170, cx + 170, cy + 170), 205, 335, fill=TEAL_DARK, width=8)
    d.arc((cx - 70, cy - 70, cx + 70, cy + 70), 25, 155, fill=AMBER, width=7)
    draw_center(d, (cx, cy), "AI", font(60, True), TEAL_DARK)
    d.text((70, h - 58), "www.therasik.com  ·  console.therasik.com  ·  contact@therasik.com", font=font(22), fill=MUTED)
    save(img, "therasik_ai_design_cover.png")


def uncertainty() -> None:
    img, d = base(WIDE)
    d.text((70, 50), "从盲目筛选到有目的验证", font=font(50, True), fill=TEXT)
    d.text((70, 116), "AI 设计的价值：在湿实验前缩小不确定性", font=font(30), fill=TEAL_DARK)
    left = (80, 210, 500, 540)
    right = (700, 210, 1120, 540)
    round_rect(d, left, "#fff7ed", "#fed7aa")
    round_rect(d, right, "#ecfdf5", BORDER)
    draw_center(d, (290, 250), "盲筛路径", font(34, True), "#9a3412")
    draw_center(d, (910, 250), "AI 预评估路径", font(34, True), TEAL_DARK)
    for i, s in enumerate(["候选多", "方向不清", "试错成本高"]):
        draw_center(d, (290, 325 + i * 62), s, font(27), "#7c2d12")
    for i, s in enumerate(["风险先看清", "少量高置信方案", "实验更有方向"]):
        draw_center(d, (910, 325 + i * 62), s, font(27), TEAL_DARK)
    d.line((530, 375, 670, 375), fill=TEAL, width=8)
    d.polygon([(670, 375), (640, 355), (640, 395)], fill=TEAL)
    draw_center(d, (600, 430), "减少不确定性", font(25, True), TEAL_DARK)
    save(img, "ai_reduces_uncertainty.png")


def dual_track() -> None:
    img, d = base(WIDE)
    d.text((70, 50), "线上自助 + 线下精修", font=font(52, True), fill=TEXT)
    d.text((70, 116), "同一设计标准，同一报告体系", font=font(30), fill=TEAL_DARK)
    boxes = [
        ((90, 220, 530, 550), "线上平台", ["快速评估", "AI 助手问答", "报告生成", "早期方向判断"], TEAL),
        ((670, 220, 1110, 550), "线下专家", ["深度设计", "实验路线", "亲和力验证", "湿实验对接"], PURPLE),
    ]
    for box, title, lines, color in boxes:
        round_rect(d, box, "#ffffff", color, width=3)
        draw_center(d, ((box[0] + box[2]) // 2, box[1] + 48), title, font(36, True), color)
        for i, line in enumerate(lines):
            y = box[1] + 120 + i * 50
            d.ellipse((box[0] + 78, y + 7, box[0] + 96, y + 25), fill=color)
            d.text((box[0] + 120, y), line, font=font(26), fill=TEXT)
    d.line((555, 380, 645, 380), fill=TEAL_DARK, width=5)
    d.polygon([(645, 380), (620, 365), (620, 395)], fill=TEAL_DARK)
    save(img, "therasik_dual_track_service.png")


def service_matrix() -> None:
    img, d = base(WIDE)
    d.text((70, 48), "Therasik 服务矩阵", font=font(52, True), fill=TEXT)
    d.text((70, 112), "从抗体工程到细胞治疗构型建议", font=font(30), fill=TEAL_DARK)
    items = [
        ["VH/VL", "人源化"],
        ["VHH", "人源化"],
        ["VH-to-VHH", "小型化"],
        ["CMC", "可开发性"],
        ["多特异", "抗体"],
        ["Smart CAR", "T / CAR-M"],
        ["AI", "Agent"],
        ["线下实验", "对接"],
    ]
    for idx, item in enumerate(items):
        row, col = divmod(idx, 4)
        x = 70 + col * 275
        y = 205 + row * 165
        round_rect(d, (x, y, x + 240, y + 120), "#ffffff", BORDER, radius=22)
        d.ellipse((x + 22, y + 30, x + 72, y + 80), fill=TEAL_LIGHT, outline=TEAL)
        draw_center(d, (x + 47, y + 55), str(idx + 1), font(24, True), TEAL_DARK)
        draw_multiline_center(d, (x + 160, y + 60), item, font(25, True), TEXT, gap=8)
    save(img, "therasik_service_matrix.png")


def agent_boundary() -> None:
    img, d = base(WIDE)
    d.text((70, 48), "Therasik AI Agent", font=font(52, True), fill=TEXT)
    d.text((70, 112), "专业知识助手，输出结论与建议", font=font(30), fill=TEAL_DARK)
    round_rect(d, (390, 220, 810, 445), "#ffffff", TEAL, width=4, radius=34)
    draw_center(d, (600, 300), "AI Agent", font(50, True), TEAL_DARK)
    draw_center(d, (600, 365), "报告解读 · 风险解释 · 验证路线", font(25), MUTED)
    labels = [
        ("结构生物学问答", 145, 215),
        ("CMC 风险解释", 130, 455),
        ("多特异构型建议", 870, 215),
        ("Smart CAR-T / CAR-M", 850, 455),
    ]
    for label, x, y in labels:
        round_rect(d, (x, y, x + 245, y + 74), "#ffffff", BORDER, radius=20)
        draw_center(d, (x + 122, y + 37), label, font(23, True), TEXT)
    d.text((210, 585), "客户可见输出：工程结论、风险类别、推荐动作、湿实验验证路径", font=font(26, True), fill=TEAL_DARK)
    save(img, "therasik_agent_boundary.png")


def contact_card() -> None:
    img, d = base(CONTACT)
    d.text((70, 50), "开始使用 Therasik 药物 AI 设计平台", font=font(44, True), fill=TEXT)
    d.text((70, 110), "线上体验 + 正式项目合作入口", font=font(28), fill=TEAL_DARK)
    cards = [
        ("客服微信", "rockyhj", "快速响应"),
        ("邮箱", "contact@therasik.com", "NDA / 正式合作"),
        ("官网", "www.therasik.com", "服务与案例"),
        ("控制台", "console.therasik.com", "注册即送积分"),
    ]
    for i, (title, value, hint) in enumerate(cards):
        x = 55 + i * 285
        round_rect(d, (x, 205, x + 260, 390), "#ffffff", BORDER if i else TEAL, width=3, radius=24)
        draw_center(d, (x + 130, 248), title, font(24, True), TEAL_DARK)
        draw_center(d, (x + 130, 305), value, font(23 if len(value) < 18 else 19, True), TEXT)
        draw_center(d, (x + 130, 355), hint, font(19), MUTED)
    d.text((70, 455), "说明：AI 设计用于研发规划和方向筛选，不替代湿实验、临床试验或注册申报结论。", font=font(22), fill=MUTED)
    save(img, "therasik_contact_card.png")


def series_cover(name: str, title: str, subtitle: str, accent: str) -> None:
    img, d = base(WIDE)
    d.text((70, 70), "Therasik 公众号系列", font=font(30, True), fill=accent)
    y = draw_wrapped(d, (70, 150), title, font(54, True), TEXT, 760, line_gap=14)
    draw_wrapped(d, (70, y + 20), subtitle, font(30), MUTED, 720, line_gap=10)
    d.ellipse((870, 185, 1080, 395), outline=accent, width=8)
    d.arc((820, 135, 1130, 445), 210, 330, fill=accent, width=8)
    draw_center(d, (975, 290), "AI", font(58, True), accent)
    save(img, name)


def simple_diagram(name: str, title: str, left: str, right: str) -> None:
    img, d = base(WIDE)
    d.text((70, 58), title, font=font(46, True), fill=TEXT)
    round_rect(d, (95, 235, 500, 475), "#ffffff", "#fbbf24", width=3)
    round_rect(d, (700, 235, 1105, 475), "#ffffff", BORDER, width=3)
    draw_wrapped(d, (145, 310), left, font(31, True), "#92400e", 300)
    draw_wrapped(d, (750, 310), right, font(31, True), TEAL_DARK, 300)
    d.line((535, 355, 665, 355), fill=TEAL, width=8)
    d.polygon([(665, 355), (635, 335), (635, 375)], fill=TEAL)
    save(img, name)


def main() -> None:
    cover()
    uncertainty()
    dual_track()
    service_matrix()
    agent_boundary()
    contact_card()
    series_cover("series_01_uncertainty_cover.png", "药物研发不是少做实验，而是少做盲目实验", "AI 预评估帮助研发团队先看清方向、风险和验证路径", TEAL)
    simple_diagram("series_01_blind_vs_guided.png", "盲筛路径 vs 有目的验证", "候选多\n方向不清\n成本高", "先评估\n再验证\n更聚焦")
    simple_diagram("series_01_ai_expert_wetlab.png", "AI · 专家 · 湿实验协同", "经验试错", "AI 预判 + 专家取舍 + 实验验证")
    series_cover("series_02_antibody_structure_cover.png", "抗体人源化、VHH 与 VH-to-VHH", "为什么结构比序列更重要？", TEAL_DARK)
    simple_diagram("series_02_structure_vs_sequence.png", "序列相似不等于结构保留", "只看序列", "关注 CDR 构象与 Fv 架构")
    simple_diagram("series_02_vh_to_vhh.png", "VH-to-VHH 不是删除轻链", "简单截取", "结构兼容性重构")
    series_cover("series_03_cmc_cover.png", "抗体项目失败，不一定败在亲和力", "CMC 可开发性越早看，越少后期返工", AMBER)
    simple_diagram("series_03_cmc_risk_map.png", "CMC 风险地图", "亲和力之外", "表达 · 聚集 · 稳定性 · 免疫原性")
    simple_diagram("series_03_early_vs_late_cmc.png", "早期 CMC vs 后期返工", "后期发现", "序列阶段提前评估")
    series_cover("series_04_multispecific_car_cover.png", "不是简单拼装", "多特异和 CAR 设计需要场景驱动", PURPLE)
    simple_diagram("series_04_format_selection.png", "多特异格式选择", "机械拼接", "机制 · 空间 · CMC 综合判断")
    simple_diagram("series_04_smart_car_scenario.png", "Smart CAR-T / CAR-M", "从元件出发", "从靶点和疾病场景出发")


if __name__ == "__main__":
    main()
