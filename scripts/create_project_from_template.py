from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


DEFAULT_SKILL_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?")
    parser.add_argument("--skill-dir", default=str(DEFAULT_SKILL_DIR))
    parser.add_argument("--out-dir")
    parser.add_argument("--project-id", default="demo_project")
    parser.add_argument("--target-journal", default="Frontiers in Pharmacology")
    parser.add_argument("--article-type", default="review")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output_arg = args.out_dir or args.output_dir
    if not output_arg:
        raise SystemExit("Provide output_dir or --out-dir")
    skill_dir = Path(args.skill_dir).resolve()
    template_dir = skill_dir / "assets" / "project-template"
    if not template_dir.exists():
        raise SystemExit(f"Template directory not found: {template_dir}")

    output_dir = Path(output_arg)
    if output_dir.exists() and any(output_dir.iterdir()):
        if not args.force:
            raise SystemExit(f"Output directory is not empty: {output_dir}")
        shutil.rmtree(output_dir)
    shutil.copytree(template_dir, output_dir, dirs_exist_ok=True)

    config_path = output_dir / "project_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["project_id"] = args.project_id
    config["target_journal"] = args.target_journal
    config["article_type"] = args.article_type
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(config_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
