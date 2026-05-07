import yaml
from pathlib import Path
class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills = {}
        for f in sorted(skills_dir.rglob("SKILL.md")):
            text = f.read_text()
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body}

    def _parse_frontmatter(self, text: str) -> tuple:
        """解析 SKILL.md 的 YAML frontmatter，返回 (meta_dict, body_str)"""
        if not text.startswith("---"):
            return {}, text
        parts = text[3:].split("---", 1)
        if len(parts) < 2:
            return {}, text
        meta = yaml.safe_load(parts[0].strip()) or {}
        body = parts[1].strip()
        return meta, body

    def get_descriptions(self) -> str:
        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "")
            lines.append(f"  - {name}: {desc}")
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        skill = self.skills.get(name)
        if not skill:
            return f"Error: Unknown skill '{name}'."
        return f"<skill name=\"{name}\">\n{skill['body']}\n</skill>"