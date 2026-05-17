from weave.ddb.portraits import extract_portraits, roster_avatar_url


def test_extract_portraits_v5_decorations():
    portraits = extract_portraits(
        {
            "decorations": {
                "avatarUrl": "https://www.dndbeyond.com/avatars/1.png",
                "frameAvatarUrl": "https://www.dndbeyond.com/frames/2.png",
                "largeBackdropAvatarUrl": "https://www.dndbeyond.com/backdrops/large/3.png",
            }
        }
    )
    assert portraits.avatar_url.endswith("1.png")
    assert portraits.frame_avatar_url.endswith("2.png")
    assert "backdrops" in (portraits.large_backdrop_avatar_url or "")


def test_roster_avatar_url_from_entry():
    url = roster_avatar_url(
        {"characterId": 99, "avatarUrl": "https://www.dndbeyond.com/avatars/x.png"}
    )
    assert url and "avatars" in url
