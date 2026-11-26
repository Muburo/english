"""英会話の通話「取り込んで」の後半: Anki照合 → リポに保存 → Obsidian の 📞 通話ページをゴミ箱へ。

使い方: python call/archive_call.py              # チェック（- [x]）のある 📞 通話ページを全部処理
        python call/archive_call.py --dry-run    # 照合と予定だけ表示（何も書かない・消さない）
        python call/archive_call.py --empty-ok   # チェック0件の「候補」ページも、記録だけ残して片付ける（本人が0件で良いと言ったとき）
一連の手順は英語お題（odai/archive_odai.py）と同じで、照合・ゴミ箱・記録帳の書き方はそちらの部品を使う:
  1. Anki照合 … チェックした英文が全部 Anki に入っているか確かめ「✅ Anki M/D」を付ける。1つでも無ければそのページは残す
  2. 保存     … ページ本体を english/YYYY-MM/YYYY-MM-DD/call_page[-N].md へ、
                 記録を call/calls.jsonl（1行=1通話）・phrases.jsonl（1行=候補1件）へ。同じ id は上書き
  3. コミット … commit → push（push 失敗は報告だけ。commit できなければゴミ箱に移さない）
  4. ゴミ箱   … Obsidian の元ページを OS のゴミ箱へ
書式の正本: ~/.claude/skills/english-call/references/page-format.md
"""
import io, re, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "odai"))
import archive_odai as od  # noqa: E402  （照合 verify・ゴミ箱 trash・git・upsert・ANKI_UP を共有）

REPO = od.REPO
PAGES = od.PAGES
SECTIONS = {"🟥": "言えなかった", "🟧": "直された", "🟩": "自分で出せた"}


def parse(s):
    fm = dict(re.findall(r"^(\w+): (.*)$", s.split("---")[1], re.M))
    pid = fm.get("id") or fm["date"]
    date = fm["date"]
    head = s.split("## 🔁")[0].split("## 📝")[0]
    phrases, kind = [], None
    for part in re.split(r"^(## .*)$", head, flags=re.M):
        if part.startswith("## "):
            kind = next((v for k, v in SECTIONS.items() if k in part), None)
            continue
        if not kind:
            continue
        for blk in re.split(r"\n### ", "\n" + part)[1:]:
            m = re.match(r"(\d+)\.\s*(.*)", blk.split("\n")[0])
            if not m:
                continue
            ja = re.search(r"^日本語：(.*)$", blk, re.M)
            said = re.search(r"^通話では：(.*)$", blk, re.M)
            tip = re.search(r"^💡 (.*)$", blk, re.M)
            for cm in re.finditer(r"^- \[( |x)\] (.*?)(?:\s*✅ Anki (\S+))?$", blk, re.M):
                anki = cm.group(3)
                if anki and re.fullmatch(r"\d{1,2}/\d{1,2}", anki):
                    mo, d = anki.split("/")
                    anki = f"{date[:4]}-{int(mo):02d}-{int(d):02d}"
                phrases.append({"id": f"{pid}-{m.group(1)}", "call": pid, "date": date, "scene": fm.get("scene"),
                                "kind": kind, "expr": m.group(2).strip(),
                                "ja": ja.group(1).strip().strip("「」") if ja else None,
                                "said": said.group(1).strip() if said else None,
                                "en": cm.group(2).strip(), "chosen": cm.group(1) == "x", "anki": anki,
                                "tip": tip.group(1) if tip else None})
    sess = {"id": pid, "date": date, "scene": fm.get("scene"),
            "candidates": len(phrases), "chosen": sum(p["chosen"] for p in phrases)}
    return fm, pid, sess, phrases


def main(dry, empty_ok):
    saved, stopped = [], []
    for p in sorted(PAGES.glob("📞 通話 *.md")):
        s = io.open(p, encoding="utf-8").read()
        has_check = bool(od.CHECK.search(s))
        if not has_check and not empty_ok:
            continue  # まだチェックしていないページは触らない
        out, missing = od.verify(s) if has_check else (re.sub(r"^status: .*$", "status: 片付け（0件）", s, count=1, flags=re.M), [])
        if missing:
            stopped.append(p.name)
            print(f"⛔ {p.name}: " + ("Anki に見つからない" if od.ANKI_UP else "Anki に届かず・✅ 印も無い") + f" {len(missing)}件 → このページは残す")
            for en in missing:
                print(f"   - {en}")
            continue
        fm, pid, sess, phrases = parse(out)
        suffix = pid[len(fm["date"]):]  # "" or "-2"
        dest = REPO / fm["date"][:7] / fm["date"] / f"call_page{suffix}.md"
        print(f"✅ {p.name}: Anki照合 {len(od.CHECK.findall(out))}件OK・候補 {len(phrases)}件 → {dest.relative_to(REPO)}")
        if dry:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        io.open(dest, "w", encoding="utf-8", newline="\n").write(out)
        od.upsert(HERE / "calls.jsonl", [sess], "id")
        od.upsert(HERE / "phrases.jsonl", phrases, "id")
        saved.append((p, pid, dest))
    if dry or not saved:
        if not saved and not stopped and not dry:
            print("チェック済みの 📞 通話ページはありません")
        return 1 if stopped else 0

    paths = [str(d.relative_to(REPO)) for _, _, d in saved] + ["call/calls.jsonl", "call/phrases.jsonl"]
    od.git("add", *paths)
    ids = "・".join(i for _, i, _ in saved)
    if od.git("diff", "--cached", "--quiet").returncode != 0:
        c = od.git("commit", "-m", f"data: {ids}の英会話通話をAnki照合して保存")
        if c.returncode != 0:
            print("⛔ commit に失敗 → Obsidian のページは残す\n" + c.stderr)
            return 1
    print("コミット済み" + ("" if od.git("push").returncode == 0 else "（push 失敗。あとで git push）"))
    for p, _, _ in saved:
        od.trash(p)
        print(f"🗑 ゴミ箱へ: {p.name}")
    return 1 if stopped else 0


if __name__ == "__main__":
    sys.exit(main("--dry-run" in sys.argv, "--empty-ok" in sys.argv))
