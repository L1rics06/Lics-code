"""工具函数模块：提供文件读写、命令执行、网络搜索等基础能力，供 Agent 循环调用"""

import subprocess
import yaml
import logging
from pathlib import Path

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
    WORKSPACE = Path(config["app"]["workspace"]).resolve()


def sanitize_text(text: str) -> str:
    """清洗字符串：抹除幽灵字符/代理字符，防止网络库崩溃"""
    if not isinstance(text, str):
        return text
    return text.encode("utf-8", errors="replace").decode("utf-8")


def run_bash(command: str) -> str:
    """在沙箱中执行 shell 命令；禁止高危操作"""
    ban = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(bad in command for bad in ban):
        return "命令包含不允许的字符或操作。"
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        output = result.stdout.strip()
        if not output:
            return "命令执行成功，无终端输出。"
        return output
    except subprocess.CalledProcessError as e:
        error_msg = f"命令执行失败。错误码: {e.returncode}\n错误信息: {e.stderr.strip()}"
        logging.error(f"Error occurred while running bash command: {error_msg}")
        return error_msg
    except Exception as e:
        return f"系统调用异常: {str(e)}"


def path_sandbox(p: str) -> Path:
    """将相对路径解析到工作区内，防止路径逃逸"""
    path = (WORKSPACE / p).resolve()
    if not path.is_relative_to(WORKSPACE):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def read_file(file_path: str) -> str:
    """读取工作区内指定文件的全部内容"""
    try:
        path = path_sandbox(file_path)
        text = path.read_text()
        return text
    except Exception as e:
        return f"读取文件失败: {str(e)}"


def write_file(file_path: str, content: str) -> str:
    """将内容写入工作区内指定文件（自动创建父目录）"""
    try:
        path = path_sandbox(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return "文件写入成功。"
    except Exception as e:
        return f"写入文件失败: {str(e)}"


def append_file(file_path: str, content: str) -> str:
    """将内容追加到工作区内指定文件末尾（自动创建父目录）"""
    try:
        path = path_sandbox(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return "文件追加成功。"
    except Exception as e:
        return f"追加文件失败: {str(e)}"




def edit_file(file_path: str, content: str) -> str:
    """覆盖写入工作区内已有文件（文件不存在则报错）"""
    try:
        path = path_sandbox(file_path)
        if not path.exists():
            return "文件不存在，无法编辑。"
        path.write_text(content)
        return "文件编辑成功。"
    except Exception as e:
        return f"编辑文件失败: {str(e)}"
