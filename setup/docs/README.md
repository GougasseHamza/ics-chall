# Documentation index

The documentation is separated by audience so challenge secrets and solution
details are not accidentally handed to players.

| Document | Audience | Contains spoilers |
|---|---|---:|
| [Player brief](PLAYER_BRIEF.md) | Players | No |
| [Architecture](ARCHITECTURE.md) | Authors and reviewers | Yes |
| [Operations runbook](OPERATIONS.md) | Event operators | Operational details |
| [Security boundaries](SECURITY.md) | Authors and infrastructure reviewers | Yes |
| [Author guide](AUTHOR_GUIDE.md) | Challenge authors | Yes |
| [Official walkthrough](../../writeup/README.md) | Authors and post-event readers | Yes |

## Release rule

Before the event, distribute only `PLAYER_BRIEF.md`, the public endpoints and
the player credential. Keep this repository private if the challenge is still
live.

The screenshots were captured from a completed instance and include an
instance-specific proof token. Before publishing the repository or walkthrough:

1. rotate `FLAG_SECRET` and `INSTANCE_ID`;
2. redeploy the checker;
3. reset the process;
4. confirm that the old proof token is no longer accepted.

## Evidence

The walkthrough refers to the numbered images under
[`../../writeup/assets/screenshots`](../../writeup/assets/screenshots/). Their
order follows the tested player journey from login through physical failure
and flag validation.
