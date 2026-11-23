# Redmi / Xiaomi — Boot Loop: Field Notes

Original troubleshooting notes for Redmi phones stuck restarting at the
logo. Software recovery usually takes 20 to 60 minutes depending on
whether user data must be preserved.

## Common causes

- A corrupted system update can cause a boot loop right after installation.
- A faulty power button stuck in the pressed position restarts the phone endlessly.
- A dead or swollen battery drops voltage under load and the phone restarts.
- Damaged storage or a corrupted data partition prevents Android from finishing boot.

## Diagnostic procedure

1. Charge the phone for 30 minutes; low voltage alone can mimic a boot loop.
2. Check the power button feel; a stuck button clicks without travel.
3. Boot into recovery with Volume Up plus Power and wipe the cache partition.
4. If cache wipe fails, back up data if recovery allows, then factory reset.
5. Flash the official firmware with the vendor tool if reset does not help.
6. Open the device and test with a known-good battery if flashing fails.
7. Replace the battery if voltage collapses under load.

## Tools

- USB cable and computer
- Screwdriver set
- Spudger
- Multimeter
- Replacement battery

## Warnings

- Warning: a factory reset erases user data; warn the customer before resetting.
- Do not interrupt firmware flashing; a dead battery mid-flash can brick the phone.
- Avoid heating a swollen battery with a heat gun.
- Unlocking the bootloader may void the manufacturer warranty.
