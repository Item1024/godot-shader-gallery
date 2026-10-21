"""M5 manifest validation, behavior/repeatability checks and reviewed-reference comparison.

Requires Pillow and NumPy. This tool never creates or replaces approved references.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests/visual_cases.json"
STATES = ["off", "default", "min", "max", "secondary", "early", "late"]
REPEAT = dict(mean=1 / 255, pixel=3 / 255, fraction=0.001)
REGRESSION = dict(mean=2 / 255, pixel=8 / 255, fraction=0.01)


def digest(path, text=False):
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b"\r\n", b"\n") if text else data).hexdigest()


def load_manifest(path=MANIFEST):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    catalog = {e["number"]: e for e in json.loads((ROOT / "catalog.json").read_text(encoding="utf-8")) if "parameters" in e}
    if manifest["version"] != 1 or manifest["viewport_size"] != [640, 480]:
        raise ValueError("Unsupported manifest version or render dimensions")
    numbers = [e["number"] for e in manifest["effects"]]
    if len(numbers) != 20 or set(numbers) != set(catalog):
        raise ValueError("Manifest must contain the twenty profiled effects exactly once")
    for effect in manifest["effects"]:
        if [s["id"] for s in effect["states"]] != STATES:
            raise ValueError("Each effect needs exactly seven ordered states")
        params = {p["key"]: p for p in catalog[effect["number"]]["parameters"]}
        for state in effect["states"]:
            if state["time"] < 0:
                raise ValueError("Negative sample time")
            for key, value in state.get("parameters", {}).items():
                p = params[key]
                if p["type"] == "float" and not p["min"] <= value <= p["max"]:
                    raise ValueError("Parameter outside metadata bounds: " + key)
                if p["type"] in ["enum", "texture"] and value not in [o["value"] for o in p["options"]]:
                    raise ValueError("Invalid parameter option: " + key)
        primary = effect["primary"]
        for state_id, endpoint in [("min", "min"), ("max", "max")]:
            state = next(s for s in effect["states"] if s["id"] == state_id)
            if state["parameters"] != {primary: params[primary][endpoint]}:
                raise ValueError("Primary endpoints must match metadata")
        if not effect["checks"] or not any(c["kind"] == "different" for c in effect["checks"]):
            raise ValueError("Every effect needs explicit behavior assertions")
    return manifest


def read_capture(directory, manifest, defaults_only=False):
    directory = Path(directory)
    report = json.loads((directory / "capture.json").read_text(encoding="utf-8"))
    if not report["complete"] or report["only"] != 0 or report["defaults_only"] != defaults_only:
        raise ValueError("Incomplete or diagnostic capture cannot be a full M5 run")
    if report["manifest_sha256_lf"] != digest(MANIFEST, text=True):
        raise ValueError("Capture manifest hash mismatch")
    expected = {f'{e["number"]:03d}_{s["id"]}' for e in manifest["effects"] for s in e["states"] if not defaults_only or s["id"] == "default"}
    rows = report["captures"]
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)) or {r["id"] for r in rows if r["category"] == "state"} != expected:
        raise ValueError("Missing, extra or duplicate canonical states")
    for row in rows:
        if row["filename"] != row["id"] + ".png" or Path(row["filename"]).name != row["filename"]:
            raise ValueError("Invalid capture filename")
        path = directory / row["filename"]
        if digest(path) != row["sha256"]:
            raise ValueError("Capture image hash mismatch: " + row["id"])
        with Image.open(path) as image:
            if list(image.size) != manifest["viewport_size"]:
                raise ValueError("Capture dimensions mismatch: " + row["id"])
    return report


def rgba(path):
    with Image.open(path) as image:
        return np.asarray(image.convert("RGBA"), dtype=np.int16)


def metrics(a, b, region, pixel=0):
    if a.shape != b.shape:
        raise ValueError("Image dimensions differ")
    x, y, w, h = region
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > a.shape[1] or y + h > a.shape[0]:
        raise ValueError("Comparison region outside image")
    delta = np.abs(a[y:y+h, x:x+w] - b[y:y+h, x:x+w]) / 255.0
    return dict(mean=float(delta[:, :, :3].mean()),
                fraction=float((delta[:, :, :3].max(axis=2) > pixel).mean()),
                max_alpha=float(delta[:, :, 3].max()), max_channel=float(delta.max()))


def within(values, limits):
    return values["mean"] <= limits["mean"] and values["fraction"] <= limits["fraction"] and values["max_alpha"] <= limits["pixel"]


def difference(a, b, path):
    delta = np.abs(a - b)
    rgb = np.maximum(delta[:, :, :3], delta[:, :, 3:4])
    Image.fromarray(np.clip(rgb * 4, 0, 255).astype(np.uint8)).save(path)


def check_behavior(effect, directory, output):
    base = f'{effect["number"]:03d}_'
    results = []
    for index, check in enumerate(effect["checks"]):
        a = rgba(directory / (base + check["a"] + ".png"))
        b = rgba(directory / (base + check["b"] + ".png"))
        region = check.get("region", effect["region"])
        values = metrics(a, b, region)
        kind = check["kind"]
        if kind == "same":
            passed = values["max_channel"] <= check.get("max_channel", 0)
        elif kind == "different":
            passed = values["mean"] >= check["min_mean"]
        elif kind == "alpha_same":
            passed = values["max_alpha"] == 0
        elif kind == "empty_alpha":
            passed = not bool(np.any(a[:, :, 3]))
        elif kind == "outer_outline":
            opaque = b[:, :, 3] == 255
            # Rounded 8-bit alpha=255 also includes near-opaque filtered edge texels.
            # Require a 3x3 opaque neighborhood to identify the actual interior.
            opaque = np.logical_and.reduce([np.roll(opaque, (y, x), (0, 1)) for y in [-1, 0, 1] for x in [-1, 0, 1]])
            exterior = b[:, :, 3] == 0
            passed = bool(np.array_equal(a[opaque], b[opaque]) and np.any(a[:, :, 3][exterior] > 0) and np.all(a[:, :, 3] >= b[:, :, 3]))
        elif kind == "progress_endpoints":
            y, x = np.indices(a.shape[:2])
            radius = np.sqrt((x + 0.5 - 320)**2 + (y + 0.5 - 240)**2) / 240
            interior = radius < 0.77
            if effect["number"] == 296:
                interior &= radius > 0.65
            color = np.array([85, 232, 187])
            full_error = np.abs(b[:, :, :3][interior] - color).max()
            empty_error = np.abs(a[:, :, :3] - np.array([9, 15, 26])).max()
            passed = bool(full_error <= 1 and empty_error <= 1)
            values.update(full_error=int(full_error), empty_error=int(empty_error))
        elif kind == "smooth_edges":
            x, y, w, h = region
            blurred = a[y:y+h, x:x+w, :3].std()
            original = b[y:y+h, x:x+w, :3].std()
            passed = bool(blurred < original * 0.8)
            values.update(blurred_std=float(blurred), original_std=float(original))
        else:
            raise ValueError("Unknown assertion: " + kind)
        filename = f'behavior_{base}{index:02d}.png'
        difference(a, b, output / filename)
        results.append(dict(effect=effect["number"], name=check["name"], passed=passed, metrics=values, diff=filename))
    return results


def compare_runs(actual, other, manifest, output, repeat):
    results = []
    limits = REPEAT if repeat else REGRESSION
    for effect in manifest["effects"]:
        for state in effect["states"]:
            if repeat and state["id"] != "default":
                continue
            id = f'{effect["number"]:03d}_{state["id"]}'
            a, b = rgba(actual / (id + ".png")), rgba(other / (id + ".png"))
            values = metrics(a, b, effect["region"], limits["pixel"])
            filename = ("repeat_" if repeat else "reference_") + id + ".png"
            difference(a, b, output / filename)
            results.append(dict(id=id, passed=within(values, limits), metrics=values, diff=filename))
    return results


def reference_approval(directory, capture):
    approval = json.loads((directory / "approval.json").read_text(encoding="utf-8"))
    if approval.get("status") != "approved" or not approval.get("reviewer") or not approval.get("reviewed_at"):
        raise ValueError("Reference images require recorded human approval")
    if approval.get("capture_sha256") != digest(directory / "capture.json"):
        raise ValueError("Human approval does not match these reference images")
    if capture["approved_visual_reference"]:
        raise ValueError("Keep the original capture evidence unchanged; approval is separate")


def contact_sheets(actual, manifest, output):
    font_color = "#e2e8f0"
    links = []
    for page in range(4):
        sheet = Image.new("RGB", (7 * 224, 5 * 198), "#101827")
        draw = ImageDraw.Draw(sheet)
        history = Image.new("RGB", (4 * 280, 5 * 232), "#101827")
        history_draw = ImageDraw.Draw(history)
        for row, effect in enumerate(manifest["effects"][page * 5:page * 5 + 5]):
            base = f'{effect["number"]:03d}_'
            for col, state in enumerate(effect["states"]):
                with Image.open(actual / (base + state["id"] + ".png")) as source:
                    thumb = source.convert("RGBA").resize((224, 168))
                    sheet.paste(thumb, (col * 224, row * 198 + 24), thumb)
                draw.text((col * 224 + 4, row * 198 + 4), base + state["id"], fill=font_color)
            slug = effect["slug"]
            old = ROOT / "tests/baseline_m1"
            images = [(old / (base + slug + "_off.png"), "M1 off"), (actual / (base + "off.png"), "M5 off"),
                      (old / (base + slug + "_on.png"), "M1 on"), (actual / (base + "default.png"), "M5 default")]
            for col, (path, label) in enumerate(images):
                with Image.open(path) as source:
                    thumb = source.convert("RGBA").resize((280, 210))
                    history.paste(thumb, (col * 280, row * 232 + 22), thumb)
                history_draw.text((col * 280 + 4, row * 232 + 4), base + label, fill=font_color)
        name = f"states_{page+1}.png"
        sheet.save(output / name)
        history_name = f"m1_comparison_{page+1}.png"
        history.save(output / history_name)
        links.append(f"![140-state review, page {page+1}]({name})\n\n![M1 comparison, page {page+1}]({history_name})")
    return "\n\n".join(links)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actual", nargs="?", type=Path)
    parser.add_argument("--repeat", type=Path, help="Independent process, defaults-only capture")
    parser.add_argument("--reference", type=Path, help="Explicit, human-approved full capture directory")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest()
        if args.validate_only:
            print("M5_MANIFEST_OK effects=20 states=140")
            return 0
        if not args.actual or not args.output or not args.repeat:
            parser.error("actual, --repeat and a new --output directory are required")
        actual = read_capture(args.actual, manifest)
        repeat = read_capture(args.repeat, manifest, defaults_only=True)
        if actual["environment"] != repeat["environment"] or actual["source_sha256"] != repeat["source_sha256"]:
            raise ValueError("Repeat run environment or source files differ")
        reference = None
        if args.reference:
            reference = read_capture(args.reference, manifest)
            reference_approval(args.reference, reference)
            if actual["environment"] != reference["environment"]:
                raise ValueError("Reference GPU/driver/engine/render settings differ; review separately")
        args.output.mkdir(parents=True, exist_ok=False)
        behaviors = [r for effect in manifest["effects"] for r in check_behavior(effect, args.actual, args.output)]
        repeats = compare_runs(args.actual, args.repeat, manifest, args.output, repeat=True)
        regressions = compare_runs(args.actual, args.reference, manifest, args.output, repeat=False) if reference else []
        failures = sum(not row["passed"] for row in behaviors + repeats + regressions)
        report = dict(status="failed" if failures else ("regression_passed" if reference else "awaiting_human_reference_review"),
                      failures=failures, states=140, environment=actual["environment"],
                      actual=str(args.actual.resolve()), repeat=str(args.repeat.resolve()),
                      reference=str(args.reference.resolve()) if reference else None,
                      capture_sha256=digest(args.actual / "capture.json"),
                      manifest_sha256_lf=actual["manifest_sha256_lf"],
                      source_sha256=actual["source_sha256"], limits=dict(repeat=REPEAT, regression=REGRESSION),
                      comparator_sha256=digest(Path(__file__), text=True),
                      python=sys.version, numpy=np.__version__, pillow=Image.__version__,
                      behavior=behaviors, repeatability=repeats, regression=regressions)
        (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sheets = contact_sheets(args.actual, manifest, args.output)
        text = f'# M5 candidate review\n\nStatus: **{report["status"]}**. Canonical states: 140. Failures: {failures}.\n\n'
        text += f'Behavior assertions: {len(behaviors)}; independent default repeats: {len(repeats)}; approved-reference comparisons: {len(regressions)}.\n\n'
        text += 'Full-size PNGs and their hashes are in the capture directory recorded in report.json. Diff PNGs amplify absolute RGBA differences by 4.\n\n'
        text += 'M1 images are historical comparison samples, resized here for inspection only. M5 uses 640x480, transparent sprite backgrounds, a Gaussian test chart and an LUT color chart; these input changes are intentional. M1 remains unchanged.\n\n'
        text += 'Candidate screenshots are not approved references. Human review must cover all seven states per effect and the intended changes from M1. No references are updated by this tool.\n\n'
        text += '\n'.join(f'- FAIL: {r.get("name", r.get("id"))}' for r in behaviors + repeats + regressions if not r["passed"])
        (args.output / "REVIEW.md").write_text(text + "\n\n" + sheets + "\n", encoding="utf-8")
        print(f'M5_COMPARE states=140 behavior={len(behaviors)} repeats={len(repeats)} regression={len(regressions)} failures={failures} status={report["status"]}')
        return int(failures != 0)
    except (ValueError, KeyError, OSError) as error:
        print("M5 ERROR: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
