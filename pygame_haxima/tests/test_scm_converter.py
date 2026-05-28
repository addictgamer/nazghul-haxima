from __future__ import annotations

import json

from pygame_haxima.data.scm_converter import ScmConverter


def test_convert_terrains_parses_entries_and_passability(tmp_path) -> None:
    src = tmp_path / "terrains.scm"
    dst = tmp_path / "terrains.runtime.json"
    src.write_text(
        """
        (define opq 1)
        (define lgt 2)
        (define terrains
          (list
            (list 't_grass "Grass" 'pclass-grass 's_grass opq lgt)
            (list 't_wall "Wall" 'pclass-wall 's_wall 255 0)))
        """,
        encoding="utf-8",
    )

    converted = ScmConverter().convert_terrains(src, dst)
    payload = json.loads(dst.read_text(encoding="utf-8"))

    assert converted == 2
    assert payload["terrain_count"] == 2
    assert payload["terrains"][0]["tag"] == "t_grass"
    assert payload["terrains"][0]["passable"] is True
    assert payload["terrains"][1]["tag"] == "t_wall"
    assert payload["terrains"][1]["passable"] is False


def test_convert_map_file_extracts_rows_and_tokens(tmp_path) -> None:
    src = tmp_path / "map.scm"
    dst = tmp_path / "map.json"
    src.write_text(
        """
        (kern-mk-map 'm_test 2 2 'pal_basic
          (list "aa bb" "cc dd"))
        """,
        encoding="utf-8",
    )

    converted = ScmConverter().convert_map_file(src, dst)
    payload = json.loads(dst.read_text(encoding="utf-8"))

    assert converted == 1
    assert payload["map_count"] == 1
    entry = payload["maps"][0]
    assert entry["id"] == "m_test"
    assert entry["palette"] == "pal_basic"
    assert entry["row_count"] == 2
    assert entry["max_row_tokens"] == 2
    assert entry["tile_rows"] == [["aa", "bb"], ["cc", "dd"]]


def test_convert_quest_file_extracts_qstmk_and_update_refs(tmp_path) -> None:
    src = tmp_path / "quests-demo.scm"
    dst = tmp_path / "quests-demo.json"
    src.write_text(
        """
        (questadd
          (qst-mk
            "Wolf Hunt"
            'questentry-wolf
            (kern-ui-paginate-text "Find and defeat the wolf." "Return alive.")
            'quest-assign-wolf
            'quest-status-wolf
            's_scroll
            (tbl-build 'k_started #f 'k_done 0 'k_extra 1)))

        (quest-data-update 'questentry-wolf 'k_done #t)
        (quest-data-update 'non-quest-entry 'ignored #t)
        """,
        encoding="utf-8",
    )

    converted = ScmConverter().convert_quest_file(src, dst)
    payload = json.loads(dst.read_text(encoding="utf-8"))

    assert converted == 1
    assert payload["quest_count"] == 1
    quest = payload["quests"][0]
    assert quest["id"] == "questentry-wolf"
    assert quest["description_line_count"] == 2
    assert quest["description_preview"] == "Find and defeat the wolf."
    assert quest["payload_flags"] == ["k_done", "k_started"]
    assert payload["quest_update_refs"] == [
        {
            "api": "quest-data-update",
            "quest_id": "questentry-wolf",
            "key": "k_done",
        }
    ]


def test_convert_townsfolk_resolves_load_chain_and_extracts_metadata(tmp_path) -> None:
    world_dir = tmp_path / "world"
    src_dir = world_dir / "townsfolk"
    src_dir.mkdir(parents=True, exist_ok=True)
    init_src = src_dir / "init.scm"
    npc_src = src_dir / "abe.scm"
    dst = tmp_path / "townsfolk.runtime.json"

    init_src.write_text('(load "townsfolk/abe.scm")', encoding="utf-8")
    npc_src.write_text(
        """
        (define sch_abe (kern-mk-sched 'sch_abe (list 7 9)))
        (define abe-conv (ifc (reply 'name "Abe") (reply 'job "Smith")))
        (define (mk-abe)
          (mk-townsman '((name . "Abe")) sch_abe))
        """,
        encoding="utf-8",
    )

    converted = ScmConverter().convert_townsfolk(world_dir, init_src, dst)
    payload = json.loads(dst.read_text(encoding="utf-8"))

    assert converted == 1
    assert payload["loaded_count"] == 1
    assert payload["resolved_count"] == 1
    entry = payload["entries"][0]
    assert entry["source_file"] == "abe.scm"
    assert any(s["id"] == "sch_abe" for s in entry["schedules"])
    assert any(c["id"] == "abe-conv" and "name" in c["keywords"] for c in entry["conversations"])
    assert any(f["id"] == "mk-abe" and f["builder"] == "mk-townsman" for f in entry["factories"])
