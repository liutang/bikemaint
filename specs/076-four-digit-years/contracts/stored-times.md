# Contract change: Stored Times (amends 075's contracts/stored-times.md)

## Storage (amended)

- Every instant is UTC text `YYYY-MM-DDTHH:MM:SS.ffffffZ`, and `YYYY` is always four digits, zero-padded, on every platform.
- A typed year from 0 to 99 means 2000 to 2099. A typed year from 100 to 1899 is refused with "Enter a valid date".
- Stored values with a year below 100 are repaired once (data step `0020_four_digit_years`) and on every restore. See [../data-model.md](../data-model.md).

## Rides (amended)

- A ride added or edited by hand can't be dated in the future: a date after today in the saved zone, or today with a typed time later than now, is refused with "The ride date cannot be in the future."
- A ride for today with no time is allowed and is stored as noon, as before.

The rest of 075's contract is unchanged.
