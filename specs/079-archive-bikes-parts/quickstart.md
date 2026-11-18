# Quickstart: 079 Archive Bikes and Parts

## Prerequisites

The app runs locally (see `CLAUDE.md`), signed in. Set up:
- a bike paired with Strava, with two schedules, a wheel with a tire inside, and rides;
- a part in storage with a schedule.

## US1: archive a bike

1. Edit the bike. The Archive card spans below Strava and Delete, and lists 2 schedules and the part count.
2. Press Archive bike without choosing: the form asks for a choice.
3. Choose "Move the parts to storage" and archive.
   - The Garage shows the bike only under a closed "Archived (1)".
   - Maintenance due no longer shows its two schedules.
   - The wheel is in Storage with the tire inside, both keeping their schedules.
   - The bike is unpaired.
4. Open its Rides: no Add, Edit or Delete. Posting to `/rides/{id}` directly answers 409 and changes nothing.

## US2: take parts off

5. Archive a second bike with "Keep the parts on the bike". Drag its wheel to storage: the wheel arrives with the tire inside, removed now.
6. On that bike's Install History, a still-installed row's Edit offers only removal fields. Back-date a removal: the part moves to storage at that moment.

## US3: archive a part

7. Edit the stored part and archive it. It's under Storage's closed "Archived (1)", and it isn't offered in the builder's storage list or the Inside part list.
8. Edit an installed part: the Archive card says to take it off first.

## US4: unarchive

9. On the archived bike's Edit screen, press Unarchive bike. It's back with the active bikes and editable, with no schedules and not paired. Pairing again imports its full history.

## Checks

10. `.venv/bin/python -m pytest -q` passes, including the route walk that fails for any unguarded POST.
