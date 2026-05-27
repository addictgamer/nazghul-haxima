from pygame_haxima.data.content_registry import ContentRegistry


def test_new_session_has_party_and_place() -> None:
    session = ContentRegistry().make_new_session()
    assert session.place.width > 0
    assert session.party.members
    assert session.party.x == session.party.members[0].x
