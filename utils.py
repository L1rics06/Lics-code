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


class Todomanager:
    """实时任务管理器，集成终端显示功能"""
    
    def __init__(self):
        self.tasks = []
        self._display = None
    
    def _get_display(self):
        """延迟加载终端显示器，避免循环导入"""
        if self._display is None:
            try:
                from client import get_display  # 从 client 导入而不是 terminal_display
                self._display = get_display()
            except ImportError:
                return None
        return self._display
    
    def update_tasks(self, new_tasks: list) -> str:
        """更新任务列表并更新显示"""
        if len(new_tasks) > 10:
            return "任务列表过长，请限制在10条以内。"
        
        validated_tasks = []
        wether_processed = False
        
        for i, task in enumerate(new_tasks):
            text = task.get("text", "").strip()
            status = task.get("status", "pending").strip().lower()
            task_id = task.get("id", str(i+1))
            
            if not text:
                return f"任务文本不能为空 (任务ID: {task_id})。"
            if status not in ["pending", "completed", "processing"]:
                return f"任务状态无效 (任务ID: {task_id})，必须是 'pending', 'completed' 或 'processing'。"
            if status == "processing":
                wether_processed = True 
            
            validated_tasks.append({
                "id": task_id,
                "text": text,
                "status": status    
            })
        
        # 更新内部状态
        self.tasks = validated_tasks
        
        # 同步到终端显示器
        display = self._get_display()
        if display:
            # 检查现有任务并进行智能更新
            existing_task_ids = {t.id for t in display.tasks}
            new_task_ids = {t["id"] for t in validated_tasks}
            
            # 更新现有任务
            for new_task in validated_tasks:
                task_id = new_task["id"]
                if task_id in existing_task_ids:
                    display.update_task(task_id, status=new_task["status"], text=new_task["text"])
                else:
                    display.add_task(task_id, new_task["text"], new_task["status"])
            
            # 移除已删除的任务
            display.tasks = [t for t in display.tasks if t.id in new_task_ids]
        
        return self.render()
    
    def render(self) -> str:
        """渲染任务列表为文本"""
        if not self.tasks:
            return "当前没有待办任务。"
        
        lines = []
        for task in self.tasks:
            status_symbol = "✅" if task["status"] == "completed" else ("⏳" if task["status"] == "processing" else "🔲")
            lines.append(f"{status_symbol} [{task['id']}] {task['text']}")
        
        return "\n".join(lines)