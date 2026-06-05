# Ethical Use Policy

Telescope is a defensive Threat Intelligence and OSINT tool. It is built to help
security teams, researchers, and defenders monitor publicly accessible Telegram
content for threats relevant to their organization.

This document is a hard line, not a suggestion. If your intended use does not fit
inside it, do not use this tool.

## What Telescope does (and does not) do

- Telescope connects to Telegram using your **personal user session** via the official
  MTProto API (Telethon). It can only see content that **your Telegram account can
  already see** - public channels, groups you have joined, chats you participate in.
- Telescope does **not** scrape behind invite walls, bypass Telegram access controls,
  exploit API quotas, or interact with accounts on your behalf beyond reading messages
  in monitored sources.
- Telescope does **not** collect data from accounts you do not have a direct
  relationship with. It is not a surveillance tool for tracking individuals.

## Acceptable use

You may use Telescope to:

- Monitor publicly accessible Telegram channels for threat intelligence relevant to
  your organization (CVE chatter, 0-day discussion, ransomware leak sites,
  Initial Access Broker activity, credential dumps mentioning your domain).
- Track open-source threat indicators (CVE IDs, IOCs, malware family names) in
  channels you have a legitimate professional reason to follow.
- Build internal dashboards or alert pipelines that integrate Telescope's webhook
  output into your existing SIEM, ticketing, or incident response stack.
- Conduct security research on threat actor activity in publicly accessible spaces.

## Unacceptable use

You may **not** use Telescope to:

- Surveil, harass, dox, or otherwise target individual people.
- Monitor private one-on-one direct messages of others.
- Stalkerware applications of any form.
- Collect data on private groups that you joined under false pretenses or by
  abusing access you should not have.
- Evade Telegram's Terms of Service or its rate limits.
- Aggregate personally identifiable information about non-public individuals.
- Sell or redistribute collected data without the consent of the source channels.

## Responsible disclosure

If Telescope helps you observe a 0-day, an active exploitation campaign, or a
breach affecting a third party, the right move is responsible disclosure to the
affected vendor or organization - not publication. Use the data to defend, not to
amplify harm.

## Operational hygiene

- Treat your `.session` file as a credential. Anyone with that file can act as your
  Telegram account.
- Do not commit your `config.json`, `.env`, `*.session`, or `telescope.db` to public
  repositories. They contain access tokens, chat identifiers, and historical match
  data.
- Be careful with webhook destinations. Match payloads contain message excerpts
  that may be sensitive.
- Rotate your bot tokens and API credentials regularly.

## Telegram Terms of Service

Telescope uses the official Telegram client API via Telethon. You are responsible
for ensuring your usage complies with the [Telegram Terms of Service](https://telegram.org/tos)
and the [Telegram API Terms of Service](https://core.telegram.org/api/terms).
Excessive activity from a user-session account can result in rate limiting or
account restrictions imposed by Telegram itself.

## Legal

The Apache license under which Telescope is distributed disclaims warranty and
liability. You are responsible for the legality of your use in your jurisdiction.

If you are unsure whether your intended use is appropriate, **don't use it.**
