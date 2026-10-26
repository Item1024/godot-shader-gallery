"""Export and verify a Windows x64 package using a matching Godot template."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, cwd, log):
    with log.open("w", encoding="utf-8") as stream:
        subprocess.run([str(c) for c in command], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=600)
    if "ERROR:" in log.read_text(encoding="utf-8", errors="replace"):
        raise RuntimeError("Godot reported an error; inspect " + str(log))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", type=Path, default=Path("E:/Godot/Godot_v4.7.2-stable_win64_console.exe"))
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    engine, template, output = args.godot.resolve(), args.template.resolve(), args.output.resolve()
    if not engine.is_file() or not template.is_file():
        parser.error("Godot and the matching Windows release template must exist")
    if output.exists() or output.with_suffix(".zip").exists():
        parser.error("Choose a new output directory; existing builds are never overwritten")
    version = subprocess.check_output([str(engine), "--version"], text=True).strip()
    if not version.startswith("4.7.2.stable"):
        parser.error("This package is verified with Godot 4.7.2.stable")
    output.mkdir(parents=True)
    staging, package, validation = [output / n for n in ["project", "package", "validation"]]
    for folder in [staging, package, validation]: folder.mkdir()
    paths = subprocess.check_output(["git", "ls-files", "-z", "--", "assets", "effects", "shared",
                                     "project.godot", "gallery.tscn", "catalog.json", "categories.json"], cwd=ROOT).decode().split("\0")
    paths = [p for p in paths if p]
    for name in paths:
        target = staging / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    preset = (ROOT / "export_presets.cfg").read_text(encoding="utf-8")
    preset = preset.replace('custom_template/release=""', 'custom_template/release="' + template.as_posix() + '"')
    (staging / "export_presets.cfg").write_text(preset, encoding="utf-8")
    run([engine, "--headless", "--path", staging, "--editor", "--import"], ROOT, output / "import.log")
    executable = package / "ShaderAtlas.exe"
    run([engine, "--headless", "--path", staging, "--export-release", "Windows Desktop", executable], ROOT, output / "export.log")
    if not executable.is_file() or not executable.with_suffix(".pck").is_file():
        raise RuntimeError("Exporter did not produce both the executable and PCK")
    # Validate the bare executable/PCK pair before adding the readable source folders.
    expected = {p: digest(ROOT / p) for p in paths if Path(p).suffix in [".json", ".md", ".gdshader"]}
    manifest = validation / "expected.json"
    manifest.write_text(json.dumps(expected, ensure_ascii=False, indent=2), encoding="utf-8")
    empty_cwd = validation / "empty-working-directory"
    empty_cwd.mkdir()
    # Official release templates disable external --script path overrides.
    run([engine, "--headless", "--main-pack", executable.with_suffix(".pck"), "--script", ROOT / "tools/test_windows_export.gd", "--",
         "--manifest=" + str(manifest), "--output=" + str(validation)], empty_cwd, validation / "resources.log")
    records = []
    for category in range(1, 24):
        folder = validation / f"category-{category}"
        run([executable, "--rendering-method", "forward_plus", "--rendering-driver", "vulkan", "--resolution", "1440x900",
             "--max-fps", "30", "--", "--audit", "--quit-after-audit", f"--audit-categories={category}",
             "--audit-output=" + str(folder)], empty_cwd, validation / f"category-{category}.log")
        records += json.loads((folder / "runtime_followup.json").read_text(encoding="utf-8"))
    if len(records) != 421 or {int(r["number"]) for r in records} != set(range(1, 422)) or not all(r["valid"] for r in records):
        raise RuntimeError("Exported GPU audit did not pass all 421 unique effects")
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    for record in records:
        entry = catalog[int(record["number"]) - 1]
        for key in ["shader", "readme"]:
            if record[key + "_sha256"] != expected[entry[key].removeprefix("res://")]:
                raise RuntimeError("Exported executable read different bytes: " + entry[key])
    for name in paths:
        if not name.startswith(("assets/", "effects/", "shared/")): continue
        target = package / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    for name in ["GODOT_LICENSE.txt", "THIRD_PARTY_NOTICES.txt"]:
        shutil.copy2(validation / name, package / name)
    (package / "README.txt").write_text(
        "Shader Atlas - Windows x64\n\n解压整个文件夹后双击 ShaderAtlas.exe。无需安装 Godot 编辑器。\n"
        "请保留 ShaderAtlas.pck 和随附目录。effects/、shared/、assets/ 提供可阅读和复制的示例源文件，"
        "界面的“打开效果目录”打开这些实际目录。\n\n"
        "本机验证：Windows、Godot 4.7.2、RTX 5060、Forward+ / Vulkan。其他显卡、系统和渲染器未验证。\n"
        "历史内存分配失败和 7 个 Texture RID 退出警告仍未解决；421 项运行检查不代表全部效果的像素质量认证。\n\n"
        "项目：https://github.com/Item1024/godot-shader-gallery\n"
        "Godot：https://godotengine.org/license/；完整引擎及第三方声明随包附带。\n", encoding="utf-8")
    report = {"engine": version, "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "template_sha256": digest(template), "preset_sha256": digest(ROOT / "export_presets.cfg"),
              "raw_resource_checks": len(expected), "gpu_audit_effects": len(records), "gpu_audit_failures": 0,
              "warnings": [f"{p.name}: {line}" for p in validation.glob("*.log")
                           for line in p.read_text(encoding="utf-8", errors="replace").splitlines() if "WARNING:" in line],
              "files": {p.relative_to(package).as_posix(): digest(p) for p in package.rglob("*") if p.is_file()}}
    (output / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive_path = output.with_suffix(".zip")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in package.rglob("*"):
            if path.is_file(): archive.write(path, "ShaderAtlas/" + path.relative_to(package).as_posix())
    print("WINDOWS_PACKAGE_OK", archive_path, archive_path.stat().st_size, digest(archive_path))


if __name__ == "__main__":
    main()
