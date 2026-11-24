"""英語お題「チェックした英語を取り込んで」: Anki照合 → リポに保存 → Obsidian の元ページをゴミ箱へ。

使い方: python odai/archive_odai.py            # チェック（- [x]）のあるページを全部処理
        python odai/archive_odai.py --dry-run  # 照合と予定だけ表示（何も書かない・消さない）
一連の手順（1ページずつ。途中で止まったページは Obsidian に残す）:
  1. Anki照合 … チェックした英文が全部 Anki（AnkiConnect）に入っているか確かめ、行に「✅ Anki M/D」を付ける。
                 1つでも見つからなければそのページは止める（保存もゴミ箱もしない）
  2. 保存     … ページ本体を english/YYYY-MM/YYYY-MM-DD/odai_page.md（status: Anki済み）へ、
                 学習記録を odai/sessions.jsonl（1行=1日）・phrases.jsonl（1行=言いたかった1件）へ。同じ id は上書き
  3. コミット … english リポに commit → push（push 失敗は報告だけ。commit できなければゴミ箱に移さない）
  4. ゴミ箱   … Obsidian の元ページを OS のゴミ箱へ（Mac=Finder／Win=ごみ箱。完全削除はしない）
"""
import io, os, re, json, sys, html, datetime, pathlib, subprocess, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
VAULT = pathlib.Path(os.environ.get("OBSIDIAN_VAULT", ""))
PAGES = VAULT / "04_Life" / "5.💬英語"
REPO = HERE.parent
CHECK = re.compile(r"^(- \[x\] )(.*?)(?:\s*✅ Anki (\S+))?$", re.M)


def parse(s):
    fm = dict(re.findall(r"^(\w+): (.*)$", s.split("---")[1], re.M))
    head = s.split("## 今日のお題")[0]
    m = re.search(r"\*\*CEFR：(\w+)（(\d+)点", head)
    date = fm["date"]
    sess = {"date": date, "mode": fm.get("mode"), "scene": fm.get("scene"),
            "cefr": m.group(1) if m else None, "score": int(m.group(2)) if m else None}
    phrases = []
    for i, blk in enumerate(re.split(r"\n### ", head)[1:], 1):
        title = re.sub(r"^\d+\.\s*", "", blk.split("\n")[0])
        want = re.search(r"^言いたかった：(.*)$", blk, re.M)
        said = re.search(r"^あんたの発話：\*(.+?)\*", blk, re.M)
        opts = []
        for cm in re.finditer(r"^- \[( |x)\] (.*?)(?:\s*✅ Anki (\S+))?$", blk, re.M):
            anki = cm.group(3)
            if anki and re.fullmatch(r"\d{1,2}/\d{1,2}", anki):
                mo, d = anki.split("/")
                anki = f"{date[:4]}-{int(mo):02d}-{int(d):02d}"
            opts.append({"en": cm.group(2).strip(), "chosen": cm.group(1) == "x", "anki": anki})
        tip = re.search(r"^💡 (.*)$", blk, re.M)
        phrases.append({"id": f"{date}-{i}", "date": date, "scene": fm.get("scene"),
                        "topic": title, "ja": want.group(1).strip("「」") if want else None,
                        "said": said.group(1).strip('"') if said else None,
                        "options": opts, "tip": tip.group(1) if tip else None})
    return fm, sess, phrases


def upsert(path, rows, key):
    old = {}
    if path.exists():
        for line in io.open(path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line); old[r[key]] = r
    for r in rows:
        old[r[key]] = r
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        for k in sorted(old):
            f.write(json.dumps(old[k], ensure_ascii=False) + "\n")


# ---- Anki 照合（読むだけ。登録はしない） ----
def anki_port():
    port = os.environ.get("ANKI_CONNECT_PORT")
    if port is None:  # 8765 は実験場が使う。AnkiConnect は config.json のポート（Mac=8767）
        base = (pathlib.Path(os.environ["APPDATA"]) / "Anki2" if os.name == "nt" and os.environ.get("APPDATA")
                else pathlib.Path.home() / "Library" / "Application Support" / "Anki2")
        cfg = base / "addons21" / "2055492159" / "config.json"
        if cfg.exists():
            port = str(json.loads(cfg.read_text(encoding="utf-8")).get("webBindPort", 8765))
    return int(port or 8765)


def anki(action, **params):
    req = urllib.request.Request(f"http://127.0.0.1:{anki_port()}",
                                 json.dumps({"action": action, "version": 6, "params": params}).encode())
    r = json.load(urllib.request.urlopen(req, timeout=10))
    if r.get("error"):
        raise RuntimeError(r["error"])
    return r["result"]


def norm(t):
    t = html.unescape(re.sub(r"<[^>]+>|\[sound:[^\]]*\]", " ", t))
    return re.sub(r"\s+", " ", t.replace("’", "'").replace("—", "-")).strip().lower()


def find_in_anki(sentence):
    """英文を含むノートを探し、そのノートの登録日（YYYY-MM-DD）を返す。無ければ None。"""
    words = re.findall(r"[A-Za-z0-9-]+", sentence)
    chunks = [c for c in re.split(r"[^A-Za-z0-9\- ]+", sentence) if len(c.split()) >= 2]
    key = max(chunks, key=len).strip() if chunks else " ".join(words[:4])
    nids = anki("findNotes", query=f'"{key}"')
    if not nids:
        return None
    target = norm(sentence)
    for n in anki("notesInfo", notes=nids):
        if any(target in norm(f["value"]) for f in n["fields"].values()):
            return datetime.date.fromtimestamp(n["noteId"] / 1000).isoformat()
    return None


ANKI_UP = None  # None=未確認 / True=AnkiConnect に届く / False=届かない（未起動・サンドボックス）


def anki_up():
    global ANKI_UP
    if ANKI_UP is None:
        try:
            anki("version")
            ANKI_UP = True
        except Exception as e:
            ANKI_UP = False
            print(f"⚠ AnkiConnect に届かない（{type(e).__name__}）→ 「✅ Anki 日付」の印が付いた行はその印を信じて進む。印の無いチェック行があるページは止める")
    return ANKI_UP


def verify(s):
    """チェック行を全部照合して「✅ Anki M/D」を付けた本文と、見つからなかった英文を返す。
    Anki に届かないときは、登録した人が付けた「✅ Anki M/D」を登録の証拠として扱う
    （家の Codex で Anki に入れた直後にしまう、をサンドボックス内でも完走させるため・2026-11-24）。"""
    missing = []

    def mark(m):
        en = m.group(2).strip()
        if not anki_up():
            if m.group(3):
                return m.group(0)
            missing.append(en)
            return m.group(0)
        got = find_in_anki(en)
        if not got:
            missing.append(en)
            return m.group(0)
        return f"{m.group(1)}{en} ✅ Anki {int(got[5:7])}/{int(got[8:10])}"
    out = CHECK.sub(mark, s)
    out = re.sub(r"^status: .*$", "status: Anki済み", out, count=1, flags=re.M)
    return out, missing


def trash(p):
    if sys.platform == "darwin":
        cmd = ["osascript", "-e", f'tell application "Finder" to delete (POSIX file "{p}" as alias)']
    elif os.name == "nt":
        cmd = ["powershell", "-NoProfile", "-Command",
               "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile("
               f"'{p}','OnlyErrorDialogs','SendToRecycleBin')"]
    else:
        cmd = None
    try:
        if cmd is None:
            raise RuntimeError("ゴミ箱に移す方法がない OS")
        subprocess.run(cmd, check=True, capture_output=True)
    except Exception:
        # OS のゴミ箱が使えない（サンドボックス等）→ Obsidian 自身のゴミ箱（vault/.trash）へ移す
        dest = VAULT / ".trash" / p.name
        dest.parent.mkdir(exist_ok=True)
        if dest.exists():
            dest = dest.with_name(f"{p.stem} {datetime.datetime.now():%H%M%S}{p.suffix}")
        p.rename(dest)
        print(f"   （OS のゴミ箱が使えないので Obsidian の .trash へ: {dest.name}）")


def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True)


def main(dry):
    saved, stopped = [], []
    for p in sorted(PAGES.glob("🗣 英語 *.md")):
        s = io.open(p, encoding="utf-8").read()
        if not CHECK.search(s):
            continue  # まだチェックしていないページ（お題・話した・取り込み済み）は触らない
        fm = parse(s)[0]
        out, missing = verify(s)
        if missing:
            stopped.append(p.name)
            print(f"⛔ {p.name}: Anki に見つからない {len(missing)}件 → このページは残す")
            for en in missing:
                print(f"   - {en}")
            continue
        _, sess, phrases = parse(out)
        dest = REPO / fm["date"][:7] / fm["date"] / "odai_page.md"
        print(f"✅ {p.name}: Anki照合 {len(CHECK.findall(out))}件OK・記録 {len(phrases)}件 → {dest.relative_to(REPO)}")
        if dry:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        io.open(dest, "w", encoding="utf-8", newline="\n").write(out)
        upsert(HERE / "sessions.jsonl", [sess], "date")
        upsert(HERE / "phrases.jsonl", phrases, "id")
        saved.append((p, fm["date"], dest))
    if dry or not saved:
        if not saved and not stopped and not dry:
            print("チェック済みのページはありません")
        return 1 if stopped else 0

    paths = [str(d.relative_to(REPO)) for _, _, d in saved] + ["odai/sessions.jsonl", "odai/phrases.jsonl"]
    git("add", *paths)
    dates = "・".join(d for _, d, _ in saved)
    if git("diff", "--cached", "--quiet").returncode != 0:
        c = git("commit", "-m", f"data: {dates}の英語お題をAnki照合して保存")
        if c.returncode != 0:
            print("⛔ commit に失敗 → Obsidian のページは残す\n" + c.stderr)
            return 1
    print("コミット済み" + ("" if git("push").returncode == 0 else "（push 失敗。あとで git push）"))
    for p, _, _ in saved:
        trash(p)
        print(f"🗑 ゴミ箱へ: {p.name}")
    return 1 if stopped else 0


if __name__ == "__main__":
    sys.exit(main("--dry-run" in sys.argv))
