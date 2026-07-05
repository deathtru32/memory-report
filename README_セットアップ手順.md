# 半導体メモリ定点観測 自動レポート（サブスクリプション枠版）

Claude Pro/Maxの**プラン料金内**で、1日3回（8:10 / 12:00 / 22:00 JST）Claudeが情報収集し、
T1〜T8監視トリガーに紐づけた要約レポートをNotionへ自動投稿します。

## 仕組み（API従量課金版との違い）

```
GitHub Actions (定時起動・無料枠内)
  └─ Claude Code CLI ヘッドレスモード (claude -p)
       ├─ 認証: CLAUDE_CODE_OAUTH_TOKEN ← Pro/Maxのプラン枠を消費(追加課金なし)
       ├─ ツール: WebSearch / WebFetch のみ許可
       └─ 出力(markdown) → Python → Notion API(無料)でDBへページ作成
```

- Messages APIを直接呼ばず、**Claude Codeとして実行**します。Pro/Maxユーザーが
  `claude setup-token` で生成するOAuthトークンは、公式のGitHub Actions連携で
  APIキーの代替として明示的にサポートされている方式です
- 使用量は**あなたのサブスクの利用枠（5時間ごとのローリング枠＋週次上限）から消費**されます
- 追加の金銭コストはゼロ（Pro $20/月 または Max のプラン料金のみ）

## セットアップ（所要 約30分）

### 1. OAuthトークンの生成（要: Pro/Maxプラン＋ローカルPC）
```bash
npm install -g @anthropic-ai/claude-code   # 未インストールの場合
claude                                      # 起動し、サブスクのアカウントで /login 済みであること
claude setup-token                          # ブラウザが開きOAuthフロー→長期トークンが表示される
```
表示されたトークン（一度しか表示されません）を控える → `CLAUDE_CODE_OAUTH_TOKEN`

### 2. Notion側の準備
1. https://www.notion.so/my-integrations で Internal インテグレーションを作成
   → シークレットを控える（`NOTION_TOKEN`）
2. データベース「デイリーレポート」を作成し、プロパティを**この名前どおり**用意:
   | プロパティ名 | タイプ | 選択肢 |
   | --- | --- | --- |
   | レポート名 | タイトル | |
   | 日付 | 日付 | |
   | 実行回 | セレクト | 朝(寄り前) / 昼(前場後) / 夜(引け後) |
   | シグナル | セレクト | 変化なし / 変化あり |
3. DBページ右上「…」→「コネクト」→ 作成したインテグレーションを追加（忘れると403）
4. DBのURLの32桁英数を控える → `NOTION_DATABASE_ID`

### 3. GitHubリポジトリ
1. **Private**リポジトリを作成し、この4ファイルを同じ配置でアップロード:
   `main.py` / `prompts.py` / `requirements.txt` / `.github/workflows/daily_report.yml`
2. Settings → Secrets and variables → Actions → Secrets に3件登録:
   `CLAUDE_CODE_OAUTH_TOKEN` / `NOTION_TOKEN` / `NOTION_DATABASE_ID`

### 4. テスト実行
Actions タブ → memory-market-report → Run workflow（mode: night 等）
→ NotionのDBにページが生成されれば完成。以後は毎日3回自動実行。

## プラン枠の消費とレート制限の考え方

- 1回の実行 ≒ Claude Code の1プロンプト（内部でWeb検索を最大8回実行）
- Proプランの目安は数十プロンプト/5時間。**3回の実行はそれぞれ別の5時間枠に収まる時刻**
  （8:10/12:00/22:00）に配置してあるため、通常利用と併用しても余裕があります
- 自分が対話で使っている枠と共有される点に注意。枠を使い切ったタイミングの実行は
  失敗しますが、次のスケジュールで自動的に再開します（レポートが1回飛ぶだけ）
- 実行が失敗した場合、GitHubから通知メールが届きます

## 重要な注意（規約・セキュリティ）

- OAuthトークンは**Claude Code経由の利用のみが認められた方式**です。このトークンで
  Messages APIを直接呼ぶ改造はしないでください（本構成はCLI経由なので問題ありません）
- トークンは個人アカウントに紐づきます。**必ずPrivateリポジトリ＋GitHub Secrets**で管理し、
  コードやログに出力しないこと
- トークンが失効した場合（logout・革命的な仕様変更等）は `claude setup-token` を再実行して
  Secretsを更新してください

## カスタマイズ

- 監視項目・銘柄・出力形式 → `prompts.py` を編集（ダッシュボード更新時はここにも反映）
- 実行時刻 → `daily_report.yml` の cron（UTC表記＝JST−9時間）
- モデル → リポジトリ Variables に `CLAUDE_MODEL`（`sonnet` / Maxなら `opus` も可）
- 平日のみ → cron末尾を `* * 0-4`（朝）/ `* * 1-5`（昼・夜）に変更

## 制約

- GitHub Actionsのcronは数分〜15分遅延あり（朝は8:10起動で吸収済み）
- リポジトリに60日間コミットがないとスケジュールが自動停止（通知メールから再有効化）
- Privateリポジトリの無料枠は2,000分/月。本ワークフローは約300〜500分/月で収まります
- 株価数値はWeb検索経由のため遅延・誤差があります。執行判断は証券アプリで確認すること
- レポートは情報整理であり投資助言ではありません

## トラブルシューティング

| 症状 | 原因 | 対処 |
| --- | --- | --- |
| `Invalid API key` | `sk-ant-oat...`(OAuthトークン)を`ANTHROPIC_API_KEY`に入れている | 変数名を`CLAUDE_CODE_OAUTH_TOKEN`にする（修正版main.pyは自動で読み替えます） |
| `cannot be launched inside another Claude Code session` | Claude Codeの中からローカルテストしている | 普通のターミナルで実行する（修正版main.pyはCLAUDECODE変数を自動除去して回避します） |
| 長時間無出力→タイムアウト | 認証失敗状態でCLIがハングしている場合が大半 | まず `claude -p "1+1は?"` の単体テストで認証を確認してから本体を実行 |
| Notion 403 | DBにインテグレーションを「コネクト」していない | DB右上「…」→コネクト→インテグレーション追加 |
| Notion 400 (property) | DBのプロパティ名が手順と不一致 | 「レポート名/日付/実行回/シグナル」を名前どおりに作成 |

### ローカルでの正しいテスト手順（普通のターミナルで）
```bash
export CLAUDE_CODE_OAUTH_TOKEN="(setup-tokenで再発行したトークン)"
export NOTION_TOKEN="(再発行したNotionシークレット)"
export NOTION_DATABASE_ID="(32桁のID)"
claude -p "1+1は?" --output-format text   # ①認証の単体確認(数秒で「2」が返ればOK)
python3 main.py --mode noon                # ②本体実行(2〜5分)
```
※ローカルでClaude Codeにログイン済みなら、トークンをexportせず②だけでも動きます（GitHub Actions用にはSecretsが必須）。
※トークンをコマンドラインに直書きしない（psコマンドで他プロセスから見えるため）。

## 発展（第2段階の候補）

- 週次サマリー: 週末に7日分を読み込ませ週次レポートDBへ自動転記
- シグナル「変化あり」検出時のみメール/LINE通知するステップの追加
- 決算日（ハイパースケーラー決算、キオクシアQ1、MU FQ4）だけ調査を深くする特別モード
