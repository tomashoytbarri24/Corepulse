Option Explicit
Dim fso, shell, root, launcher, pointer, chosen, localVenv, runtimeBase, pyFolder, verFolder, candidate, newestDate, stream
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = fso.BuildPath(root, "corepulse_launcher.py")

If Not fso.FileExists(launcher) Then
    MsgBox "No se encontró corepulse_launcher.py en la carpeta de CorePulse.", vbCritical, "CorePulse"
    WScript.Quit 1
End If

shell.CurrentDirectory = root
shell.Environment("PROCESS")("COREPULSE_SILENT_BOOTSTRAP") = "1"
chosen = ""

' 1) Runtime exacto validado por esta copia de CorePulse.
pointer = fso.BuildPath(root, ".corepulse_runtime_python.txt")
If fso.FileExists(pointer) Then
    On Error Resume Next
    Set stream = fso.OpenTextFile(pointer, 1, False)
    If Err.Number = 0 Then
        chosen = Trim(stream.ReadAll)
        stream.Close
        chosen = Replace(chosen, "python.exe", "pythonw.exe", 1, -1, 1)
        If Not fso.FileExists(chosen) Then chosen = ""
    Else
        Err.Clear
    End If
    On Error GoTo 0
End If

' 2) Entorno local del proyecto, si existe.
If chosen = "" Then
    localVenv = fso.BuildPath(root, ".venv\Scripts\pythonw.exe")
    If fso.FileExists(localVenv) Then chosen = localVenv
End If

' 3) Runtime más reciente de CorePulse en LOCALAPPDATA.
If chosen = "" Then
    runtimeBase = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\CorePulse\runtime"
    If fso.FolderExists(runtimeBase) Then
        newestDate = #1/1/1970#
        For Each pyFolder In fso.GetFolder(runtimeBase).SubFolders
            For Each verFolder In pyFolder.SubFolders
                candidate = fso.BuildPath(verFolder.Path, "Scripts\pythonw.exe")
                If fso.FileExists(candidate) Then
                    If verFolder.DateLastModified >= newestDate Then
                        newestDate = verFolder.DateLastModified
                        chosen = candidate
                    End If
                End If
            Next
        Next
    End If
End If

If chosen <> "" Then
    shell.Run """" & chosen & """ """ & launcher & """", 0, False
    WScript.Quit 0
End If

' 4) Primer arranque: usa pythonw global oculto; el bootstrap crea el runtime sin consolas auxiliares.
On Error Resume Next
Err.Clear
shell.Run "pyw.exe -3.12 """ & launcher & """", 0, False
If Err.Number = 0 Then WScript.Quit 0
Err.Clear
shell.Run "pythonw.exe """ & launcher & """", 0, False
If Err.Number = 0 Then WScript.Quit 0
On Error GoTo 0

MsgBox "CorePulse no encontró un intérprete Python compatible para preparar el runtime.", vbCritical, "CorePulse"
WScript.Quit 2
