# english — 英語スピーチ練習ログ（共通ルール正本・Claude Code / Codex 両方が読む）

> 2026-11-24 に CLAUDE.md から flip（Codex が英語お題のルールを読めず、Anki に入れたページが Obsidian に残り続けたため）。Claude Code 固有の補足は CLAUDE.md（このファイルを import する薄いラッパー）。

GitHub: `Muburo/english`（public）

## プロジェクト概要

英語スピーチ練習アプリで毎日 2 分程度即興で話した後の振り返りログ。
日本語で「言えなかったこと」「詰まった理由」「覚えておきたい表現」を音声日記として記録している。
文章は未整理で、思考途中・言い直し・迷いを含む。

> **詳細仕様の所在（必要時に読む）**:
> - レビュー仕様（定量指標・ライトレビュー構成・フルレビュー構成・スコア/CEFR 基準）→ [references/review-specs.md](references/review-specs.md) が正本。**レビュー生成前に必ず読む**
> - 進化レポート仕様（月次プログレストラッキング）→ [references/progress-specs.md](references/progress-specs.md) が正本。**生成前に必ず読む**
> - 日次ログの保存・ライトレビュー・push の一括フロー → english-entry スキル（`~/.claude/skills/english-entry/`）

## データ構造

```
english/
├── AGENTS.md       # 共通ルール正本（本ファイル）
├── CLAUDE.md       # Claude Code 用ラッパー（@AGENTS.md）
├── references/     # 詳細仕様（レビュー仕様・進化レポート仕様）
├── reports/        # ライトレビュー出力（quick-*.md）。archive/ に旧フル/週次レビュー
├── history/        # 練習の歩み（PRACTICE-HISTORY.md）・表現ストック（EXPRESSION-STOCK.md）
├── progress/       # 月次進化レポート（progress-YYYY-MM.md / TIMELINE.md）
├── odai/           # 英語お題の記録帳（sessions.jsonl=1日1行 / phrases.jsonl=言いたかった1件1行）＋ archive_odai.py（「チェックした英語を取り込んで」の一連の手順＝Anki照合→本体を YYYY-MM-DD/odai_page.md と記録帳へ保存→commit/push→Obsidian の元ページをゴミ箱へ）
└── YYYY-MM/        # 月別フォルダ
    └── YYYY-MM-DD/ # 日付フォルダ（1日1フォルダ）
        ├── en_log.md   # 英語スピーチの書き起こし（音声認識）
        ├── ja_log.md   # 日本語での振り返り（音声入力）
        └── odai_page.md # 英語お題の練習ページ本体（Anki照合後に保存し、Obsidian の元ページはゴミ箱へ・2026-11-21〜）
```

### 英語お題（2026-11-19〜・手順の正本＝共有スキル english-odai）
合言葉「**英語取り込んで**」「チェックした英語を取り込んで」「英語お題しまって」→ **english-odai スキル**（`~/.claude/skills/english-odai/SKILL.md`。Codex も `~/.codex/skills` 経由で同じものを読む）に従う。スキルが読めない環境でも、最低限次は守る:
1. **Anki に入れたら、同じ会話の中でページをしまうまで走る**（別の合言葉を待たない・2026-11-24 本人決定）。チェック行（`- [x]`）に `✅ Anki M/D` を付け `status: Anki済み` にしたら、すぐ `python odai/archive_odai.py` を回す。Anki 登録を anki-story-import でやった場合も同じ
2. `archive_odai.py` が1ページずつ完走する: **Anki照合**（AnkiConnect。届かないときは `✅ Anki` 印を証拠として扱い、印の無いチェック行があるページだけ止める）→ **保存**（`YYYY-MM/YYYY-MM-DD/odai_page.md`・`odai/sessions.jsonl`・`phrases.jsonl`）→ **commit/push**（commit できなければ次へ進まない）→ **Obsidian の元ページをゴミ箱へ**（OS のゴミ箱。使えなければ vault の `.trash/`）
3. 話したページの取り込み（ログ保存・CEFR・言いたかった英文の候補2案ずつ）と次の日のお題ページ作成はスキルの手順どおり

### データの特徴
- `en_log.md`: 即興スピーチのため文法・構成が不完全。音声認識の誤りも含む
- `ja_log.md`: 口語的な音声書き起こし。句読点が不完全、思考の飛躍あり
- 一部の日付フォルダには `en_log.md` のみ（`ja_log.md` なし）の場合あり

## スピーキングのコンテキストと目標

- 一人練習（聴衆なし）、約 2 分の即興。正確さよりも流暢さ・自然さを重視
- 目標: 英語を「考えながらでも止まらずに話せる」こと。完璧な表現より、軽く・自然に言い切ることを優先

## 分析の共通ルール（全レビュー共通）

### 分析の姿勢
- en_log（英語書き起こし）と ja_log（日本語振り返り）の**両方**を必ず読む
- ja_log で本人が「言えなかった」「言えるようにしたい」と自覚しているポイントを優先的に拾う
- 音声認識ミス（protein nail → protein shake 等）と本当の語彙不足を区別する
- 一般的な英語学習アドバイスは不要。このログ特有の「言い切れなさ」「詰まり方」「逃げ」を重視する
- 抽象論ではなく、再利用可能な形に分解する。厳しめ・踏み込んだ指摘歓迎。「できていない前提」で分析する

### 例文ルール（ライトレビュー + フルレビューのトップ5に適用）
- 「実際に言えなかった表現・間違えた表現」を起点にする
- 各項目に**完成形の例文を2つ**含める。例文は**フルセンテンス**（そのまま暗記して使える完全な英文）。フレーズだけで終わらせない
- en_log の実際の発話と ja_log の自覚ポイントの両方を根拠にする
- フルレビューの構造分析セクションでは en_log 引用は証拠として使うが、Anki 用の例文列挙は不要

## レビュー2種（詳細は references/review-specs.md）

> **フルレビューは休止中（2026-07-04）**: 見返さなくなったため過去分（月次・週次）は `reports/archive/` に移動し、Obsidian のインデックスも `05_Knowledge/99.💤 休眠/🗂 英語フルレビュー（2026-11-18 引退）/` へ移した。新規生成はしない（月次の定点観測は進化レポートが担う）。仕様は references/review-specs.md に残してあり、再開時はそのまま使える。

| | ライトレビュー | フルレビュー |
|---|---|---|
| トリガー | 「今日の分をレビューして」「ライトレビューして」、期間+「軽く」 | 「今月のフルレビュー」「フルレポート出して」、2週間以上の期間 |
| 対象期間 | 1日〜1週間 | 月次（指定なければ前回フルレポート以降） |
| 出力 | `reports/quick-YYYY-MM-DD.md` / `quick-YYYY-WXX.md` | `reports/review-YYYY-MM.md` / `review-YYYY-WXX-WXX.md` |
| 粒度 | 表現レベル（トップ3・フォーカス弱点・意見スピーチ弱点） | 構造・戦略レベル（トップ5・宣言vs実行・根本課題マップ・来月の戦略） |
| 役割 | 表現コーチ | 戦略コンサルタント（「練習の仕方を変えよう」） |

- レポート冒頭に定量指標＋100点スコア＋CEFR を付ける（基準は references/review-specs.md）
- フルレビューにカテゴリ別表現テーブルや Anki リストの大量列挙を含めない（それはライトの役割）

## 進化レポート（月次）と歩み

変化の過程を追うためのトラッキング層（2026-07-04 新設）。日次のライトレビューとは役割が別（コーチングではなく定点観測）。

- **進化レポート**: 月1回、前月分を生成。トリガー「英語の進化レポート」「進化レポート出して」。仕様の正本は [references/progress-specs.md](references/progress-specs.md)（構成・出力先・Obsidian 連携・git まで全部そこに従う）
- **タイムライン**: [progress/TIMELINE.md](progress/TIMELINE.md) — 1行=1ヶ月の累積ダッシュボード。レポート生成時に追記
- **歩み**: [history/PRACTICE-HISTORY.md](history/PRACTICE-HISTORY.md) — 練習方法の変遷年表。**方法を変えたら追記**（Obsidian `05_Knowledge/98.🗄 裏方/💬 英語の歩み/英語練習の歩み.md` と両更新）
- **表現ストック**: [history/EXPRESSION-STOCK.md](history/EXPRESSION-STOCK.md) — 言えるようになった表現の累積台帳（4カテゴリ・昇格パイプライン）。月次レポートとワンセットで更新。単体トリガー「表現ストック更新して」。手順は progress-specs.md「表現ストック更新」
- Obsidian の `04_Life/5.💬英語/` 直下は本人が開くものだけ（練習ページ・使い方・ライトレビュー目次・🗂 練習ログ・Road to Native。2026-11-18 再編で 2026/ フォルダは廃止）。歩み・進化レポート系は `05_Knowledge/98.🗄 裏方/💬 英語の歩み/` に置く

## 運用ルール

### コミット
- 新しい日付フォルダの追加時にコミット。メッセージは日付または内容がわかる簡潔な記述

### Obsidian 連携（レビュー生成時のフロー）
1. レビュー内容を生成 → `reports/` に保存
2. Obsidian `100_Notes/1.2026年/` に同一内容のノートを作成（年が変わったらフォルダ更新）
   - 命名: `ライトレビュー — YYYY-MM-DD.md` / `ライトレビュー — YYYY-WXX.md` / `フルレビュー — YYYY-MM.md`（`—` は em-dash）
3. インデックスに `[[ノート名]]` リンクを追加（月見出し `## YYYY-MM` の下、新しい日付が上）
   - ライト: `obsidian-vault/04_Life/5.💬英語/ライトレビュー.md`（フルのインデックスは `05_Knowledge/99.💤 休眠/🗂 英語フルレビュー（2026-11-18 引退）/フルレビュー.md` にアーカイブ済み）
4. git commit（english リポジトリ）

### public リポジトリの注意
- 個人情報（名前、職場名など）を含むログは push 前に確認
- `ja_log.md` に仕事の具体的内容が含まれる場合は注意
