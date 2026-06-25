# 小红书 / 微信公众号格式 SSOT

## 文件

| 文件 | 用途 |
|------|------|
| `01_writer_system.md` | DeepSeek 写手系统提示 |
| `02_writer_user_template.md` | 用户消息模板 |
| `03_format_spec_v2.md` | 格式硬性约束（SSOT） |
| `04_validate_social.py` | 规则校验（字数/图数/章节） |
| `../../config/wechat_ad_bar.yaml` | 公众号文末**固定广告栏**（周更流水线自动注入） |

## 标准栈（非论文发表）

```
原文 → DeepSeek 写 JSON → Kimi 事实审查 → DeepSeek 修订 → 04_validate → space-design / gpt-image-2 配图
```

## 运行

```powershell
conda activate content_gen
python scripts/run_content_studio.py --scene xiaohongshu --source hiv_real_paper.txt --project demo_social
python content_generation_tools/social_content_prompts/04_validate_social.py outputs/demo_social/content_ssot/social.json
```

Cursor skill: `.cursor/skills/xhs-wechat-format/`
