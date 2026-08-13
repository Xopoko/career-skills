# Installation receipts

These receipts record bounded host observations for immutable Career Skills
releases. They are evidence of the checks named in each receipt, not a promise
that every host, operating system, account, or future version behaves the same
way.

The [Windows `0.1.2` receipt](2026-08-13-windows-v0.1.2.json) binds its checks
to release commit `42e77fbe5592f1953e6407784bba024e6956f2e7`. It verifies all
81 tracked release blobs in the installed Codex, Claude Code, and Cursor copies,
then runs the package validator and trigger contract from each copy.

Host visibility is stated narrowly:

- Codex reported `career@local` installed and enabled.
- Claude Code reported `career@career-skills` enabled at user scope.
- Cursor's installed checkout and Git head were verified, but the `cursor` CLI
  was not available in `PATH`; UI visibility therefore remains unverified.

No installation or cache was changed while producing the receipt. Usernames and
absolute machine paths are deliberately omitted.
