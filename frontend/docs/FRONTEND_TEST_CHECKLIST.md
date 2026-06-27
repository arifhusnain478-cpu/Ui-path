# Frontend Test Checklist

## Authentication

- login works
- token persists
- wrong credentials show error
- logout clears token
- protected routes redirect

## Dashboard

- cases load
- fields render
- filters work
- risk colors work
- click opens case
- empty state exists

## New Complaint

- exact fields
- US/EU only
- approved complaint types only
- snake_case request
- null batch_number allowed
- errors visible
- success opens case

## Case Detail

- correct case loads
- stage highlighted
- confidence correct
- <0.6 red
- 3 hypotheses where available
- citations from API only
- CAPA and SLA render

## Human Task

- task and AI recommendation render
- citations render
- approve works
- reject requires reason
- override requires reason
- override_reason sent in snake_case
- case/task refreshes

## Audit Trail

- chronological
- actor/user/timestamp/type visible
- overrides distinct
- AI decisions distinct
- stage transitions distinct

## Contract checks

- no camelCase API fields
- no component Axios calls
- no hardcoded case outcomes
- loading/error/empty states exist
- mobile and desktop work
