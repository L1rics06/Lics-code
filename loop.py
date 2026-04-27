"""Agent 主循环模块：加载工具定义与配置，驱动模型-工具交互循环直至生成最终回答；
支持 info / debug 两种日志级别，debug 模式下输出请求/响应/耗时/用量等详细信息"""

import time
from openai import OpenAI
import yaml
import json
from utils import *
from client import get_display, console

# ─── 创建全局单例 Todomanager，避免每次调用都重新创建导致任务丢失 ──────────
_todo_manager = Todomanager()

# 工具名称 -> 处理函数的映射表
TOOL_HANDLERS = {
    "run_bash": lambda **kw: run_bash(kw.get("command", "")),
    "read_file": lambda **kw: read_file(kw.get("file_path", "")),
    "write_file": lambda **kw: write_file(kw.get("file_path", ""), kw.get("content", "")),
    "append_file": lambda **kw: append_file(kw.get("file_path", ""), kw.get("content", "")),
    "todo": lambda **kw: _todo_manager.update_tasks(kw.get("tasks", []))   # ← 用单例 + 正确的 key "tasks"
}

# 加载配置文件，初始化模型客户端
with open("./config.yaml", "r") as f:
    config = yaml.safe_load(f)
    llm_client = OpenAI(
        api_key=config["model"]["api_key"],
        base_url=config["model"]["base_url"]
    )
    model = config["model"]["model_name"]

# 加载工具定义列表
with open("./tools.json", "r") as f:
    tools_list = json.load(f)


def agent_loop(query, tools):
    """Agent 主循环：持续调用模型并执行工具，直到模型返回最终回答"""
    # 初始化终端显示器
    display = get_display()
    display.start()
    
    #debug 模式：启动时显示配置要点
    display.display_debug_config(
        model_name=model,
        base_url=config["model"]["base_url"],
        workspace=str(WORKSPACE),
        log_level=LOG_LEVEL_STR,
    )
    
    messages = [{"role": "user", "content": query}]
    rounds_since_todo = 0
    used_todo = False
    
    # 显示开始消息
    display.display_info(f"开始处理查询: {query[:50]}...")
    display.show_task_summary()
    
    round_count = 0
    
    while True:
        round_count += 1
        display.display_waiting(f"第 {round_count} 轮对话，正在思考或生成回答...")
        
        #debug 模式：显示当前轮次与消息历史
        display.display_debug_round(round_count, len(messages))
        
        #debug 模式：显示 API 请求要点 
        display.display_debug_request(
            model=model,
            messages_count=len(messages),
            tools_count=len(tools),
        )
        
        #调用 API 并计时 
        t_start = time.time()
        response = llm_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools
        )
        t_elapsed = time.time() - t_start

        message = response.choices[0].message
        
        messages.append(message.model_dump(exclude_none=True))

        # debug 模式：显示 API 响应要点
        finish_reason = response.choices[0].finish_reason
        tool_calls = response.choices[0].message.tool_calls or []
        usage_dict = None
        if hasattr(response, 'usage') and response.usage:
            usage_dict = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        display.display_debug_response(
            finish_reason=finish_reason,
            usage=usage_dict,
            tool_calls_count=len(tool_calls),
            elapsed=t_elapsed,
        )

        if finish_reason != "tool_calls":
            display.display_info("对话完成，生成最终结果")
            return response.choices[0].message.content

        # 遍历处理所有并发调用的工具
        for block in tool_calls:
            tool_name = block.function.name
            try:
                arguments = json.loads(block.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            display.display_tool_call(tool_name, arguments)

            handler = TOOL_HANDLERS.get(tool_name)
            if handler:
                try:
                    t_tool_start = time.time()
                    output = handler(**arguments)
                    t_tool_elapsed = time.time() - t_tool_start
                    
                    #强制确保 tool 的返回值绝对是字符串 
                    if output is None:
                        output = "Success"
                    elif not isinstance(output, str):
                        output = str(output)
                        
                    display.display_success(f"工具 '{tool_name}' 执行成功")
                    
                    # ── debug 模式：显示工具执行的完整详情 ──────────────────
                    display.display_debug_tool_detail(
                        tool_name=tool_name,
                        args=arguments,
                        output=output,
                        elapsed=t_tool_elapsed,
                    )
                except Exception as e:
                    output = f"工具执行失败: {str(e)}"
                    display.display_error(f"工具 '{tool_name}' 执行失败: {str(e)}")
                    # ── debug 模式：失败的详情也记录 ───────────────────────
                    display.display_debug_tool_detail(
                        tool_name=tool_name,
                        args=arguments,
                        output=output,
                        elapsed=0,
                    )
            else:
                output = f"未知工具: {tool_name}"
                display.display_warning(f"未知工具调用: {tool_name}")
            
            if block.function.name == "todo":
                used_todo = True
                # 任务列表的同步已由 Todomanager.update_tasks() 内部完成，
                # 这里只需要触发一次显示刷新即可
                display.show_task_summary()

            rounds_since_todo = 0 if used_todo else rounds_since_todo + 1

            messages.append({
                "role": "tool",
                "tool_call_id": block.id,
                "name": tool_name,
                "content": output 
            })

if __name__ == "__main__":
    input_query = sanitize_text(input("Enter your query: ").strip())
    result = agent_loop(input_query, tools_list)
    display = get_display()
    display.display_final_result(result)
    console.print()