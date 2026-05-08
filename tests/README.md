# Test Suite

## Çalıştırma
```bash
python -m pytest tests/ -v
```

## Dosyalar
- `tests/conftest.py` — Pytest config & fixtures
- `tests/test_components_v2.py` — V2 component builder unit tests (31 test)
- `tests/test_moderation.py` — parse_duration & hierarchy_ok (14 test)
- `tests/test_fun_games.py` — TKM, TR_NORM, 8ball, date parsing, vampir role distribution (16 test)
- `tests/test_music.py` — duration_fmt, platform detection, thumbnail extraction (25 test)
- `tests/test_bot_startup.py` — import smoke tests, cog setup() checks (6 test)

## Sonuç (2026-05-08)
92 test — **Tümü geçti** ✅
