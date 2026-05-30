CreateObject("WScript.Shell").Run "python """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\funpay_boost.py""", 0, False
