<div align="center">

<br>

# ◈ MPaste

![early-access](https://img.shields.io/badge/⚠_EARLY_ACCESS-ff6b6b?style=for-the-badge&labelColor=1a1a2e)
&nbsp;
![version](https://img.shields.io/badge/version-1.0-f5c842?style=for-the-badge&labelColor=1a1a2e)
&nbsp;
![studio](https://img.shields.io/badge/Requires_Resolve_Studio-f5c842?style=for-the-badge&labelColor=1a1a2e)

<br>

**Paste images into DaVinci Resolve from your browser. No downloads required.**

*Find it on the web. Copy it. Paste it straight into your timeline.*

<br>

![Windows](https://img.shields.io/badge/Windows-f5c842?style=flat-square&logo=windows&logoColor=1a1a2e)
&nbsp;
![Python](https://img.shields.io/badge/Python_3.9+-f5c842?style=flat-square&logo=python&logoColor=1a1a2e)
&nbsp;
![Resolve](https://img.shields.io/badge/DaVinci_Resolve_Studio-f5c842?style=flat-square&logoColor=1a1a2e)

<br>

[![downloads](https://img.shields.io/gitea/downloads/release/USER/mpaste?gitea_url=https%3A%2F%2Fcodeberg.org&style=flat-square&label=downloads&color=f5c842&labelColor=1a1a2e)](https://codeberg.org/USER/mpaste/releases)
&nbsp;
[![stars](https://img.shields.io/gitea/stars/USER/mpaste?gitea_url=https%3A%2F%2Fcodeberg.org&style=flat-square&label=stars&color=f5c842&labelColor=1a1a2e)](https://codeberg.org/USER/mpaste)
&nbsp;
[![issues](https://img.shields.io/gitea/issues/open/USER/mpaste?gitea_url=https%3A%2F%2Fcodeberg.org&style=flat-square&label=open%20issues&color=333&labelColor=1a1a2e)](https://codeberg.org/USER/mpaste/issues)
&nbsp;
[![last commit](https://img.shields.io/gitea/last-commit/USER/mpaste?gitea_url=https%3A%2F%2Fcodeberg.org&style=flat-square&label=last%20commit&color=555&labelColor=1a1a2e)](https://codeberg.org/USER/mpaste/commits/branch/main)

<br>

> ⚠️ **Early access release.** Bugs are expected and features are actively being added. Your feedback directly shapes what gets built next — see how to reach us below.

<br>

</div>

---

## ![what](https://img.shields.io/badge/◈_WHAT_IS_MPASTE-f5c842?style=flat-square&labelColor=1a1a2e)

The usual workflow for getting an image into Resolve is painful: find the image online → save to disk → import to Media Pool → add to timeline. **MPaste cuts that down to two steps: copy from the browser, click Paste.**

It also works the other way — the **Copy** button grabs the current frame at your playhead and sends it to your clipboard, ready to paste anywhere.

<table>
<tr>
<td>

![paste](https://img.shields.io/badge/PASTE-f5c842?style=flat-square&labelColor=26233a)

```
Browser → right-click an image → Copy Image
Switch to MPaste → click Paste
Done. It's in your Media Pool and on the timeline.
```

</td>
<td>

![copy](https://img.shields.io/badge/COPY-555?style=flat-square&labelColor=26233a)

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

## ![how](https://img.shields.io/badge/◈_HOW_IT_WORKS-f5c842?style=flat-square&labelColor=1a1a2e)

**Paste flow** — MPaste reads whatever is in your clipboard (bitmap, PNG, JPG, even SVG if CairoSVG is installed), saves it as a PNG, imports it into Resolve's Media Pool through the scripting API, and inserts it at the position of your playhead.

**Copy flow** — MPaste switches Resolve to the Color page, grabs a still at the current frame, exports it as PNG, copies it to the clipboard as a bitmap, and switches back to your original page. Automatically.

> The image is placed at the **exact frame where your playhead is**. If that position is occupied, it falls back to appending at the end of the timeline.

---

## ![settings](https://img.shields.io/badge/◈_SETTINGS-f5c842?style=flat-square&labelColor=1a1a2e)

![accent](https://img.shields.io/badge/Accent_color-f5c842?style=flat-square&labelColor=26233a) &nbsp;Seven color options to match your setup.

![theme](https://img.shields.io/badge/Theme-555?style=flat-square&labelColor=26233a) &nbsp;Dark, AMOLED, and Dim variants.

![aot](https://img.shields.io/badge/Always_on_Top-f5c842?style=flat-square&labelColor=26233a) &nbsp;Toggle whether MPaste floats above all other windows. Useful when working across browser and Resolve side by side. Takes effect immediately — no restart needed.

![lang](https://img.shields.io/badge/Language-555?style=flat-square&labelColor=26233a) &nbsp;English, Español, Hindi, Hinglish.

---

## ![install](https://img.shields.io/badge/◈_INSTALLATION-f5c842?style=flat-square&labelColor=1a1a2e)

MPaste installs itself on first run. Just double-click `main.py` or run:

```bash
python main.py
```

On first launch it will:
- Install required dependencies automatically (`Pillow`, `pywebview`, `pywin32`)
- Place the Resolve launcher script in the right folder

From then on, open MPaste directly from DaVinci Resolve:

```
Workspace → Scripts → MPaste
```

<details>
<summary>

![manual](https://img.shields.io/badge/Troubleshooting_/_manual_setup-555?style=flat-square&labelColor=26233a)

</summary>

<br>

If the automatic install fails, install dependencies manually from an admin CMD:

```bash
pip install Pillow pywebview pywin32
```

MPaste also requires **Microsoft Edge WebView2 Runtime** for the UI (usually already present on Windows 10/11):

```
https://aka.ms/webview2
```

<br>

> **Still stuck? Join the Discord.** Since this is an early access release, many issues are already known and solved there. Post your error message, your Windows version, and your Python version.

[![discord](https://img.shields.io/badge/Join_the_Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/YOURLINK)

<br>

</details>

---

## ![req](https://img.shields.io/badge/◈_REQUIREMENTS-f5c842?style=flat-square&labelColor=1a1a2e)

| | |
|---|---|
| ![os](https://img.shields.io/badge/Windows_10_/_11-f5c842?style=flat-square&labelColor=26233a) | Only Windows is supported at this time |
| ![resolve](https://img.shields.io/badge/DaVinci_Resolve_Studio-f5c842?style=flat-square&labelColor=26233a) | **Studio license required** — the scripting API used by MPaste is not available in the free version |
| ![python](https://img.shields.io/badge/Python_3.9+-f5c842?style=flat-square&labelColor=26233a) | **Must be the `.exe` installer from [python.org](https://python.org/downloads)** |
| ![webview2](https://img.shields.io/badge/WebView2_Runtime-555?style=flat-square&labelColor=26233a) | Pre-installed on most Windows systems — [download here](https://aka.ms/webview2) if missing |

> ⚠️ **Python from the Microsoft Store will not work.** Download the standard installer from **[python.org/downloads](https://python.org/downloads)** and check *"Add Python to PATH"* during setup.

---

## ![opt](https://img.shields.io/badge/◈_OPTIONAL-555?style=flat-square&labelColor=1a1a2e)

![cairo](https://img.shields.io/badge/CairoSVG-f5c842?style=flat-square&labelColor=26233a) &nbsp;Install `cairosvg` to enable SVG support — paste vector graphics directly from the web and they get converted to PNG automatically.

```bash
pip install cairosvg
```

---

<div align="center">

<br>

![oss](https://img.shields.io/badge/Free_&_Open_Source-1a1a2e?style=for-the-badge)
&nbsp;
[![discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/YOURLINK)
&nbsp;
[![releases](https://img.shields.io/badge/Releases-f5c842?style=for-the-badge&labelColor=1a1a2e)](https://codeberg.org/USER/mpaste/releases)

<br>
<sub>Part of the MMarket ecosystem. Built for the DaVinci Resolve community.</sub>
<br><br>

</div>

