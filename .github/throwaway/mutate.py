"""Undo each fix in turn and show that the tests written for it fail. Throwaway, fork only."""
import subprocess, sys
P = "crates/engine/src/file_access.rs"
pkg = sys.argv[1]
src = open(P, encoding="utf8").read()
OLD = '''root.components().all(|r| path.next().is_some_and(|p| same_component(p, r)))
}

fn same_component(a: Component, b: Component) -> bool {
    if a == b {
        return true;
    }
    if !cfg!(windows) {
        return false;
    }
    match (a.as_os_str().to_str(), b.as_os_str().to_str()) {
        (Some(a), Some(b)) => a.to_lowercase() == b.to_lowercase(),
        _ => false,
    }'''
MUTANTS = {
    "device names": ([(' | "¹" | "²" | "³"', "")], ["device_names", "refuses_devices"]),
    "colon": ([("split(['.', ':'])", "split('.')")], ["device_names"]),
    "exact compare": ([("root.components().all(|r| path.next() == Some(r))", OLD)],
                      ["names_are_compared_exactly", "a_case_sensitive_folder_keeps_a_differently_cased_name_out"]),
    "entry in its real case": ([("return Ok(std::fs::canonicalize(&entry).unwrap_or(entry));", "return Ok(entry);")], ["refuses_devices"]),
}
bad = 0
for name, (edits, must_fail) in MUTANTS.items():
    if not all(a in src for a, _ in edits):
        print(f"--- {name}: not in this app, skipped", flush=True)
        continue
    text = src
    for a, b in edits:
        text = text.replace(a, b)
    open(P, "w", encoding="utf8").write(text)
    r = subprocess.run(["cargo", "test", "--locked", "-p", pkg, "--lib", "file_access", "--", "--test-threads=1"], capture_output=True, text=True, encoding="utf8", errors="replace")
    failed = [l for l in r.stdout.splitlines() if l.startswith("test ") and l.endswith("FAILED")]
    print(f"--- without {name}: exit {r.returncode}", flush=True)
    print("\n".join(failed), flush=True)
    for m in must_fail:
        if not any(m in l for l in failed):
            print(f"!!! expected a failure in {m}", flush=True)
            bad += 1
    if "error" in r.stderr and not failed:
        print(r.stderr[-3000:], flush=True)
        bad += 1
open(P, "w", encoding="utf8").write(src)
sys.exit(1 if bad else 0)
