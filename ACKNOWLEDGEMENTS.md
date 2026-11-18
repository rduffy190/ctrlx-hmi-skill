# Acknowledgements

## Use of AI in this software

Parts of this skill were generated and tested with the help of Anthropic's AI models **Claude Opus 5.5** and
**Claude Sonnet 5.5**, working in Claude Code under the direction of the author.

What that covers:

- **Instructions and references:** `SKILL.md`, the README and the reference notes were drafted or edited with the models.
- **Code:** the screen generator (`scripts/visugen.py`), the preview renderer and the examples were written or revised by the models from the author's requests.
- **Testing:** the models wrote and ran tests where this repo has them, ran the tools against real ctrlX software or
  a simulator, and helped investigate and fix the problems that turned up.

The author set the requirements, directed the work, ran it on real ctrlX installations and decided what was kept.
AI-assisted work can still contain mistakes. Preview a generated screen and test it in the IDE before it goes to an operator panel.

## Other software and trademarks

No ctrlX PLC Engineering or CODESYS content is shipped in this repository. The templates the generator needs are exports of CODESYS visualization objects, so each user makes them from their own licensed ctrlX PLC Engineering with `scripts/make_templates.py`; the `templates/` folder is gitignored.

ctrlX, ctrlX CORE, ctrlX DRIVE, ctrlX OS and ctrlX PLC Engineering are products of Bosch Rexroth AG, and CODESYS
is a product of CODESYS GmbH. This project is independent and is not affiliated with or endorsed by either, or by
Anthropic.

This repository is licensed under the MIT License, see [LICENSE](LICENSE). It comes without warranty of any kind.
