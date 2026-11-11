# Quickstart: Unified Bike Screen and Simpler Parts

1. Build and run the image (see README "Running in Docker").
2. Add a bike: type Year, Make, Model, pick a Category; confirm the name "Year Make Model".
3. Open the bike: one screen with breadcrumb, actions, tree, storage, palette; no Build/Add component buttons.
4. Drag Frame, Wheel, Tire onto the bike; click Wheel to drill in: breadcrumb Garage > bike > Wheel, its own actions, no Pair with Strava.
5. Use the Garage and Trash buttons on a part; trash a part with history to see the in-place confirmation.
6. `.venv/bin/python -m pytest -q` is green.
