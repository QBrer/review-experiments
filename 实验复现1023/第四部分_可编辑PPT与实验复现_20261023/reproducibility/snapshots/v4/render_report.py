from pathlib import Path
import pythoncom,win32com.client,json
root=Path(__file__).resolve().parent
pythoncom.CoInitialize();app=win32com.client.DispatchEx('Word.Application');app.Visible=False;app.DisplayAlerts=0;app.AutomationSecurity=3
try:
 d=app.Documents.Open(str(root/'实验执行结果报告.docx'),ReadOnly=True,AddToRecentFiles=False,Visible=False,OpenAndRepair=False)
 d.Repaginate();v={'pages':d.ComputeStatistics(2),'tables':d.Tables.Count,'images':d.InlineShapes.Count}
 d.ExportAsFixedFormat(str(root/'实验执行结果报告.pdf'),17,OpenAfterExport=False);d.Close(False)
 (root/'报告格式检查.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8');print(v)
finally:app.Quit();pythoncom.CoUninitialize()
