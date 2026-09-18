# Submitting the cdc_usb icon to home-assistant/brands

## Why this is needed

Home Assistant's "Devices & Services" page and the "Add Integration" dialog
never read an icon from this repo or from the integration's own files. They
always fetch it from a single central CDN, `brands.home-assistant.io`, keyed
by the integration's domain (`cdc_usb`). Until that domain has an entry
there, HA shows a generic "icon not available" placeholder — that's what
you're seeing today. There is no local override; getting a real icon means
getting `cdc_usb` added to the `home-assistant/brands` GitHub repo.

## What's already prepared

This folder (`brands-submission/`) contains the two image files the brands
repo wants, already built from `\\192.168.0.104\GCstudio\G+Stools\cowicon.ico`:

| File          | Size    | Notes                                              |
| ------------- | ------- | --------------------------------------------------- |
| `icon.png`    | 256×256 | Required. Transparent background (verified: alpha=0 outside the mark, alpha=255 on it). |
| `icon@2x.png` | 512×512 | Optional but recommended (retina/high-DPI).         |

**Caveat to know before submitting:** the source `.ico` only had a native
64×64 frame — these PNGs are a high-quality upscale of that, not a native
256px asset. It looks clean because the source art is a simple flat
low-poly shape, but if you have (or can get) a genuinely higher-resolution
version of the same cow mark, swap these two files for that before
submitting; it'll hold up better under reviewer/community scrutiny.

## One-time things you need

- A GitHub account (used to fork `home-assistant/brands`).
- Either:
  - **Git for Windows** on this machine (not currently installed — `winget
    install --id Git.Git -e`), **or**
  - Just a browser — GitHub's web UI supports creating a branch, uploading
    files, and opening a PR without any local git at all (steps below cover
    this path since this machine doesn't have git installed).

## Step by step (browser-only, no git required)

1. **Fork the repo.** Go to
   https://github.com/home-assistant/brands and click **Fork** (top right).
   This creates `https://github.com/<your-username>/brands`.

2. **Create a branch for this change.** On your fork, click the branch
   dropdown (says "master") and type a new branch name, e.g.
   `add-cdc_usb-icon`, then confirm creating it from `master`.

3. **Create the folder and upload the files.** Still on your fork, on the
   new branch, navigate into `custom_integrations/` and use **Add file →
   Upload files**. Drag in this folder's `icon.png` and `icon@2x.png`.
   GitHub will create `custom_integrations/cdc_usb/icon.png` and
   `custom_integrations/cdc_usb/icon@2x.png` automatically as long as you
   type `custom_integrations/cdc_usb/` in the "Upload files" path box, or
   navigate into a manually-created `cdc_usb` folder first (use "Create new
   file", type `custom_integrations/cdc_usb/icon.png` as the filename to
   force the folder to exist, then delete that placeholder once the real
   upload is in).

   The domain folder name (`cdc_usb`) **must exactly match** the `domain`
   field in `custom_components/cdc_usb/manifest.json` in this repo — it
   does, so no change needed there.

4. **Commit directly to your branch** (not `master`) with a message like
   `Add cdc_usb icon`.

5. **Open the Pull Request as a Draft.** Go to your fork, you'll see a
   "Compare & pull request" banner for the branch you just pushed — click
   it. Base repo: `home-assistant/brands`, base branch: `master`. Head
   repo: your fork, branch: `add-cdc_usb-icon`. Fill in:

   - **Title:** `Add cdc_usb icon`
   - **Description:**
     ```
     Adds the icon for the `cdc_usb` Home Assistant custom integration
     (https://github.com/GreatCowBASIC/ha-GCBASIC-Temperature_Solution),
     a device driver for a GCBASIC-firmware USB-CDC board (VID:PID
     1209:2008) - temperature/potentiometer sensors, 4 LED switches, and
     command buttons.
     ```
   - Click the dropdown next to "Create pull request" and choose
     **"Create draft pull request"** instead of a regular one. This opens
     it as visibly work-in-progress so you can review the diff yourself
     (and I can too, if you paste me the PR link) before marking it
     "Ready for review", which is the point where the home-assistant/brands
     maintainers actually look at it.

6. **After you're happy with it**, open the PR page and click **"Ready for
   review"**. From there it's in the maintainers' hands — approval isn't
   guaranteed; they've occasionally pushed back on submissions for
   integrations with a very small/no user base beyond the author, so don't
   be surprised if there's back-and-forth.

## Reference: image requirements (for future updates)

From the `home-assistant/brands` repo's own rules, if you ever revisit
this:

- `icon.png` — required, square, PNG, ≥256×256, transparent background.
- `icon@2x.png` — optional, square, PNG, ≥512×512.
- `logo.png` — optional, wider non-square logo variant, max height 256px.
- `dark_icon.png` / `dark_logo.png` — optional dark-theme variants.
- No extra padding baked into the image — the mark should fill most of the
  square frame, same as `icon.png` here already does.
