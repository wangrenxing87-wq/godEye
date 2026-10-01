param([int]$GameProcessId, [ValidateSet('click','drag','key','text')][string]$Action,
      [int]$X = 0, [int]$Y = 0, [int]$Key = 0, [string]$Text = '',
      [int]$EndX = 0, [int]$EndY = 0)
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class GodEyeGameInput {
    [StructLayout(LayoutKind.Sequential)] public struct Point { public int X, Y; }
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref Point p);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint data, UIntPtr e);
    [DllImport("user32.dll")] public static extern void keybd_event(byte key, byte scan, uint flags, UIntPtr extra);
    [DllImport("user32.dll", EntryPoint="PostMessageW")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
}
'@
$gameProcess = Get-Process -Id $GameProcessId -ErrorAction Stop
if ($gameProcess.ProcessName -ne 'Minecraft.Windows') { throw 'Expected test game process' }
$window = $gameProcess.MainWindowHandle
[void][GodEyeGameInput]::SetForegroundWindow($window)
Start-Sleep -Milliseconds 150
if ($Action -in @('click', 'drag')) {
    $point = New-Object GodEyeGameInput+Point
    $point.X = $X; $point.Y = $Y
    [void][GodEyeGameInput]::ClientToScreen($window, [ref]$point)
    [void][GodEyeGameInput]::SetCursorPos($point.X, $point.Y)
    [GodEyeGameInput]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    if ($Action -eq 'drag') {
        for ($step = 1; $step -le 20; $step++) {
            $next = New-Object GodEyeGameInput+Point
            $next.X = [int]($X + ($EndX - $X) * $step / 20)
            $next.Y = [int]($Y + ($EndY - $Y) * $step / 20)
            [void][GodEyeGameInput]::ClientToScreen($window, [ref]$next)
            [void][GodEyeGameInput]::SetCursorPos($next.X, $next.Y)
            Start-Sleep -Milliseconds 30
        }
    }
    [GodEyeGameInput]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
} elseif ($Action -eq 'key') {
    [GodEyeGameInput]::keybd_event([byte]$Key, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [GodEyeGameInput]::keybd_event([byte]$Key, 0, 2, [UIntPtr]::Zero)
} else {
    foreach ($character in $Text.ToCharArray()) {
        [void][GodEyeGameInput]::PostMessage($window, 0x0102, [IntPtr][int]$character, [IntPtr]::Zero)
    }
}
