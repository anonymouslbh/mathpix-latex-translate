#!/usr/bin/env python3
"""Plan and perform bounded book-cache cleanup using only the standard library."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
import sys

SCHEMA = "mathpix-book-cleanup.v1"
IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
CORE = {"source", "baseline", "translation", "delivery", "output", "final", "adopted-skill",
        "skill-snapshot", "skills", "assets", "scripts", ".git"}
ASSET_PARTS = CORE | {"covers", "images"}


class CleanupError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise CleanupError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def relative(value):
    require(isinstance(value, str) and value, "Paths must be nonempty strings.")
    require(not PureWindowsPath(value).drive, "Drive-qualified policy paths are forbidden.")
    normalized = PurePosixPath(value.replace("\\", "/"))
    require(not normalized.is_absolute() and ".." not in normalized.parts,
            "Policy paths must stay inside the project: " + value)
    require(normalized.parts and all(":" not in part for part in normalized.parts),
            "Root paths and alternate streams are forbidden: " + value)
    require(all(not part.endswith((".", " ")) and not any(c in part for c in '<>"|?*')
                for part in normalized.parts),
            "Ambiguous Windows paths and wildcard paths are forbidden: " + value)
    return normalized.as_posix()


def inside(path, parent):
    a, b = PurePosixPath(path).parts, PurePosixPath(parent).parts
    if os.name == "nt":
        a, b = tuple(x.casefold() for x in a), tuple(x.casefold() for x in b)
    return a[:len(b)] == b


def overlaps(a, b):
    return inside(a, b) or inside(b, a)


def linked(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 1024)


def checked(root, rel):
    """Reject links/junctions on every component before resolving a delete target."""
    rel = relative(rel)
    current = root
    for part in PurePosixPath(rel).parts:
        current = current / part
        require(current.exists() or current.is_symlink(), "Missing path: " + rel)
        require(not linked(current), "Links/junctions are excluded: " + rel)
    require(current.resolve().is_relative_to(root), "Resolved path escapes project: " + rel)
    canonical = current.resolve().relative_to(root).as_posix()
    require(inside(canonical, rel) and inside(rel, canonical),
            "Filesystem alias differs from policy path: " + rel)
    return current


def walk(root, rel):
    base = checked(root, rel)
    if base.is_file():
        yield rel
        return
    require(base.is_dir(), "Unsupported path: " + rel)
    stack = [base]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for entry in sorted(entries, key=lambda item: item.name):
                path = Path(entry.path)
                require(not linked(path), "Links/junctions are excluded: " + str(path))
                if entry.is_dir(follow_symlinks=False):
                    stack.append(path)
                elif entry.is_file(follow_symlinks=False):
                    yield path.relative_to(root).as_posix()
                else:
                    raise CleanupError("Unsupported filesystem entry: " + str(path))


def snapshot(root, rel):
    path = checked(root, rel)
    require(path.is_file(), "Expected a regular file: " + rel)
    before = path.stat()
    digest = sha(path)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
            "File changed while being scanned: " + rel)
    return {"path": rel, "bytes": after.st_size, "mtime_ns": after.st_mtime_ns,
            "sha256": digest}


def project_root(value):
    path = Path(value).absolute()
    require(path.is_dir() and not linked(path), "Project root must be a real directory.")
    # Also reject a project reached through a junction/symlink in its parent chain.
    for parent in path.parents:
        require(not linked(parent), "Project parent contains a link/junction.")
    root = path.resolve()
    require((root / "project.json").is_file(), "Select one book project with project.json.")
    checked(root, "project.json")
    return root


def policy_check(root, policy):
    require(isinstance(policy, dict), "Policy must be a JSON object.")
    allowed = {"current_pdf", "current_pages", "keep", "generated_roots", "image_roots",
               "obsolete_pdfs", "duplicate_copies"}
    require(set(policy) <= allowed, "Unknown policy fields: " + str(set(policy) - allowed))
    for key in ("keep", "generated_roots", "image_roots", "obsolete_pdfs", "duplicate_copies"):
        require(isinstance(policy.get(key, []), list), key + " must be a list.")
    current = relative(policy.get("current_pdf"))
    pages = relative(policy.get("current_pages"))
    require(checked(root, current).is_file() and Path(current).suffix.lower() == ".pdf",
            "current_pdf must be the verified current PDF.")
    require(checked(root, pages).is_dir(), "current_pages must identify the retained page set.")
    require(any(Path(x).suffix.lower() in IMAGES for x in walk(root, pages)),
            "The retained page set contains no images.")
    keep = {current, pages, "project.json"}
    keep.update(relative(x) for x in policy.get("keep", []))
    project = load(checked(root, "project.json"))
    # Original inputs declared by the project are protected even outside source/.
    for item in project.get("inputs", []):
        if isinstance(item, dict) and item.get("path"):
            keep.add(relative(item["path"]))
    for rel in keep:
        checked(root, rel)
    generated = [relative(x) for x in policy.get("generated_roots", [])]
    require(generated, "Declare the generated cache directories explicitly.")
    for rel in generated:
        require(PurePosixPath(rel).parts[0].casefold() not in CORE,
                "Original/editable/delivery directories cannot be cleanup roots: " + rel)
        require(checked(root, rel).is_dir(), "Generated root must be a directory: " + rel)
    image_roots = [relative(x) for x in policy.get("image_roots", [])]
    for rel in image_roots:
        require(any(inside(rel, base) for base in generated), "Image root is not a declared cache.")
        require(checked(root, rel).is_dir(), "Image root must be a directory: " + rel)
    old_pdfs = [relative(x) for x in policy.get("obsolete_pdfs", [])]
    copies = []
    for item in policy.get("duplicate_copies", []):
        require(isinstance(item, dict) and set(item) == {"path", "keep"},
                "Each duplicate copy needs exactly path and keep.")
        old, retained = relative(item["path"]), relative(item["keep"])
        require(not overlaps(old, retained), "A duplicate must not contain its keeper.")
        checked(root, old)
        checked(root, retained)
        require(any(inside(old, base) for base in generated), "Duplicate is not in a declared cache.")
        keep.add(retained)
        copies.append({"path": old, "keep": retained})
    require(all(not overlaps(a["path"], b["path"])
                for i, a in enumerate(copies) for b in copies[i+1:]),
            "Duplicate copy selections overlap.")
    return {"current_pdf": current, "current_pages": pages, "keep": sorted(keep),
            "generated_roots": generated, "image_roots": image_roots,
            "obsolete_pdfs": old_pdfs, "duplicate_copies": copies}


def protected(rel, policy):
    return (PurePosixPath(rel).parts[0].casefold() in CORE
            or any(inside(rel, path) for path in policy["keep"]))


def candidate_kind(rel, policy):
    require(not protected(rel, policy), "Protected file selected for cleanup: " + rel)
    require(any(inside(rel, base) for base in policy["generated_roots"]),
            "Candidate is outside generated caches: " + rel)
    for pair in policy["duplicate_copies"]:
        if inside(rel, pair["path"]):
            return "duplicate-copy"
    if rel in policy["obsolete_pdfs"]:
        require(Path(rel).suffix.lower() == ".pdf", "obsolete_pdfs contains a non-PDF.")
        return "obsolete-pdf"
    require(Path(rel).suffix.lower() in IMAGES
            and any(inside(rel, base) for base in policy["image_roots"]),
            "Unrecognized cleanup candidate: " + rel)
    require(not any(part.casefold() in ASSET_PARTS for part in PurePosixPath(rel).parts),
            "Source/cover/asset images are excluded: " + rel)
    return "old-page-image"


def keeper_for(root, rel, policy):
    for pair in policy["duplicate_copies"]:
        if inside(rel, pair["path"]):
            base = checked(root, pair["path"])
            if base.is_file():
                require(rel == pair["path"], "Invalid duplicate file path.")
                return pair["keep"]
            tail = PurePosixPath(rel).relative_to(PurePosixPath(pair["path"]))
            return (PurePosixPath(pair["keep"]) / tail).as_posix()
    raise CleanupError("Duplicate has no retained counterpart.")


def plan(root, original):
    policy = policy_check(root, original)
    selected = set()
    excluded_assets = 0
    for base in policy["image_roots"]:
        for rel in walk(root, base):
            if Path(rel).suffix.lower() not in IMAGES or protected(rel, policy):
                continue
            if any(part.casefold() in ASSET_PARTS for part in PurePosixPath(rel).parts):
                excluded_assets += 1
                continue
            selected.add(rel)
    selected.update(policy["obsolete_pdfs"])
    for pair in policy["duplicate_copies"]:
        old, retained = checked(root, pair["path"]), checked(root, pair["keep"])
        require(old.is_dir() == retained.is_dir(), "Duplicate/keeper types differ.")
        require(not any(overlaps(pair["path"], path) for path in policy["keep"]),
                "Duplicate copy overlaps protected material.")
        old_files = list(walk(root, pair["path"]))
        kept_files = list(walk(root, pair["keep"]))
        if old.is_dir():
            old_names = {str(PurePosixPath(x).relative_to(pair["path"])) for x in old_files}
            kept_names = {str(PurePosixPath(x).relative_to(pair["keep"])) for x in kept_files}
            require(old_names == kept_names, "Duplicate trees have different file inventories.")
        selected.update(old_files)
    rows = []
    keep_checks = {}
    for rel in sorted(selected):
        kind = candidate_kind(rel, policy)
        row = snapshot(root, rel)
        row["kind"] = kind
        if kind == "duplicate-copy":
            keeper = keeper_for(root, rel, policy)
            if keeper not in keep_checks:
                keep_checks[keeper] = snapshot(root, keeper)
            check = keep_checks[keeper]
            require(row["sha256"] == check["sha256"] and row["bytes"] == check["bytes"],
                    "Copies are not byte-identical: " + rel)
            row["keeper"] = keeper
        rows.append(row)
    for path in policy["keep"]:
        if path not in keep_checks and checked(root, path).is_file():
            keep_checks[path] = snapshot(root, path)
    # The complete retained set is bound too; a newer render invalidates this plan.
    for path in walk(root, policy["current_pages"]):
        if path not in keep_checks:
            keep_checks[path] = snapshot(root, path)
    summary = {}
    for row in rows:
        part = summary.setdefault(row["kind"], {"files": 0, "bytes": 0})
        part["files"] += 1
        part["bytes"] += row["bytes"]
    return {"schema": SCHEMA, "created": datetime.datetime.now().astimezone().isoformat(),
            "project": str(root), "policy": original, "resolved_policy": policy,
            "protected_files": list(keep_checks.values()), "candidates": rows,
            "summary": summary, "candidate_files": len(rows),
            "estimated_file_bytes": sum(row["bytes"] for row in rows),
            "excluded_asset_images": excluded_assets, "files_deleted": 0}


def verify(root, row):
    require(snapshot(root, row["path"]) == {key: row[key]
            for key in ("path", "bytes", "mtime_ns", "sha256")},
            "Plan is stale; regenerate it: " + row["path"])


def apply(root, evidence, report, writers_stopped):
    require(writers_stopped, "Stop all writers/build/render processes, then pass --writers-stopped.")
    require(evidence.get("schema") == SCHEMA and evidence.get("project") == str(root),
            "Plan does not belong to this project.")
    policy = policy_check(root, evidence["policy"])
    require(policy == evidence["resolved_policy"], "Project protection changed; regenerate the plan.")
    rows = evidence["candidates"]
    require(len({row["path"] for row in rows}) == len(rows), "Duplicate candidate records.")
    for row in rows:
        require(row["kind"] == candidate_kind(row["path"], policy), "Candidate kind changed.")
        if row["kind"] == "duplicate-copy":
            require(row["keeper"] == keeper_for(root, row["path"], policy), "Keeper changed.")
            require(sha(checked(root, row["keeper"])) == row["sha256"], "Retained copy changed.")
        verify(root, row)
    for row in evidence["protected_files"]:
        verify(root, row)
    protected_set = {row["path"] for row in evidence["protected_files"]}
    require(all(path in protected_set for path in walk(root, policy["current_pages"])),
            "Retained page set changed; regenerate the plan.")
    # Exclusive creation prevents accidental replay or overwriting the cleanup journal.
    report = Path(report).absolute()
    report.parent.mkdir(parents=True, exist_ok=True)
    if report.is_relative_to(root):
        rel_report = report.relative_to(root).as_posix()
        require(not any(inside(rel_report, row["path"]) for row in rows), "Report is a cleanup target.")
    deleted = freed = 0
    with report.open("x", encoding="utf-8") as journal:
        def record(value):
            journal.write(json.dumps(value, ensure_ascii=False) + "\n")
            journal.flush()
        record({"event": "started", "project": str(root), "schema": SCHEMA,
                "candidate_files": len(rows), "created": datetime.datetime.now().astimezone().isoformat()})
        for row in rows:
            path = checked(root, row["path"])
            info = path.stat()
            require((info.st_size, info.st_mtime_ns) == (row["bytes"], row["mtime_ns"]),
                    "File changed during cleanup; stop: " + row["path"])
            record({"event": "delete-intent", **row})
            path.unlink()
            deleted += 1
            freed += row["bytes"]
            record({"event": "deleted", "path": row["path"], "bytes": row["bytes"]})
        record({"event": "complete", "deleted_files": deleted, "deleted_file_bytes": freed})
    return {"deleted_files": deleted, "deleted_file_bytes": freed, "report": str(report)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    preview = modes.add_parser("plan", help="Write a cleanup plan; never delete files.")
    preview.add_argument("project")
    preview.add_argument("--policy", required=True)
    preview.add_argument("--output", required=True)
    execute = modes.add_parser("apply", help="Delete only the verified files in an existing plan.")
    execute.add_argument("project")
    execute.add_argument("--plan", required=True)
    execute.add_argument("--report", required=True)
    execute.add_argument("--writers-stopped", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = project_root(args.project)
        if args.mode == "plan":
            result = plan(root, load(Path(args.policy)))
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            print(json.dumps({"plan": str(output.absolute()), "candidate_files": result["candidate_files"],
                              "estimated_file_bytes": result["estimated_file_bytes"],
                              "summary": result["summary"], "files_deleted": 0}, ensure_ascii=False))
        else:
            result = apply(root, load(Path(args.plan)), args.report, args.writers_stopped)
            print(json.dumps(result, ensure_ascii=False))
        return 0
    except (CleanupError, OSError, ValueError, KeyError, TypeError) as error:
        print("Cleanup refused: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
