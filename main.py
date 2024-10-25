import os, urllib, urllib.request, ssl, enum, html, json, subprocess, traceback
from xml.dom import minidom
from loguru import logger

Global = {
    "MaximumRetry": 3, # Maximum retry
    "timeout": 20, # Timeout
    "cookie": None,
    "unverifiedContext": None,
    "getCookieXml": None,
    "wuidRequestXml": None,
    "debug": False
}
""" Global variable """
if Global["debug"]: logger.level("DEBUG")

class ReleaseType(enum.Enum):
    """ release type """
    Release: int = 0
    Beta: int = 1
    Preview: int = 2

def updateGlobalVariable() -> None:
    """ Update the global variable """

    logger.debug("Updating global variable...")

    # update the global getCookieXml variable
    if not Global["getCookieXml"]:
        logger.debug("Updating getCookieXml variable...")
        with open("xml/getCookie.xml", "r", encoding = "utf-8") as file:
            Global["getCookieXml"] = file.read()
        logger.debug("Updated getCookieXml variable.")

    # update the global wuidRequestXml variable
    if not Global["wuidRequestXml"]:
        logger.debug("Updating wuidRequestXml variable...")
        with open("xml/wuidRequest.xml", "r", encoding = "utf-8") as file:
            Global["wuidRequestXml"] = file.read()
        logger.debug("Updated wuidRequestXml variable.")

    # update the global unverifiedContext variable
    if not Global["unverifiedContext"]:
        logger.debug("Updating unverifiedContext variable...")
        Global["unverifiedContext"] = ssl.create_default_context()
        Global["unverifiedContext"].check_hostname = False
        Global["unverifiedContext"].verify_mode = ssl.CERT_NONE
        logger.debug("Updated unverifiedContext variable.")

    # update the global cookie variable
    if not Global["cookie"]:
        logger.debug("Updating cookie variable...")
        Global["cookie"] = os.getenv("COOKIE")
        for count in range(Global["MaximumRetry"] + 1, -1, -1):
            try:
                if Global["cookie"]: break
                if count == 0:
                    logger.error("Cookie acquisition exceeded the maximum number of times and is exiting")
                    exit(1)
                if count < Global["MaximumRetry"]: logger.warning("Failed to obtain the cookie. Trying again...")

                request: urllib.request.Request = urllib.request.Request(
                    "https://fe3.delivery.mp.microsoft.com/ClientWebService/client.asmx",
                    data = Global["getCookieXml"].encode("utf-8"),
                    headers = { "Content-Type": "application/soap+xml; charset=utf-8"}
                )
                output: minidom.Document = minidom.parseString(urllib.request.urlopen(request, context = Global["unverifiedContext"], timeout = Global["timeout"]).read())
                Global["cookie"] = output.getElementsByTagName("EncryptedData")[0].firstChild.nodeValue
            except Exception as error: logger.error(f"Error occurred while obtain cookie variable. Error: {error}")
        logger.debug(f"Updated cookie variable. value: {Global["cookie"]}")

    logger.debug("Updated global variable.")

def getPackageVersionAndArch(packageMoniker: str) -> dict[str, str]:
    """ 
    Returns a dictionary containing the version and architecture of the package. 

    Args:
        packageMoniker (str): The package moniker. For Example: "Microsoft.MinecraftUWP_1.21.4101.0_x86__8wekyb3d8bbwe"
    Returns:
        dict[str, str]: A dictionary containing the version and architecture of the package.   
        For Example: {"version": "1.21.4101.0", "arch": "x86"}
    """
    info: list[str] = packageMoniker.split("_")
    return {
        "version": info[1],
        "arch": info[2]
    }

def getUpdates(categoryId: str) -> str:
    """
    Returns the updates of the specified category.

    Args:
        categoryId (str): The category ID. For Example: "d25480ca-36aa-46e6-b76b-39608d49558c"
    Returns:
        str: The updates of the specified category.
    """
    logger.debug("Getting updates...")
    request: urllib.request.Request = urllib.request.Request(
        "https://fe3.delivery.mp.microsoft.com/ClientWebService/client.asmx",
        data = Global["wuidRequestXml"].format(cookie = Global["cookie"], categoryId = categoryId, releaseType = "Retail").encode("utf-8"),
        headers = {"Content-Type": "application/soap+xml; charset=utf-8"}
    )
    for count in range(Global["MaximumRetry"] + 1, -1, -1):
        if count == 0: raise Exception("getUpdates failed.")
        if count < Global["MaximumRetry"]: logger.warning("getUpdates failed. Retrying...")
        try: return html.unescape(urllib.request.urlopen(request, context = Global["unverifiedContext"], timeout = Global["timeout"]).read().decode("utf-8"))
        except Exception as error: logger.error(f"Error occurred while getting updates. Error:{error}")
    raise Exception("getUpdates failed.")

def getUpdateIdentityByCategoryId(categoryId: str) -> list[dict[str, str]]:
    """
    Returns a list of dictionaries containing the update ID and package moniker of the updates in the specified category.

    Args:
        categoryId (str): The category ID. For Example: "d25480ca-36aa-46e6-b76b-39608d49558c"
    Returns:
        list[dict[str, str]]: A list of dictionaries containing the update ID and package moniker of the updates in the specified category.   
        for Example: [{"updateId": "4b95a4cd-d471-45c8-bd01-9cd448dfda94", "packageMoniker": "Microsoft.MinecraftUWP_1.21.4101.0_x86__8wekyb3d8bbwe", "id": "307700497"}]
    """
    logger.debug("Getting update identity by category ID...")
    result: list[dict[str, str]] = []
    for node in minidom.parseString(getUpdates(categoryId)).getElementsByTagName("SecuredFragment"):
        xml = node.parentNode.parentNode
        result.append({
            "updateId": xml.firstChild.attributes["UpdateID"].nodeValue,
            "packageMoniker": xml.getElementsByTagName("AppxMetadata")[0].attributes["PackageMoniker"].nodeValue,
            "id": xml.parentNode.firstChild.firstChild.nodeValue
        })
    return result

def getCurrentVersionInfo(packageFamilyName: str, categoryId: str) -> list[dict[str, str]]:
    """
    Returns a list of dictionaries containing the current version and architecture of the specified package.

    Args:
        packageFamilyName (str): The package family name. For Example: "Microsoft.MinecraftUWP_8wekyb3d8bbwe"
        categoryId (str): The category ID. For Example: "d25480ca-36aa-46e6-b76b-39608d49558c"
    Returns:
        list[dict[str, str]]: A list of dictionaries containing the current version and architecture of the specified package.   
        for Example: [{"updateId": "4b95a4cd-d471-45c8-bd01-9cd448dfda94", "packageMoniker": "Microsoft.MinecraftUWP_1.21.4101.0_x86__8wekyb3d8bbwe", "id": "307700497", "version": "1.21.4101.0", "arch": "x86"}]
    """
    logger.debug("Getting current version info...")
    packageFamilyName: str = packageFamilyName[:packageFamilyName.rfind("_")]
    versions: list[dict[str, str]] = []
    for update in getUpdateIdentityByCategoryId(categoryId):
        if packageFamilyName in update["packageMoniker"]:
            versions.append({**update, **getPackageVersionAndArch(update["packageMoniker"])})
    logger.debug("Got current version info.")
    return versions

def appVersionToStr(version: str, withFifth: bool = False) -> str:
    """
    Convert version string format

    Args:
        version (str): The version string. For Example: "1.21.4101.0"
        withFifth (bool): Whether to include the fifth digit in the version string.
    Returns:
        str: The version string in the format "1.21.41.1"
    """
    arr = version.split(".")
    if (n := 4 - len(arr[2])) > 0: arr[2] = ("0" * n) + arr[2]
    return f"{arr[0]}.{arr[1]}.{arr[2][:-2]}.{arr[2][-2:]}" + ("." + arr[3] if withFifth else "")

def checkForUpdate(packageFamilyName: str, categoryId: str, releaseType: ReleaseType) -> None:
    """
    Checks for updates for the specified package and prints the current version and architecture of the specified package.

    Args:
        packageFamilyName (str): The package family name. For Example: "Microsoft.MinecraftUWP_8wekyb3d8bbwe"
        categoryId (str): The category ID. For Example: "d25480ca-36aa-46e6-b76b-39608d49558c"
        releaseType (ReleaseType): The release type. For Example: ReleaseType.Release
    """
    try:
        logger.debug(f"Checking for {packageFamilyName} updates...")
        with open("versions.json.min", "r", encoding="utf-8") as file: versions = json.load(file)
        newVersion: bool = True
        gameVersion: str | None = None
        identityName: str = packageFamilyName[:packageFamilyName.rfind("_")]
        updateTxt: str = ""

        for info in getCurrentVersionInfo(packageFamilyName, categoryId):
            if identityName not in info["packageMoniker"]: continue
            updateTxt += f"{info["updateId"]} {info["packageMoniker"]} {info["id"]}\n"
            match info["arch"]:
                case "x64":
                    gameVersion: str = appVersionToStr(info["version"])
                    for version in versions:
                        if ReleaseType(version[2]) == releaseType and version[0] == gameVersion:
                            newVersion: bool = False
                            break
                    if newVersion: versions.append([gameVersion, info["updateId"], releaseType.value])
                case _: pass
        
        if newVersion and gameVersion:
            logger.info(f"New version found for {identityName}: {gameVersion}")
            commitMsg: str = "Minecraft " + gameVersion
            if releaseType == ReleaseType.Preview: commitMsg += " (Preview)"
        
            with open("versions.json.min", "w", encoding="utf-8") as file: json.dump(versions, file, ensure_ascii=False)
            with open("versions.txt", "r") as file:
                verTxt: str = file.read()
                start: int = verTxt.find("\n\n", verTxt.find(releaseType.name)) + 1
                file.close()
                with open("versions.txt", "w", encoding="utf-8") as wf: wf.write(verTxt[:start] + updateTxt + verTxt[start:])

            subprocess.run(["git", "add", "versions.json.min", "versions.txt"])
            subprocess.run(["git", "-c", "user.name='github-actions[bot]'", "-c", "user.email='github-actions[bot]@users.noreply.github.com'", "commit", "-m", commitMsg])
            subprocess.run(["git", "push", "origin"])

            if os.getenv("ENABLE_NOTIFICATION"):
                try:
                    import notification
                    cp = subprocess.run(["git", "rev-parse", "HEAD"], stdout = subprocess.PIPE)
                    commitId = cp.stdout.decode("utf-8").strip()
                    notification.pushNotification(packageFamilyName, gameVersion, releaseType, commitId)
                except:
                    logger.error("Failed to push notification.")
                    traceback.print_exc()
        else: logger.info(f"{identityName} is up to date.")
        logger.debug(f"Checked for {packageFamilyName} updates.")
    except Exception as error: logger.error(f"Error occurred while checking for {packageFamilyName} updates. Error: {error}")

if __name__ == "__main__":
    updateGlobalVariable()
    logger.info("-" * 100)
    checkForUpdate("Microsoft.MinecraftUWP_8wekyb3d8bbwe", "d25480ca-36aa-46e6-b76b-39608d49558c", ReleaseType.Release)
    logger.info("-" * 100)
    checkForUpdate("Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe", "188f32fc-5eaa-45a8-9f78-7dde4322d131", ReleaseType.Preview)
    logger.info("-" * 100)