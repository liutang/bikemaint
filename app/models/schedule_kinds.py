"""The vocabulary of maintenance schedules (specs/040-schedule-types-and-intervals)."""

SERVICE_TYPES = ("Charge", "Check", "Clean", "Lube/Wax", "Replace", "Service", "Topup")
USAGE_UNITS = ("miles", "rides", "hours")
PERIOD_UNITS = ("years", "months", "weeks")
WHOLE_UNITS = ("rides", "years", "months", "weeks")  # these count in whole numbers
UNIT_LABELS = {
    "miles": "Miles", "rides": "Rides", "hours": "Hours",
    "years": "Years", "months": "Months", "weeks": "Weeks",
}
