# Changelog

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
