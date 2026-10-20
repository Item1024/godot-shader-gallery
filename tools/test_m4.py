"""Verify each dependency manifest in its own fresh Godot project (real GPU)."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", default=r"E:\Godot\Godot_v4.7.2-stable_win64_console.exe")
    parser.add_argument("--only", help="One CATEGORY/SLUG for diagnosis; omit for all twenty")
    args = parser.parse_args()
    output = ROOT / "artifacts/m4"
    output.mkdir(parents=True, exist_ok=True)
    copies = Path(tempfile.mkdtemp(prefix="copies-", dir=output))
    entries = [e for e in json.loads((ROOT / "catalog.json").read_text(encoding="utf-8")) if "parameters" in e]
    if args.only:
        entries = [e for e in entries if e["category_slug"]+"/"+e["slug"] == args.only]
        if not entries: parser.error("Unknown M4 effect")
    results = []
    for entry in entries:
        number = entry["number"]
        directory = entry["directory"].removeprefix("res://")
        manifest = json.loads((ROOT / directory / "dependencies.json").read_text(encoding="utf-8"))
        project = copies / f"{number:03d}"
        project.mkdir()
        declared = set(manifest["files"])
        errors = []
        sources = {}
        for name in sorted(declared):
            relative = name.removeprefix("res://")
            if not name.startswith("res://") or ".." in Path(relative).parts or "\\" in name:
                raise ValueError("Invalid dependency: " + name)
            source = ROOT / relative
            if not source.is_file(): raise FileNotFoundError(source)
            if name in ["res://catalog.json", "res://shared/stage.gd", "res://shared/gallery.gd", "res://shared/standalone.gd"]:
                errors.append("Forbidden gallery dependency: " + name)
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            sources[name] = hashlib.sha256(source.read_bytes()).hexdigest()
            if source.suffix in [".tscn", ".tres", ".gd", ".gdshader"]:
                for reference in re.findall(r'res://[^\s"\)]+', source.read_text(encoding="utf-8")):
                    if reference not in declared: errors.append("Undeclared dependency: " + reference)
        (project / "project.godot").write_text('''config_version=5
[application]
config/name="M4 isolated usage verification"
config/features=PackedStringArray("4.7", "Forward Plus")
[display]
window/size/viewport_width=640
window/size/viewport_height=480
window/size/window_width_override=640
window/size/window_height_override=480
''', encoding="utf-8")
        # Test-only scaffolding is separate from the runtime dependency list.
        shutil.copy2(ROOT / "tools/test_m4.gd", project / "verify_m4.gd")
        (project / "case.json").write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        commands = [
            [args.godot, "--headless", "--path", str(project), "--editor", "--import", "--quit"],
            [args.godot, "--path", str(project), "--script", "res://verify_m4.gd", "--resolution", "640x480", "--position", "700,100"],
        ]
        for label, command in zip(["import", "gpu"], commands):
            if errors: break
            with (project / f"{label}.log").open("w", encoding="utf-8") as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=240)
            log_text = (project / f"{label}.log").read_text(encoding="utf-8")
            if result.returncode or any(token in log_text for token in ["SCRIPT ERROR:", "Parse Error:", "SHADER ERROR:", "ERROR:"]):
                errors.append(f"{label} failed (exit {result.returncode}); see {project / (label+'.log')}")
        report_path = project / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        if not report or report.get("failures", 1): errors.append("Missing or failed GPU report")
        row = dict(number=number, name=entry["name"], project=str(project), sources=sources, errors=errors, report=report)
        results.append(row)
        print(f'M4_COPY {number:03d} checks={len(report.get("checks", []))} failures={len(errors)}', flush=True)
    report = dict(effects=len(results), failures=sum(bool(r["errors"]) for r in results),
                  assertions=sum(len(r["report"].get("checks", [])) for r in results), results=results)
    path = output / ("report_"+args.only.replace("/", "_")+".json" if args.only else "report.json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f'M4_COMPLETE effects={report["effects"]} assertions={report["assertions"]} failures={report["failures"]}', flush=True)
    return int(report["failures"] != 0)


if __name__ == "__main__":
    sys.exit(main())
