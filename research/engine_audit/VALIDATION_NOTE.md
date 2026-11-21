# Validation note

The source-derived strategy modules were independently ported rather than copied verbatim because upstream licensing was not established for every source. Missing taker-flow values follow the source behavior and fall back to neutral 0.5. The validation workflow compiles the modules and runs the existing regression suite plus the audit-specific unit tests.
