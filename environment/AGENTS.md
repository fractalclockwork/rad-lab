# Environment

Host vs container boundary, archive downloads, and `sdr_run`. Builds argv; does not invent TX assent (callers use **human**).

## Allowed
- `make image`, `make archive`, `make sdr`.
- Change Dockerfile / container helpers.

## Forbidden
- Keying RF without going through human assent in the caller.
