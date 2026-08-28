## ADDED Requirements

### Requirement: legacy env deprecation warning is emitted at most once per process

`paulsha_cortex.monitor.config._resolve_config_source()` MUST emit the `PAULSHACLAW_CONFIG` deprecation warning at most once per process lifetime, and that warning MUST use the legacy key `legacy-monitor-env`.

#### Scenario: legacy env deprecation warning dedupe

- **GIVEN** the process has `PAULSHACLAW_CONFIG` set and no `PSC_MONITOR_CONFIG`
- **WHEN** `_resolve_config_source(None)` is called three times
- **THEN** exactly one warning MUST be emitted
- **AND** the warning message MUST exactly match `PAULSHACLAW_CONFIG 已 deprecated，改用 project-cortex.yaml`
- **AND** `_resolve_config_source(None)` MUST return the same path all three times

### Requirement: legacy file deprecation warning is emitted at most once per process

`paulsha_cortex.monitor.config._resolve_config_source()` MUST emit the legacy file deprecation warning at most once per process lifetime, and that warning MUST use the legacy key `legacy-monitor-file`.

#### Scenario: legacy file deprecation warning dedupe

- **GIVEN** no `PSC_MONITOR_CONFIG` and no `PAULSHACLAW_CONFIG`
- **AND** `project-cortex.yaml` does not exist while `paulshaclaw.yaml` exists
- **WHEN** `_resolve_config_source(None)` is called three times
- **THEN** exactly one warning MUST be emitted
- **AND** the warning message MUST match the existing phrasing
- **AND** `_resolve_config_source(None)` MUST return the same legacy path all three times

### Requirement: legacy warning behavior does not change message, precedence, or stacklevel contract

For non-deprecated paths, including when `project-cortex.yaml` exists, `_resolve_config_source()` MUST preserve existing precedence and message content, and deprecated warning stacklevel behavior MUST remain equivalent to the prior contract.

#### Scenario: new config path and warning attribution

- **GIVEN** `project-cortex.yaml` exists and legacy env/file are absent
- **WHEN** `_resolve_config_source(None)` is called three times
- **THEN** no deprecated warning MUST be emitted
- **AND** precedence and resolved path MUST remain unchanged
- **AND** deprecated warning attribution MUST remain equivalent to the pre-refactor contract.
