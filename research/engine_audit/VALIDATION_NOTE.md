# Validation note

The source-derived strategy modules were independently ported rather than copied verbatim because upstream licensing was not established for every source. Missing taker-flow values follow the source behavior and fall back to neutral 0.5. The validation workflow compiles the modules and runs the existing regression suite plus the audit-specific unit tests.


Latest GitHub Actions validation passed on the audit branch after the CSV runner and price-action module repairs. The validated workflow compiles all audit modules and runner and executes the complete research regression suite, including audit-specific engine and CSV-ingestion tests. This validates code syntax/regressions only; it does not validate profitability or complete the 100-mechanism audit.


The latest specialist-engine tests cover round-level bounce, wall-pull event-edge behavior, rolling book imbalance warm-up/sign and point-in-time pair alignment. These are implementation regression tests, not evidence of predictive edge.
