"""英語お題: Anki済みの練習ページを記録に残して、Obsidian の一覧から 🗂 練習ログ/YYYY-MM/ へ移す。

使い方: python odai/archive_odai.py            # status: Anki済み のページを全部処理
        python odai/archive_odai.py --dry-run  # 何をするかだけ表示
記録先（このフォルダ）:
  sessions.jsonl … 1行=1日（日付・モード・場面・CEFR・点数）
  phrases.jsonl  … 1行=言いたかった1件（日本語・実際の発話・2案・選んだ案・Anki日・ヒント）
同じ id は上書き（二重登録しない）。
"""
import io, os, re, json, sys, shutil, pathlib

HERE = pathlib.Path(__file__).resolve().parent
VAULT = pathlib.Path(os.environ.get("OBSIDIAN_VAULT", ""))
PAGES = VAULT / "04_Life" / "5.💬英語"
ARCHIVE = PAGES / "🗂 練習ログ"


def parse(path):
    s = io.open(path, encoding="utf-8").read()
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


def main(dry):
    done = []
    for p in sorted(PAGES.glob("🗣 英語 *.md")):
        fm, sess, phrases = parse(p)
        if fm.get("status") != "Anki済み":
            continue
        dest = ARCHIVE / fm["date"][:7] / p.name
        print(f"{p.name}: 記録 {len(phrases)}件 → {dest.relative_to(PAGES)}")
        if dry:
            continue
        upsert(HERE / "sessions.jsonl", [sess], "date")
        upsert(HERE / "phrases.jsonl", phrases, "id")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dest))
        done.append(p.name)
    if not done and not dry:
        print("Anki済みのページはありません")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
