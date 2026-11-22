#!/usr/bin/env python3
"""Harvest exactly 1,000 source-code trading strategy implementations from public repositories.

This is a source acquisition stage only. It preserves original files, provenance, repository
commit IDs, licenses, and SHA-256 fingerprints. It does not claim that every file is unique
at the mechanism level or that any strategy is profitable.
"""
from __future__ import annotations
import ast, csv, hashlib, re, shutil, subprocess
from pathlib import Path

ROOT = Path("source-harvest")
SRC = ROOT / "sources"
LIC = ROOT / "licenses"
TARGET = 1000
REPOS = {
    "pynecore": ("https://github.com/theonetrade/pynecore-strategies.git", "main"),
    "freqtrade_stuff": ("https://github.com/PeetCrypto/freqtrade-stuff.git", "main"),
    "mt5_experts": ("https://github.com/GeneralTradingSarl/expert-mt5.git", "main"),
    "freqtrade_official": ("https://github.com/freqtrade/freqtrade-strategies.git", "main"),
    "freqtrade_huge": ("https://github.com/keithorange/HUGE_FreqTrade_Strategy_Collection.git", "main"),
}

def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()

def clone(slug, url, branch, base):
    dest = base / slug
    run("git", "clone", "--quiet", "--depth", "1", "--branch", branch, url, str(dest))
    sha = run("git", "-C", str(dest), "rev-parse", "HEAD")
    return dest, sha

def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def py_is_strategy(p):
    try:
        tree=ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, UnicodeError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases=" ".join(ast.unparse(x) for x in node.bases)
            methods={x.name for x in node.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))}
            if "IStrategy" in bases and ({"populate_entry_trend","populate_buy_trend"} & methods):
                return True
    return False

def pine_is_strategy(p):
    s=p.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(r"(?<![A-Za-z0-9_])strategy\s*\(", s))

def mql_is_ea(p):
    s=p.read_text(encoding="utf-8-sig", errors="replace")
    return bool(re.search(r"\bOnInit\s*\(",s) and re.search(r"\bOnTick\s*\(",s))

def main():
    work=Path("/tmp/strategy-source-repositories")
    shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    shutil.rmtree(ROOT, ignore_errors=True); SRC.mkdir(parents=True); LIC.mkdir(parents=True)
    repos={}
    for slug,(url,branch) in REPOS.items():
        path,sha=clone(slug,url,branch,work)
        repos[slug]=(path,sha,url)
        print(f"CLONED {slug} {sha}", flush=True)

    pyne,pyne_sha,pyne_url=repos["pynecore"]
    freq,freq_sha,freq_url=repos["freqtrade_stuff"]
    mt5,mt5_sha,mt5_url=repos["mt5_experts"]
    official,official_sha,official_url=repos["freqtrade_official"]
    huge,huge_sha,huge_url=repos["freqtrade_huge"]

    pine=[p for p in (pyne/"assets/strategy/bit-exact").rglob("*.pine") if pine_is_strategy(p)]
    pine.sort(key=lambda p:p.relative_to(pyne).as_posix())
    if len(pine)<384: raise RuntimeError(f"Expected at least 384 Pine strategy implementations; found {len(pine)}")

    python_candidates=[]
    for base,slug,sha,url in [
        (freq,"freqtrade_stuff",freq_sha,freq_url),
        (official,"freqtrade_official",official_sha,official_url),
        (huge,"freqtrade_huge",huge_sha,huge_url),
    ]:
        for p in base.rglob("*.py"):
            if py_is_strategy(p):
                python_candidates.append((p,slug,sha,url,base))
    priority={"freqtrade_stuff":0,"freqtrade_official":1,"freqtrade_huge":2}
    python_candidates.sort(key=lambda x:(priority[x[1]],x[0].relative_to(x[4]).as_posix()))
    py_selected=[]; py_hashes=set()
    for item in python_candidates:
        h=digest(item[0])
        if h in py_hashes: continue
        py_hashes.add(h); py_selected.append(item)
        if len(py_selected)==429: break
    if len(py_selected)<429:
        raise RuntimeError(f"Need 429 distinct Freqtrade strategy source files; found {len(py_selected)}")

    mql=[]
    for p in (mt5/"mql5_experts_mt5").rglob("*.mq5"):
        if mql_is_ea(p): mql.append(p)
    mql.sort(key=lambda p:p.relative_to(mt5).as_posix())
    if len(mql)<187: raise RuntimeError(f"Need 187 MT5 EA implementations; found {len(mql)}")

    selected=[]
    for p in pine[:384]:
        selected.append((p,"pynecore","pine",pyne_sha,pyne_url,pyne))
    for p,slug,sha,url,base in py_selected:
        selected.append((p,slug,"python",sha,url,base))
    for p in mql[:250]:
        selected.append((p,"mt5_experts","mql5",mt5_sha,mt5_url,mt5))

    seen=set(); records=[]
    for i,(p,slug,kind,commit,url,base) in enumerate(selected,1):
        if len(records)>=TARGET: break
        h=digest(p)
        if h in seen: continue
        seen.add(h)
        rel=p.relative_to(base).as_posix()
        ext=p.suffix.lower()
        dest=SRC/f"{i:04d}_{slug}{ext}"
        shutil.copyfile(p,dest)
        records.append({
            "harvest_id":f"SRC{i:04d}","source_family":slug,"implementation_language":kind,
            "original_path":rel,"source_url":f"{url[:-4]}/blob/{commit}/{rel}",
            "repository_url":url[:-4],"commit_sha":commit,"sha256":h,
            "bytes":p.stat().st_size,"artifact_path":dest.as_posix(),
            "static_type_check":"Pine strategy() declaration" if kind=="pine" else
              ("Freqtrade IStrategy with entry method" if kind=="python" else "MQL5 OnInit + OnTick Expert Advisor"),
            "audit_status":"HARVESTED_NOT_YET_MECHANISM_AUDITED"
        })
    if len(records)!=TARGET:
        raise RuntimeError(f"Exact target not met after exact-file deduplication: {len(records)} / {TARGET}")

    for slug,(base,sha,url) in repos.items():
        candidates=[base/"LICENSE",base/"LICENSE.md",base/"COPYING",base/"COPYING.md"]
        license_file=next((p for p in candidates if p.is_file()),None)
        if license_file:
            shutil.copyfile(license_file,LIC/f"{slug}_{license_file.name}")
        else:
            (LIC/f"{slug}_LICENSE_NOT_FOUND.txt").write_text(
                f"No root license file found at harvest time. Verify licensing before redistribution.\nRepository: {url}\nCommit: {sha}\n"
            )

    fields=list(records[0])
    with (ROOT/"manifest.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(records)
    (ROOT/"README.md").write_text("""# 1,000-source strategy implementation harvest

This artifact contains exactly 1,000 individual source files fetched from public repositories:
- 384 TradingView Pine strategy scripts from theonetrade/pynecore-strategies
- 429 Freqtrade IStrategy implementations from the PeetCrypto collection, with official/community fallback pools if needed
- 187 MetaTrader 5 Expert Advisors from GeneralTradingSarl/expert-mt5

Each item passed a minimal language-specific source check and is preserved byte-for-byte in sources/. manifest.csv records original path, source URL, exact repository commit, SHA-256, size, and artifact path. Repository license files are preserved under licenses/.

Scope: This is the raw source harvest stage. It is not yet a claim of 1,000 unique trading mechanisms. Exact duplicate file hashes are removed; near-duplicate/ported/rebranded logic still requires semantic audit. No profitability or backtest claim is made. Check each original license before copying code into another product or redistributing it.
""",encoding="utf-8")
    print(f"HARVEST_COMPLETE files={len(records)} pine={sum(r['implementation_language']=='pine' for r in records)} freqtrade={sum(r['implementation_language']=='python' for r in records)} mt5={sum(r['implementation_language']=='mql5' for r in records)} unique_sha256={len(seen)}",flush=True)

if __name__=="__main__":
    main()
