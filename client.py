"""终端显示模块：使用 Rich 实现实时美化输出，含 Live Todo 列表与彩色日志；
支持 info / debug 两种日志级别，debug 模式下输出请求/响应/耗时/用量等详细信息"""

import json
import time
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.rule import Rule
from rich import box

console = Console()

# ─── 日志级别感知 ──────────────────────────────────────────────────────────────

def _is_debug():
    """延迟导入，避免循环依赖"""
    from utils import is_debug
    return is_debug()

# ─── 数据模型 ────────────────────────────────────────────────────────────────

STATUS_STYLE = {
    "pending":    ("🔲", "dim white"),
    "in_progress": ("⏳", "bold yellow"),
    "processing": ("⏳", "bold yellow"),
    "completed":  ("✅", "bold green"),
}


@dataclass
class Task:
    id: str
    text: str
    status: str = "pending"


# ─── 主显示类 ─────────────────────────────────────────────────────────────────

class TerminalDisplay:
    """Rich 驱动的终端显示器，实时渲染 Todo 列表与操作日志；
    根据 log_level 自动切换 info / debug 输出粒度"""

    def __init__(self):
        self.tasks: list[Task] = []
        self._log_lines: list[str] = []  # 保存近期日志（纯文本备用）
        self._live: Optional[Live] = None
        self._layout = Layout()

    # ── 生命周期 ──────────────────────────────────────────────────────────────

    def start(self):
        """启动 Live 渲染"""
        self._live = Live(
            self._render(),
            console=console,
            refresh_per_second=1,
            vertical_overflow="visible",
        )
        self._live.start()

    def stop(self):
        if self._live:
            self._live.stop()

    # ── Todo 操作 ─────────────────────────────────────────────────────────────

    def add_task(self, task_id: str, text: str, status: str = "pending"):
        self.tasks.append(Task(id=task_id, text=text, status=status))
        self._refresh()

    def update_task(self, task_id: str, status: str, text: Optional[str] = None):
        for t in self.tasks:
            if t.id == task_id:
                t.status = status
                if text:
                    t.text = text
                break
        self._refresh()

    def show_task_summary(self):
        """强制刷新（任务列表有变动后调用）"""
        self._refresh()

    # ── 日志输出 ──────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_lines.append(f"[dim]{ts}[/dim]  {msg}")
        if len(self._log_lines) > 200:
            self._log_lines = self._log_lines[-200:]
        self._refresh()

    # ── info 级别日志 ────────────────────────────────────────────────────────

    def display_info(self, msg: str):
        self._log(f"[bold cyan]ℹ[/bold cyan]  {msg}")

    def display_success(self, msg: str):
        self._log(f"[bold green]✔[/bold green]  {msg}")

    def display_error(self, msg: str):
        self._log(f"[bold red]✘[/bold red]  {msg}")

    def display_warning(self, msg: str):
        self._log(f"[bold yellow]⚠[/bold yellow]  {msg}")

    def display_waiting(self, msg: str):
        self._log(f"[bold magenta]◌[/bold magenta]  {msg}")

    # ── debug 级别日志 ───────────────────────────────────────────────────────

    def display_debug(self, msg: str):
        """debug 级别日志，仅在 log_level=debug 时输出"""
        if _is_debug():
            self._log(f"[bold grey69]🐛[/bold grey69]  {msg}")

    def display_debug_request(self, model: str, messages_count: int, tools_count: int):
        """详细显示 API 请求要点"""
        if not _is_debug():
            return
        self._log(f"[bold grey69]🐛 ► API 请求[/bold grey69]")
        self._log(f"[dim]    模型: {model}[/dim]")
        self._log(f"[dim]    消息数: {messages_count}[/dim]")
        self._log(f"[dim]    工具数: {tools_count}[/dim]")

    def display_debug_response(self, finish_reason: str, usage: dict = None, tool_calls_count: int = 0, elapsed: float = 0):
        """详细显示 API 响应要点"""
        if not _is_debug():
            return
        self._log(f"[bold grey69]🐛 ◄ API 响应[/bold grey69]")
        self._log(f"[dim]    完成原因: {finish_reason}[/dim]")
        self._log(f"[dim]    工具调用数: {tool_calls_count}[/dim]")
        if usage:
            prompt_tokens = usage.get("prompt_tokens", "?")
            completion_tokens = usage.get("completion_tokens", "?")
            total_tokens = usage.get("total_tokens", "?")
            self._log(f"[dim]    Token 用量: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}[/dim]")
        if elapsed > 0:
            self._log(f"[dim]    耗时: {elapsed:.2f}s[/dim]")

    def display_debug_tool_detail(self, tool_name: str, args: dict, output: str, elapsed: float = 0):
        """详细显示工具执行的完整输入/输出要点"""
        if not _is_debug():
            return
        self._log(f"[bold grey69]🐛 🔧 工具详情: {tool_name}[/bold grey69]")
        # 输入参数
        try:
            pretty_args = json.dumps(args, indent=2, ensure_ascii=False)
        except Exception:
            pretty_args = str(args)
        self._log(f"[dim]    ▸ 输入参数:[/dim]")
        for line in pretty_args.split('\n'):
            self._log(f"[dim]      {line}[/dim]")
        # 输出（截断过长内容）
        truncated = output[:500] + ("..." if len(output) > 500 else "")
        self._log(f"[dim]    ▸ 输出结果 ({len(output)} 字符): {truncated}[/dim]")
        if elapsed > 0:
            self._log(f"[dim]    ▸ 执行耗时: {elapsed:.3f}s[/dim]")

    def display_debug_round(self, round_count: int, message_history_len: int):
        """显示当前轮次与消息历史长度"""
        if not _is_debug():
            return
        self._log(f"[bold grey69]🐛 第 {round_count} 轮 | 消息历史长度: {message_history_len}[/bold grey69]")

    def display_debug_config(self, model_name: str, base_url: str, workspace: str, log_level: str):
        """启动时显示配置要点"""
        if not _is_debug():
            return
        self._log(f"[bold grey69]🐛 启动配置[/bold grey69]")
        self._log(f"[dim]    模型: {model_name}[/dim]")
        self._log(f"[dim]    API 地址: {base_url}[/dim]")
        self._log(f"[dim]    工作目录: {workspace}[/dim]")
        self._log(f"[dim]    日志级别: {log_level}[/dim]")

    # ── 工具调用显示 ──────────────────────────────────────────────────────────

    def display_tool_call(self, tool_name: str, args: dict):
        """显示工具调用，添加到日志中"""
        try:
            pretty = json.dumps(args, indent=2, ensure_ascii=False)
        except Exception:
            pretty = str(args)
        
        # 将工具调用信息格式化为多行日志
        self._log(f"[bold cyan]🔧 工具:[/bold cyan] [bold]{tool_name}[/bold]")
        
        # 将参数按行添加到日志（debug 模式下显示更多，info 下精简）
        if _is_debug():
            args_lines = pretty.split('\n')
            for line in args_lines:
                self._log(f"[dim]  {line}[/dim]")
        else:
            # info 模式下只显示关键参数的一行摘要
            summary_parts = []
            for k, v in args.items():
                val_str = str(v)
                if len(val_str) > 80:
                    val_str = val_str[:80] + "..."
                summary_parts.append(f"{k}={val_str}")
            self._log(f"[dim]  {', '.join(summary_parts)}[/dim]")

    def display_final_result(self, result: str):
        self.stop()
        console.print()
        console.print(Rule("[bold green]✨ 最终结果[/bold green]", style="green"))
        console.print(
            Panel(
                result or "[dim]（无输出）[/dim]",
                title="[bold green]Agent 回答[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )

    # ── 渲染 ──────────────────────────────────────────────────────────────────

    def _render_todo(self) -> Panel:
        """渲染 Todo 列表面板"""
        if not self.tasks:
            body = Text("暂无任务", style="dim", justify="center")
        else:
            table = Table(
                show_header=True,
                header_style="bold white on grey23",
                box=box.SIMPLE_HEAVY,
                padding=(0, 1),
                expand=True,
            )
            table.add_column("ID", style="dim", width=4, no_wrap=True)
            table.add_column("任务", ratio=1)
            table.add_column("状态", width=10, justify="center")

            for t in self.tasks:
                icon, style = STATUS_STYLE.get(t.status, ("?", "white"))
                table.add_row(
                    t.id,
                    Text(t.text, overflow="fold"),
                    Text(f"{icon} {t.status}", style=style),
                )
            body = table

        return Panel(
            body,
            title="[bold blue]📋 Todo List[/bold blue]",
            border_style="blue",
            padding=(0, 1),
        )

    def _render_log(self) -> Panel:
        """渲染近期日志面板；debug 模式显示更多行数"""
        max_lines = 50 if _is_debug() else 30
        recent = self._log_lines[-max_lines:] if self._log_lines else ["[dim]等待操作...[/dim]"]
        text = Text.from_markup("\n".join(recent))
        return Panel(
            text,
            title=f"[bold white]📜 操作日志 [{'bold yellow' if _is_debug() else 'bold cyan'}]{'DEBUG' if _is_debug() else 'INFO'}[/]",
            border_style="white",
            padding=(0, 1),
        )

    def _render(self):
        """合并 Todo + 日志为单一可渲染对象"""
        layout = Layout()
        layout.split_row(
            Layout(self._render_todo(), name="todo", ratio=2),
            Layout(self._render_log(), name="log", ratio=3),
        )
        return layout

    def _refresh(self):
        if self._live:
            self._live.update(self._render())


# ─── 单例 ─────────────────────────────────────────────────────────────────────

_display_instance: Optional[TerminalDisplay] = None


def get_display() -> TerminalDisplay:
    """获取全局单例显示器"""
    global _display_instance
    if _display_instance is None:
        _display_instance = TerminalDisplay()
    return _display_instance