"""Formatting-only regeneration from saved report text; no statistics rerun."""
from pathlib import Path
import textwrap
import report
p=Path(__file__).resolve().parent
source=(p/'report.py').read_text(encoding='utf-8')
block=' doc=Document()'+source.split(' doc=Document()',1)[1].split(' print(json.dumps(f',1)[0]
namespace=dict(vars(report));namespace['text']=(p/'公平消融实验结果报告.md').read_text(encoding='utf-8')
exec(textwrap.dedent(block),namespace)
print('Formatting-only DOCX rebuild complete')
