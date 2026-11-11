# Quickstart: Bike Catalog and Interactive Builder

1. `docker build -t bikemaint:<milestone-tag> . && docker rm -f bikemaint; docker run -d --name bikemaint -p 8000:8000 -v bikemaint-data:/data -e SESSION_SECRET_KEY=local-test-secret -e STRAVA_CLIENT_ID=0 -e STRAVA_CLIENT_SECRET=0 bikemaint:<milestone-tag>`
2. **M1**: Add a bike: pick "Trek Domane"; add it again and see "Trek Domane (2)"; no free text; edit a pre-existing bike and see "Keep current".
3. **M2**: Try to add a pedal under a wheel (Add component with a parent): refused with "A pedal can be mounted on a crankset…"; add a tire on a rim: accepted.
4. **M3**: Open a bike's Build page; drag Frame from the palette onto the bike, a Wheel, a Rim onto the wheel, a Tire onto the rim; only valid targets highlight; drop a pedal on a wheel: message; re-order siblings; reload and confirm; repeat using only the Move to… selects with the keyboard.
5. `.venv/bin/python -m pytest -q` is green.
