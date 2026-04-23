"""终端显示模块：使用 Rich 实现实时美化输出，含 Live Todo 列表与彩色日志"""

import json
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
from rich.columns import Columns
from rich.align import Align

console = Console()

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
    """Rich 驱动的终端显示器，实时渲染 Todo 列表与操作日志"""

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
            refresh_per_second=4,  # 降低刷新率，减少闪烁
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

    def display_tool_call(self, tool_name: str, args: dict):
        """显示工具调用，现在直接添加到日志中，不再直接打印"""
        try:
            pretty = json.dumps(args, indent=2, ensure_ascii=False)
        except Exception:
            pretty = str(args)
        
        # 将工具调用信息格式化为多行日志
        self._log(f"[bold cyan]🔧 工具:[/bold cyan] [bold]{tool_name}[/bold]")
        
        # 将参数按行添加到日志
        args_lines = pretty.split('\n')
        for line in args_lines:
            self._log(f"[dim]  {line}[/dim]")

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
        """渲染近期日志面板"""
        recent = self._log_lines[-30:] if self._log_lines else ["[dim]等待操作...[/dim]"]
        text = Text.from_markup("\n".join(recent))
        return Panel(
            text,
            title="[bold white]📜 操作日志[/bold white]",
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