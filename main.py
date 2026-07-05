# -*- coding: utf-8 -*-
"""
半導体メモリ定点観測レポート 自動生成スクリプト
Claude Codeをヘッドレスモード(claude -p)で実行してレポートを生成し、MDファイルとして保存する。
認証は CLAUDE_CODE_OAUTH_TOKEN(Pro/Maxのプラン枠) または ANTHROPIC_API_KEY(従量課金)のどちらか。
実行: python main.py [--mode morning|noon|night]  (省略時はJST時刻から自動判定)
"""
import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from prompts import SYSTEM_PROMPT, MODE_PROMPTS

# ---------- 設定 ----------
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "sonnet")
CLAUDE_TIMEOUT = int(os.environ.get("CLAUDE_TIMEOUT", "900"))  # 秒
REPORT_DIR = Path(__file__).parent / "reports"

JST = ZoneInfo("Asia/Tokyo")
MODE_LABELS = {"morning": "朝(寄り前)", "noon": "昼(前場後)", "night": "夜(引け後)"}


def detect_mode() -> str:
    hour = datetime.datetime.now(JST).hour
    if hour < 10:
        return "morning"
    if hour < 17:
        return "noon"
    return "night"


def _normalize_env() -> dict:
    """認証まわりの事故を自動修正した環境変数セットを返す。"""
    env = {**os.environ, "CI": "true"}
    env.pop("CLAUDECODE", None)
    api_key = env.get("ANTHROPIC_API_KEY", "")
    if api_key.startswith("sk-ant-oat"):
        env.setdefault("CLAUDE_CODE_OAUTH_TOKEN", api_key)
        env.pop("ANTHROPIC_API_KEY", None)
        print("[warn] sk-ant-oat トークンをCLAUDE_CODE_OAUTH_TOKENとして扱います")
    if env.get("CLAUDE_CODE_OAUTH_TOKEN") and env.get("ANTHROPIC_API_KEY"):
        env.pop("ANTHROPIC_API_KEY", None)
        print("[warn] OAuthとAPIキーが両方設定されているためOAuth(プラン枠)を優先します")
    return env


def generate_report(mode: str) -> str:
    """Claude Codeヘッドレスモードでレポートを生成して返す。"""
    env = _normalize_env()
    if not (env.get("CLAUDE_CODE_OAUTH_TOKEN") or env.get("ANTHROPIC_API_KEY")):
        print("[warn] 認証用の環境変数が未設定です。ローカルのログイン済み認証を試みます")

    now = datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    user_prompt = f"現在日時: {now} JST\n\n{MODE_PROMPTS[mode]}"

    cmd = [
        "claude",
        "-p", user_prompt,
        "--append-system-prompt", SYSTEM_PROMPT,
        "--allowedTools", "WebSearch,WebFetch",
        "--model", CLAUDE_MODEL,
        "--output-format", "text",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=CLAUDE_TIMEOUT,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI failed (code {result.returncode}).\n"
            f"stderr: {result.stderr[-2000:]}\nstdout: {result.stdout[-500:]}"
        )
    report = result.stdout.strip()
    if not report:
        raise RuntimeError("claude CLIの出力が空です")
    return report


def save_report(mode: str, report: str) -> Path:
    """レポートをMDファイルとしてreports/ディレクトリに保存する。"""
    REPORT_DIR.mkdir(exist_ok=True)
    now = datetime.datetime.now(JST)
    filename = f"{now.strftime('%Y-%m-%d')}_{mode}.md"
    filepath = REPORT_DIR / filename

    header = f"# 定点観測 {now.strftime('%Y/%m/%d')} {MODE_LABELS[mode]}\n\n"
    filepath.write_text(header + report, encoding="utf-8")
    return filepath


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=list(MODE_PROMPTS), default=None)
    args = parser.parse_args()
    mode = args.mode or detect_mode()

    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY", "")
    if token.startswith("sk-ant-oat") or (os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") and not os.environ.get("ANTHROPIC_API_KEY")):
        auth = "OAuth(サブスク枠)"
    elif token:
        auth = "APIキー(従量)"
    else:
        auth = "ローカルのログイン済み認証"
    print(f"[info] mode={mode} model={CLAUDE_MODEL} auth={auth}")
    report = generate_report(mode)
    print("[info] report generated:\n" + report[:500] + "...")
    filepath = save_report(mode, report)
    print(f"[done] レポート保存完了: {filepath}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)
