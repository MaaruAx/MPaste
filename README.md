<div align="center">

<br>

# ◈𝐌𝐏𝐀𝐒𝐓𝐄

[![Version](https://img.shields.io/badge/Version-v2.4.0-c4a7e7?style=for-the-badge&labelColor=1a1a2e)](https://github.com/MaaruAX/MCopy/releases)
[![Status](https://img.shields.io/badge/Status-Stable-c4a7e7?style=for-the-badge&labelColor=1a1a2e)](https://github.com/MaaruAX/MCopy)
![free](https://img.shields.io/badge/Works_on_FREE_Resolve-1a1a2e?style=for-the-badge&labelColor=1a1a2e)

<br>

**Paste images into DaVinci Resolve from your browser. No downloads required.**

*Find it on the web. Copy it. Paste it straight into your timeline.*

<br>

![Windows](https://img.shields.io/badge/Windows-9ccfd8?style=flat-square&logo=windows&logoColor=1a1a2e)
&nbsp;
![macOS](https://img.shields.io/badge/macOS-ebbcba?style=flat-square&logo=apple&logoColor=1a1a2e)
&nbsp;
![Linux](https://img.shields.io/badge/Linux-f6c177?style=flat-square&logo=linux&logoColor=1a1a2e)
&nbsp;
![Python](https://img.shields.io/badge/Python_3.9+-c4a7e7?style=flat-square&logo=python&logoColor=1a1a2e)
&nbsp;
![Resolve](https://img.shields.io/badge/Resolve_Studio-eb6f92?style=flat-square&logoColor=1a1a2e)

<br>

</div>

---

![what](https://img.shields.io/badge/◈_WHAT_IS_MPASTE-eb6f92?style=flat-square&labelColor=1a1a2e)

The usual workflow for getting an image into Resolve is painful: find the image online → save to disk → import to Media Pool → add to timeline. **MPaste cuts that down to two steps: copy from the browser, click Paste.**

It also works the other way — the **Copy** button grabs the current frame at your playhead and sends it to your clipboard, ready to paste anywhere.

<table>
<tr>
<td>

![paste](https://img.shields.io/badge/PASTE-c4a7e7?style=flat-square&labelColor=26233a)

```
Browser → right-click an image → Copy Image
Switch to MPaste → click Paste
Done. It's in your Media Pool and on the timeline.
```

</td>
<td>

![copy](https://img.shields.io/badge/COPY-9ccfd8?style=flat-square&labelColor=26233a)

```
Move your playhead to any frame
Click Copy in MPaste
The frame lands in your clipboard
Paste anywhere — Photoshop, Figma, Discord
```

</td>
</tr>
</table>

---

![features](https://img.shields.io/badge/◈_FEATURES_&_MODES-f6c177?style=flat-square&labelColor=1a1a2e)

![accent](https://img.shields.io/badge/Accent_Colors-9ccfd8?style=flat-square&labelColor=26233a) &nbsp;Seven color options to match your setup.

![theme](https://img.shields.io/badge/Dynamic_Themes-f6c177?style=flat-square&labelColor=26233a) &nbsp;Dark, AMOLED, and Dim variants.

![aot](https://img.shields.io/badge/Always_on_Top-eb6f92?style=flat-square&labelColor=26233a) &nbsp;Toggle window behavior for seamless multitasking.

![lang](https://img.shields.io/badge/Multi_Language-c4a7e7?style=flat-square&labelColor=26233a) &nbsp;English, Español, Hindi, Hinglish support.

---

![install](https://img.shields.io/badge/◈_INSTALLATION-c4a7e7?style=flat-square&labelColor=1a1a2e)

**Option A — Standalone installer (Windows)**

Download `MPaste-Setup.exe` from the [Releases page](https://codeberg.org/MaaruAx/MPaste/releases). No Python required.

**Option B — Python**

```bash
python install.py
```

On first launch, it will install dependencies (`Pillow`, `pywebview`, `pywin32`) and place the launcher in your Resolve Scripts folder. From then on, open via: `Workspace → Scripts → MPaste`.

<details>
<summary>

![troubleshoot](https://img.shields.io/badge/◈_TROUBLESHOOTING-f6c177?style=flat-square&labelColor=1a1a2e)

</summary>

<br>

If auto-install fails, run these in an admin CMD:
`pip install Pillow pywebview pywin32`

Ensure **Microsoft Edge WebView2 Runtime** is installed: [aka.ms/webview2](https://aka.ms/webview2)

<br>

</details>

---

![req](https://img.shields.io/badge/◈_REQUIREMENTS-ebbcba?style=flat-square&labelColor=1a1a2e)

| | |
|---|---|
| ![os](https://img.shields.io/badge/Windows_10_/_11-eb6f92?style=flat-square&labelColor=26233a) | Supported OS versions |
| ![resolve](https://img.shields.io/badge/Resolve_Studio-c4a7e7?style=flat-square&labelColor=26233a) | Scripting API access required |
| ![python](https://img.shields.io/badge/Python_3.9+-9ccfd8?style=flat-square&labelColor=26233a) | Official installer (python.org) |

> ⚠️ **Python from the Microsoft Store will not work.** It is a restricted stub that cannot load the DaVinci Resolve scripting modules. Download the standard installer from **[python.org/downloads](https://python.org/downloads)** and check *"Add Python to PATH"* during setup.
---

<div align="center">

<br>

![oss](https://img.shields.io/badge/Free_&_Open_Source-26233a?style=for-the-badge)
&nbsp;
[![discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/dvZ9nvN79Y)
&nbsp;
[![releases](https://img.shields.io/badge/Releases-eb6f92?style=for-the-badge)](https://codeberg.org/MaaruAx/MFlow/releases)

<br>
<sub>Part of the MMarket ecosystem • Created with love for the DaVinci Resolve community.</sub>
<br><br>

</div>