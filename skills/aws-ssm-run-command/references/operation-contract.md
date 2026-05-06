# Operation contract

The one-shot wrapper returns compact JSON with:

- `CommandId`
- `Wait`
  - `Status`
  - `ResponseCode`
  - `ExecutionStartDateTime`
  - `ExecutionEndDateTime`
  - `WaitMeta`
- `Output`
  - `Status`
  - `ResponseCode`
  - `ExecutionStartDateTime`
  - `ExecutionEndDateTime`
  - `StdOut`
  - `StdErr`

Exit behavior:

- exit `0` when wait status is `Success`
- exit non-zero when wait status is terminal but not `Success`
- exit `2` when the wait loop times out
