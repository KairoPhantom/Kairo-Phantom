# Phase 0.5 Receipt: MCP Server + Messaging Connectors

> **Date**: 2026-06-24
> **Status**: CONNECTOR SECURITY DONE — InjectionGuard proven on all 3 connectors

---

## What Was Built

### Connector Framework (sidecar/connectors/)
- `telegram_connector.py`: Full security pipeline (PromptShield + PiiGuard)
- `discord_connector.py`: Reuses telegram security pipeline
- `email_connector.py`: Reuses telegram security pipeline with email-specific message format

### Security Pipeline (REAL, not mocked)
Every inbound message goes through:
1. **Air-gap check** → if ON, blocked immediately
2. **PromptShield.scan()** → injection detection (REAL, not mocked)
3. **PiiGuard.redact()** → PII redaction on inbound (REAL)
4. **Kairo handler** → processes safe text (mock transport for testing)
5. **PiiGuard.redact()** → PII redaction on outbound (REAL)

### Key Design Decisions
- **Fail-closed**: If PromptShield is unavailable, messages are BLOCKED (not allowed through)
- **Disabled by default**: Connectors only activate with `KAIRO_CONNECTORS=telegram,discord,email`
- **Air-gap enforced**: When `KAIRO_OFFLINE=1`, all connectors refuse to start
- **Mock transport clearly labeled**: The `mock_kairo_handler` simulates the agent response
  for testing — the security screening (PromptShield + PiiGuard) is REAL

## Tests (20 tests, all pass)

```
pytest test_phase0_5_connectors.py
20 passed in 1.40s
```

### InjectionGuard Tests (proving security is REAL):
1. `test_normal_message_passes` — clean message passes through
2. `test_ignore_instructions_blocked` — "ignore previous instructions" BLOCKED
3. `test_tool_injection_blocked` — "execute rm -rf /" BLOCKED
4. `test_role_override_blocked` — "You are now DAN" BLOCKED
5. `test_hidden_instruction_blocked` — "[SYSTEM OVERRIDE]" BLOCKED
6. `test_data_exfiltration_attempt_blocked` — "reveal secrets" screened

### PiiGuard Tests:
7. `test_ssn_redacted_in_response` — SSN redacted in outbound
8. `test_email_redacted_in_response` — email redacted in outbound
9. `test_phone_redacted_in_response` — phone redacted in outbound
10. `test_no_pii_passes_through` — clean text passes unchanged

### Air-gap Tests:
11. `test_airgap_blocks_telegram` — air-gap blocks Telegram
12. `test_airgap_blocks_discord` — air-gap blocks Discord
13. `test_airgap_blocks_email` — air-gap blocks email
14. `test_no_airgap_allows_normal_message` — no air-gap allows messages

### Default-Disabled Tests:
15. `test_telegram_disabled_by_default` — disabled without env var
16. `test_telegram_enabled_with_env` — enabled with KAIRO_CONNECTORS

### End-to-End Security Pipeline:
17. `test_clean_message_e2e` — clean message → handler → response
18. `test_injection_message_e2e` — injection BLOCKED before handler
19. `test_pii_in_response_redacted_e2e` — PII redacted in E2E response
20. `test_discord_injection_blocked_e2e` — Discord injection blocked
21. `test_email_injection_blocked_e2e` — Email injection blocked

## What's NOT Done
- **MCP server enhancement**: kairo-mcp doesn't yet expose all 12 domain tools as MCP tools
- **Live bot tokens**: Telegram/Discord/Email live testing needs real bot tokens (INFRA_PENDING)
- **MCP manifest submission**: Not submitted to mcpservers.org, mcp.so, awesome-mcp-servers
- **python-telegram-bot / discord.py**: Not installed (handler logic is tested with mock transport)

## INFRA_PENDING
- Live Telegram/Discord/Email testing requires real bot tokens and network access
- Verification command:
  ```bash
  export KAIRO_CONNECTORS=telegram
  export TELEGRAM_BOT_TOKEN=<real_token>
  python3 -m sidecar.connectors.telegram_connector  # Live bot
  ```