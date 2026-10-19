# What a signed review handoff can establish

Consider an author agent that sends a patch and says its tests passed. A reviewer
signs a receipt for that handoff. Later, the patch fails. Three separate questions
remain: which bytes were exchanged, whether the tests ran against those bytes,
and whether the tests establish the desired behavior. A receipt addresses the
first question under the verifier's key and chain assumptions.

The delegation bundle supplies a useful example of the distinction. A bundle
with the wrong grantee has valid signatures and fails the authority check. Run the
README's `verify-chain` example to reproduce it. The verifier checks a declared
grant relationship as well as the signed bytes; a signature alone would leave
that relationship unresolved.

An integration should keep the patch digest, test-receipt digest, tested revision,
environment fingerprint and review result in an external action or evidence
artifact. Canonicalize that artifact using the agreed protocol and put its hash
in the existing receipt. Keep the artifact available to the reviewer. These are
integration recommendations; the current receipt schema does not validate a test
receipt's meaning or attest that a sandbox executed honestly.

Use an independent collector for test output and diffs. Have the reviewer inspect
those artifacts before receiving the author's conclusion. Record a later rerun as
new evidence linked to the failed run. Preserve the original signature and outcome
when the implementation changes; a previously passing result can remain valid
history while no longer covering the current revision.

The research lead is [Audit Without Verification](https://arxiv.org/abs/2609.07680).
It does not make this verifier a truth oracle. Do not put private source passages,
API keys, or the full business payload into a public receipt to make a handoff
look more complete. Publish only evidence you are authorized to disclose.

A small adoption experiment needs one author, one independent reviewer, the
existing synthetic keys, and two patch revisions. Verify the receipts for both;
then show that a test receipt tied to revision A cannot by itself approve B.
Success is an explicit stale-evidence finding, even when every signature passes.
