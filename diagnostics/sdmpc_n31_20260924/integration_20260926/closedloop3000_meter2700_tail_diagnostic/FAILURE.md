First attempt stopped after the held2700–2850 interval, before evaluating2850–3000.
The copied model ledger contained outside stock −2.42861286636753e−17 at
SC101_to_SC1; strict initialization correctly rejected it. Session32425 exit1.
See ../closedloop3000_meter_tail.log and ../ledger_roundoff_before.log.

Root cause reproduced with inside stock0.01 and accepted transfer0.007:
count*inside/total rounded above count, creating negative outside stock at the
target. The canonical transfer now computes count*(inside/total). Initial-stock
and real-overdraw rejection are unchanged. 52 accounting/copy tests passed.

No result from this partial attempt proves900s response. A new v2 diagnostic
directory preserves this failure and rechecks the first450s against the prior
completed three-block evaluation. No native run or MPC horizon change.
