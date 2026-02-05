Param(
    [string]$SummaryFile = "d:\Codex Projects\AI-trading\CodexTest\latest_summary.txt",
    [string]$Title = "ATGL Paper Trading"
)

if (-not (Test-Path $SummaryFile)) {
    exit 0
}

$Body = Get-Content -Raw -Path $SummaryFile

# Simple toast notification without external modules
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$toastXml = $template
$toastTextElements = $toastXml.GetElementsByTagName("text")
$toastTextElements.Item(0).AppendChild($toastXml.CreateTextNode($Title)) | Out-Null
$toastTextElements.Item(1).AppendChild($toastXml.CreateTextNode($Body)) | Out-Null

$toast = [Windows.UI.Notifications.ToastNotification]::new($toastXml)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("ATGL Paper Trading")
$notifier.Show($toast)
