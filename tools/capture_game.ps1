param([int]$GameProcessId, [string]$OutputPath = '.runtime/game.png', [switch]$ClientOnly)
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class GodEyeWindowCapture {
    [StructLayout(LayoutKind.Sequential)]
    public struct Rect { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)]
    public struct Point { public int X, Y; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out Rect r);
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out Rect r);
    [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref Point p);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
}
'@
$gameProcess = Get-Process -Id $GameProcessId -ErrorAction Stop
if ($gameProcess.ProcessName -ne 'Minecraft.Windows') { throw 'Expected Minecraft.Windows process' }
$rectangle = New-Object GodEyeWindowCapture+Rect
if (-not [GodEyeWindowCapture]::GetWindowRect($gameProcess.MainWindowHandle, [ref]$rectangle)) { throw 'Window not found' }
$width = $rectangle.Right - $rectangle.Left
$height = $rectangle.Bottom - $rectangle.Top
$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$dc = $graphics.GetHdc()
try { $captured = [GodEyeWindowCapture]::PrintWindow($gameProcess.MainWindowHandle, $dc, 2) }
finally { $graphics.ReleaseHdc($dc) }
if (-not $captured) { throw 'Capture failed' }
$resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath))
if ($ClientOnly) {
    $clientRect = New-Object GodEyeWindowCapture+Rect
    $clientOrigin = New-Object GodEyeWindowCapture+Point
    if (-not [GodEyeWindowCapture]::GetClientRect($gameProcess.MainWindowHandle, [ref]$clientRect)) { throw 'Client rect unavailable' }
    if (-not [GodEyeWindowCapture]::ClientToScreen($gameProcess.MainWindowHandle, [ref]$clientOrigin)) { throw 'Client origin unavailable' }
    $cropRect = New-Object System.Drawing.Rectangle(($clientOrigin.X - $rectangle.Left), ($clientOrigin.Y - $rectangle.Top), $clientRect.Right, $clientRect.Bottom)
    $cropped = $bitmap.Clone($cropRect, $bitmap.PixelFormat)
    try { $cropped.Save($resolvedOutput, [System.Drawing.Imaging.ImageFormat]::Png) }
    finally { $cropped.Dispose() }
} else {
    $bitmap.Save($resolvedOutput, [System.Drawing.Imaging.ImageFormat]::Png)
}
$graphics.Dispose()
$bitmap.Dispose()
Write-Output $resolvedOutput
