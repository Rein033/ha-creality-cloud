# Changelog

## 0.3.3 – 2026-10-18

- Card: the toolhead moves again while printing, now on its own layer that the browser only moves (no repaint of the
  drawing). It pauses when the card is off screen and respects "reduce motion".

## 0.3.2 – 2026-10-18

- Card: much lighter. No more endless toolhead animation (it made the browser repaint the whole drawing every frame,
  which froze dashboards on tablets and with blurred themes).
- Cards look up their printer's entities once instead of on every state change in Home Assistant (about 5x less work).

## 0.3.1 – 2026-10-18

- Card picker: a new card now picks an online printer first, and Creality Cloud before other integrations.

## 0.3.0 – 2026-10-18

- Notifications: pick in the integration's options which phones (or other notify services) get a message, and for
  which events (finished, failed, cancelled, paused, started, offline, error). With the print preview as picture.
- Print history: sensor "Last print" with the recent prints as attribute, and a history popup on the card.
- Timelapse: play a print's timelapse in a popup inside Home Assistant (when the printer records one).
- Print again: button "Print last file again", service `creality_cloud.reprint`, and a button per print in the
  history popup. Only when the printer is online and idle, and only files on the printer's own storage.
- Firmware: update entity that shows when Creality has released newer firmware for the printer's hardware.
- New card `custom:creality-print-group-card`: all printers in one compact list, with visual editor.
- Region select menu when adding the integration: International (crealitycloud.com) or China (crealitycloud.cn,
  log in with e-mail or phone number).

## 0.2.0 – 2026-10-18

- Card: drawn printer with the print growing inside it (K1 Max style, and Kobra S1 with the ACE Pro and its spool colours).
  Switch between the drawing and the progress ring on the card.
- Card: slicer info (material, layer height, layers, filament used, slicer estimate, slicer).
- Card: also works with printers of the Anycubic Cloud integration.
- Card: visual editor with options for start view, slicer info, temperatures, buttons and the view switch.
- Job sensor: material, layer height and slicer estimate from the file name as attributes.
- The card now also loads when the frontend starts after the integration.

## 0.1.1 – 2026-10-18

- Own brand icon (`brand/icon.png`), so Home Assistant and HACS show an icon for the integration.

## 0.1.0 – 2026-10-18

First release.

- Log in with a Creality Cloud account (international region); reauth when the password stops working.
- Per printer: status, progress, time remaining, print start and end, job, nozzle / bed / chamber temperature and targets,
  error code, online, printing, LED light, print preview image.
- Buttons for pause, resume and cancel (only available when they make sense).
- Creality Print Card (`custom:creality-print-card`), served by the integration itself.
- Diagnostics with e-mail, password, token, serial numbers and network details removed.
