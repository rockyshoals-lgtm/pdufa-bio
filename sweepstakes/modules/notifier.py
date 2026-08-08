"""
notifier.py — Windows desktop toast notifications
Tries win10toast first, falls back to PowerShell WinRT toast.
"""
import subprocess
import logging

logger = logging.getLogger(__name__)


def _powershell_toast(title: str, body: str):
    body_safe  = body.replace("'", "''").replace('"', '`"')[:200]
    title_safe = title.replace("'", "''").replace('"', '`"')[:60]
    script = f"""
$app = 'SweepRunner'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] | Out-Null
$template = @"
<toast>
  <visual>
    <binding template='ToastGeneric'>
      <text>{title_safe}</text>
      <text>{body_safe}</text>
    </binding>
  </visual>
</toast>
"@
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show($toast)
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, timeout=10
    )
    return result.returncode == 0


def notify(title: str, body: str) -> bool:
    """Send a Windows desktop notification. Returns True if successful."""
    # Try win10toast
    try:
        from win10toast import ToastNotifier
        tn = ToastNotifier()
        tn.show_toast(title, body, duration=8, threaded=True)
        return True
    except Exception:
        pass

    # Try plyer
    try:
        from plyer import notification
        notification.notify(title=title, message=body, app_name="SweepRunner", timeout=8)
        return True
    except Exception:
        pass

    # PowerShell WinRT fallback
    try:
        return _powershell_toast(title, body)
    except Exception as e:
        logger.warning(f"All notification methods failed: {e}")
        return False


def notify_opportunities(opps: list):
    """Send a notification summarising today's top opportunities."""
    if not opps:
        return
    top = opps[0]
    extra = f" (+{len(opps)-1} more)" if len(opps) > 1 else ""
    notify(
        f"🌟 SweepRunner: {len(opps)} Opportunity{'s' if len(opps)>1 else ''} Today",
        f"{top['name']} — {top['summary']}{extra}"
    )
