from pathlib import Path
import json,pythoncom,win32com.client
root=Path(__file__).resolve().parent
pythoncom.CoInitialize();app=win32com.client.DispatchEx('Word.Application');app.Visible=False;app.DisplayAlerts=0;app.AutomationSecurity=3
try:
 d=app.Documents.Open(str(root/'公平消融实验结果报告.docx'),ReadOnly=True,AddToRecentFiles=False,Visible=False,OpenAndRepair=False)
 d.Repaginate();r={'pages':d.ComputeStatistics(2),'tables':d.Tables.Count,'images':d.InlineShapes.Count,'opened_without_repair':True}
 d.ExportAsFixedFormat(str(root/'公平消融实验结果报告.pdf'),17,OpenAfterExport=False);d.Close(False)
 (root/'报告格式检查.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(r)
finally:app.Quit();pythoncom.CoUninitialize()
