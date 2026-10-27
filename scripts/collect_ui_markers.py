"""Collect existing explicit gettext markers after template and Python edits."""
import ast
import json
import re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
file=root/'locale/messages.json'
messages=set(json.loads(file.read_text(encoding='utf-8')))
for folder in ('accounts','appointments','consultations','core','dashboard','medical_records','notifications','specialty','availability'):
    for path in (root/folder).glob('*.py'):
        if path.name.startswith('test'): continue
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node,ast.Call) and ast.unparse(node.func) in ('ui_gettext','_','gettext','gettext_lazy') and node.args:
                if isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str): messages.add(node.args[0].value)
for path in (root/'templates').rglob('*.html'):
    for match in re.finditer(r'{%\s*(?:translate|trans)\s+((?:"(?:[^"\\]|\\.)*")|(?:\'(?:[^\'\\]|\\.)*\'))',path.read_text(encoding='utf-8')):
        messages.add(ast.literal_eval(match.group(1)))
for path in (root/'static/js').glob('*.js'):
    for match in re.finditer(r'(?:uiGettext|gettext|\bt)\(\s*((?:"(?:[^"\\]|\\.)*")|(?:\'(?:[^\'\\]|\\.)*\'))',path.read_text(encoding='utf-8')):
        messages.add(ast.literal_eval(match.group(1)))
file.write_text(json.dumps(sorted(messages),ensure_ascii=False,indent=2),encoding='utf-8')
print(len(messages),'collected messages')
