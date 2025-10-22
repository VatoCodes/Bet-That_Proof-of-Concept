# week_rollover_operator

Purpose: Automate weekly data lifecycle (backup, archive, prepare next week) with transactional safety.

## Operations
- prepare_rollover: Validate data integrity and preconditions
- execute_rollover: Backup DB, archive last week, create new week tables
- rollback_rollover: Restore from backup if failure occurs
- schedule_rollover: Configure Tuesday 3am ET trigger (placeholder)

## Safety
- Backup and verify before changes
- Lock DB during execute
- Auto-rollback on post-validate failure

## Example
```
{
  "operation": "execute_rollover",
  "current_week": 7,
  "target_week": 8,
  "dry_run": true
}
```
