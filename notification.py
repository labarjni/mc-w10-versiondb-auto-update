import urllib.request
import os

def pushNotification(pfn, gameVer, releaseType, commitId):
    # ntfy.sh
    if (token := os.getenv("NTFY_TOKEN")) is not None:
        msg = "Minecraft "
        if releaseType == 2:
            msg += "Preview "
        msg += gameVer

        serverUrl = os.getenv("GITHUB_SERVER_URL", "https://github.com")
        repository = os.getenv("GITHUB_REPOSITORY", "ddf8196/mc-w10-versiondb-auto-update")

        request = urllib.request.Request("https://ntfy.projectxero.top/mc-w10-versiondb-auto-update",
            data=msg.encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Title": "New version detected",
                "Click": f"{serverUrl}/{repository}/commit/{commitId}"
            }
        )
        urllib.request.urlopen(request, timeout=20)