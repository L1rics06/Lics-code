
import json
from rich.panel import Panel


def display_tool_call(block, console):
    """将单个工具调用以带边框的卡片形式输出到终端"""
    tool_name = block.function.name
    try:
        args_dict = json.loads(block.function.arguments)
        pretty_args = json.dumps(args_dict, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        pretty_args = block.function.arguments

    display_content = f"[bold cyan]🔧 工具名称:[/bold cyan] {tool_name}\n[bold cyan]📦 传入参数:[/bold cyan]\n{pretty_args}"

    console.log(
        Panel(
            display_content,
            title="[bold yellow]⚡ 触发工具调用[/bold yellow]",
            border_style="yellow",
            expand=False
        )
    )
